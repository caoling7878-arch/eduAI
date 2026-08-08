<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  streamGeometryTutor,
  type GeometryChatTurn,
  type GeometryLabSuggestion,
} from '../lib/geometryTutor'
import { useAuth } from '../stores/auth'

const auth = useAuth()

const messages = ref<GeometryChatTurn[]>([])
const draft = ref('')
const streaming = ref(false)
const err = ref('')
const quotaBlocked = ref(false)
const imagePreview = ref('')
const imageBase64 = ref('')
const mime = ref('image/jpeg')
const listEl = ref<HTMLElement | null>(null)
let abort: AbortController | null = null

const examples = [
  '正方体 ABCD-A1B1C1D1 中，求直线 A1C 与底面 ABCD 所成角的正弦值',
  '椭圆 x²/25 + y²/16 = 1 上一点 P 到两焦点距离之和是多少？',
  '长方体长 3 宽 4 高 5，求体积与体对角线长度',
  '抛物线 y² = 4x 上一点到焦点与准线的距离关系怎么理解？',
]

const canSend = computed(() => !streaming.value && !quotaBlocked.value && draft.value.trim().length > 0)

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function boot() {
  messages.value = [
    {
      role: 'assistant',
      content:
        '你好，我是几何讲解助手。你可以用文字描述题目，也可以上传题目截图（需配置视觉模型）。\n\n我会分步讲解思路，并推荐对应的交互动图课页，方便你拖动模型验证答案。',
    },
  ]
}

boot()

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  },
)

async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  mime.value = file.type || 'image/jpeg'
  imagePreview.value = URL.createObjectURL(file)
  const buf = await file.arrayBuffer()
  const bytes = new Uint8Array(buf)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  imageBase64.value = btoa(binary)
}

function clearImage() {
  imagePreview.value = ''
  imageBase64.value = ''
}

function useExample(text: string) {
  draft.value = text
}

function historyForApi(): Array<{ role: 'user' | 'assistant'; content: string }> {
  return messages.value
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .slice(-12)
    .map((m) => ({ role: m.role, content: m.content }))
}

async function send() {
  const text = draft.value.trim()
  if (!text || streaming.value) return

  err.value = ''
  quotaBlocked.value = false
  draft.value = ''
  const img = imageBase64.value
  const imgMime = mime.value
  clearImage()

  messages.value.push({ role: 'user', content: text })
  const assistant: GeometryChatTurn = { role: 'assistant', content: '', steps: [], suggested_labs: [] }
  messages.value.push(assistant)

  streaming.value = true
  abort?.abort()
  abort = new AbortController()

  try {
    await streamGeometryTutor(
      text,
      historyForApi().slice(0, -2),
      {
        onDelta: (chunk) => {
          assistant.content += chunk
        },
        onMeta: (meta) => {
          assistant.steps = meta.steps
          assistant.knowledge_points = meta.knowledge_points
          assistant.suggested_labs = meta.suggested_labs
          assistant.source = meta.source
        },
        onDone: (full) => {
          assistant.content = full
        },
        onError: (message, code) => {
          if (code === 'quota_exceeded') quotaBlocked.value = true
          err.value = message
          if (!assistant.content) {
            assistant.content = message
          }
        },
      },
      { imageBase64: img, mime: imgMime, signal: abort.signal },
    )
    if (auth.isLoggedIn.value && messages.value.filter((m) => m.role === 'user').length >= 1) {
      void auth.track('geometry-lab', 'tutor', 'started', { turns: messages.value.length })
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '讲解失败'
    err.value = msg
    assistant.content = msg
  } finally {
    streaming.value = false
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void send()
  }
}

onBeforeUnmount(() => {
  abort?.abort()
})
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/courses/geometry-lab">← 实验室</RouterLink>
    <div class="head">
      <div>
        <h1>对话讲解</h1>
        <p class="sub">用文字描述几何题，AI 分步讲解并推荐交互动图课页。</p>
      </div>
      <RouterLink class="ghost-link" to="/courses/geometry-lab/vision">图片读题 →</RouterLink>
    </div>

    <div class="examples">
      <span class="label">试试这些：</span>
      <button
        v-for="ex in examples"
        :key="ex"
        type="button"
        class="chip"
        :disabled="streaming"
        @click="useExample(ex)"
      >
        {{ ex.length > 28 ? `${ex.slice(0, 28)}…` : ex }}
      </button>
    </div>

    <div class="chat panel">
      <ul ref="listEl" class="messages">
        <li v-for="(m, i) in messages" :key="i" :class="m.role">
          <div class="bubble">
            <p class="content">{{ m.content }}<span v-if="streaming && i === messages.length - 1" class="cursor">▍</span></p>
            <div v-if="m.knowledge_points?.length" class="tags">
              <span v-for="k in m.knowledge_points" :key="k">{{ k }}</span>
            </div>
            <ol v-if="m.steps?.length" class="steps">
              <li v-for="(s, si) in m.steps" :key="si">{{ s }}</li>
            </ol>
            <ul v-if="m.suggested_labs?.length" class="labs">
              <li v-for="lab in m.suggested_labs as GeometryLabSuggestion[]" :key="lab.page_key">
                <RouterLink :to="`/courses/geometry-lab/${lab.page_key}`">
                  {{ lab.title }}
                  <small>{{ lab.category }}</small>
                </RouterLink>
              </li>
            </ul>
            <p v-if="m.source && m.role === 'assistant' && i > 0" class="src">
              {{ m.source === 'llm' ? '大模型讲解' : '本地模板讲解' }}
            </p>
          </div>
        </li>
      </ul>

      <div class="composer">
        <div v-if="imagePreview" class="attach">
          <img :src="imagePreview" alt="题目预览" />
          <button type="button" class="rm" @click="clearImage">移除</button>
        </div>
        <textarea
          v-model="draft"
          rows="3"
          :placeholder="
            quotaBlocked
              ? '配额已用尽，请联系学校管理员开通用量包'
              : '描述你的几何题，例如：正方体中某直线与平面所成角…（Enter 发送，Shift+Enter 换行）'
          "
          :disabled="streaming || quotaBlocked"
          @keydown="onKey"
        />
        <div class="row">
          <label class="file-btn">
            附图
            <input type="file" accept="image/*" :disabled="streaming" @change="onFile" />
          </label>
          <button type="button" class="send" :disabled="!canSend" @click="send">
            {{ streaming ? '讲解中…' : '发送' }}
          </button>
        </div>
        <p v-if="err" class="err">
          {{ err }}
          <RouterLink v-if="quotaBlocked" to="/me">查看用量</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  width: min(860px, 100%);
  margin: 0 auto;
  padding: 24px 20px 60px;
}
.back {
  color: var(--muted);
  font-size: 0.92rem;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-top: 12px;
}
h1 {
  font-family: var(--font-display);
  margin: 0 0 6px;
}
.sub {
  color: var(--muted);
  margin: 0;
}
.ghost-link {
  white-space: nowrap;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(15, 107, 92, 0.25);
  color: var(--brand);
  font-size: 0.88rem;
  font-weight: 600;
}
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 18px 0;
}
.label {
  color: var(--muted);
  font-size: 0.85rem;
}
.chip {
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.75);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.82rem;
  cursor: pointer;
  color: var(--brand-deep);
}
.chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.chat {
  border: 1px solid rgba(15, 107, 92, 0.14);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  display: flex;
  flex-direction: column;
  min-height: 520px;
  max-height: calc(100vh - 280px);
}
.messages {
  flex: 1;
  overflow: auto;
  list-style: none;
  margin: 0;
  padding: 16px;
  display: grid;
  gap: 12px;
}
.messages li.user {
  justify-self: end;
}
.messages li.assistant {
  justify-self: start;
}
.bubble {
  max-width: min(640px, 92vw);
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 0.94rem;
  line-height: 1.55;
}
.user .bubble {
  background: linear-gradient(120deg, #0f6b5c, #1a8f7a);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.assistant .bubble {
  background: rgba(15, 107, 92, 0.06);
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-bottom-left-radius: 4px;
}
.content {
  margin: 0;
  white-space: pre-wrap;
}
.cursor {
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.tags span {
  background: rgba(232, 163, 23, 0.18);
  color: #8a5a00;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.78rem;
}
.steps {
  margin: 10px 0 0;
  padding-left: 1.2rem;
  color: var(--brand-deep);
  font-size: 0.88rem;
}
.labs {
  list-style: none;
  padding: 0;
  margin: 10px 0 0;
  display: grid;
  gap: 6px;
}
.labs a {
  display: block;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.14);
  color: inherit;
  text-decoration: none;
  font-weight: 600;
}
.labs small {
  display: block;
  color: var(--muted);
  font-weight: 400;
  margin-top: 2px;
}
.src {
  margin: 8px 0 0 !important;
  font-size: 0.75rem;
  color: var(--muted) !important;
}
.composer {
  border-top: 1px solid rgba(15, 107, 92, 0.1);
  padding: 12px 14px 14px;
  display: grid;
  gap: 10px;
}
.attach {
  display: flex;
  align-items: center;
  gap: 10px;
}
.attach img {
  max-height: 80px;
  border-radius: 8px;
  background: #edf3f8;
}
.rm {
  border: 0;
  background: transparent;
  color: #b42318;
  cursor: pointer;
  font-size: 0.85rem;
}
textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  font: inherit;
  resize: vertical;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.file-btn {
  position: relative;
  overflow: hidden;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  cursor: pointer;
  font-size: 0.88rem;
  color: var(--brand-deep);
}
.file-btn input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.send {
  border: 0;
  border-radius: 999px;
  padding: 10px 20px;
  background: var(--brand);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.send:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.err {
  margin: 0;
  color: #b42318;
  font-size: 0.88rem;
}
.err a {
  margin-left: 8px;
  color: var(--brand);
}
@media (max-width: 640px) {
  .head {
    flex-direction: column;
  }
  .chat {
    min-height: 460px;
    max-height: calc(100vh - 240px);
  }
}
</style>
