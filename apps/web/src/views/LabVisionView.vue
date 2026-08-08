<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../lib/api'

const text = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)
const imagePreview = ref('')
const imageBase64 = ref('')
const mime = ref('image/jpeg')
const answers = ref<Record<number, string>>({})
const checks = ref<Record<number, { correct: boolean; analysis: string; expected?: string | null }>>({})

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

async function submit() {
  error.value = ''
  result.value = null
  checks.value = {}
  if (!text.value.trim() && !imageBase64.value) {
    error.value = '请上传题目图片或粘贴题干'
    return
  }
  loading.value = true
  try {
    result.value = await api('/labs/vision-read', {
      method: 'POST',
      body: JSON.stringify({
        text: text.value,
        image_base64: imageBase64.value,
        mime: mime.value,
      }),
      auth: false,
    })
  } catch (e: any) {
    error.value = e?.message || '读题失败'
  } finally {
    loading.value = false
  }
}

async function check(qid: number) {
  const r = await api<{ correct: boolean; analysis: string; expected?: string | null }>(
    '/labs/practice/check',
    {
      method: 'POST',
      body: JSON.stringify({ question_id: qid, answer: answers.value[qid] || '' }),
      auth: false,
    },
  )
  checks.value[qid] = r
}
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/courses/geometry-lab">← 实验室</RouterLink>
    <div class="head">
      <div>
        <h1>图片读题</h1>
        <p class="sub">上传题目截图或粘贴题干，识别知识点并推荐交互课页与巩固练习。</p>
      </div>
      <RouterLink class="ghost-link" to="/courses/geometry-lab/tutor">对话讲解 →</RouterLink>
    </div>

    <div class="panel">
      <label class="file">
        <span>上传题目图片</span>
        <input type="file" accept="image/*" @change="onFile" />
      </label>
      <img v-if="imagePreview" :src="imagePreview" alt="题目预览" class="preview" />
      <textarea v-model="text" rows="4" placeholder="也可粘贴题干文字，例如：正方体 ABCD-A1B1C1D1 中…" />
      <button type="button" class="btn" :disabled="loading" @click="submit">
        {{ loading ? '识别中…' : '开始读题' }}
      </button>
      <p v-if="error" class="err">{{ error }}</p>
    </div>

    <section v-if="result" class="result">
      <p class="meta">来源：{{ result.source === 'llm' ? '大模型识别' : '关键词启发式' }}</p>
      <p v-if="result.hint" class="hint">{{ result.hint }}</p>
      <h2>识别题干</h2>
      <p class="stem">{{ result.stem }}</p>
      <div class="tags">
        <span v-for="k in result.knowledge_points" :key="k">{{ k }}</span>
      </div>

      <h2>推荐课页</h2>
      <ul class="labs">
        <li v-for="lab in result.suggested_labs" :key="lab.page_key">
          <RouterLink :to="`/courses/geometry-lab/${lab.page_key}`">
            {{ lab.title }}
            <small>{{ lab.category }} · {{ lab.knowledge_points }}</small>
          </RouterLink>
        </li>
      </ul>
      <p v-if="!result.suggested_labs?.length" class="hint">暂无匹配课页</p>

      <h2>巩固练习</h2>
      <ul class="qs">
        <li v-for="q in result.questions" :key="q.id">
          <div class="reason">{{ q.reason }}</div>
          <p class="qstem">{{ q.stem }}</p>
          <div v-if="q.options?.length" class="opts">
            <label v-for="(opt, idx) in q.options" :key="idx">
              <input v-model="answers[q.id]" type="radio" :value="String(idx)" />
              {{ opt }}
            </label>
          </div>
          <input
            v-else
            v-model="answers[q.id]"
            class="blank"
            placeholder="填写答案"
          />
          <button type="button" class="check" @click="check(q.id)">核对</button>
          <p v-if="checks[q.id]" class="verdict" :class="{ ok: checks[q.id].correct }">
            {{ checks[q.id].correct ? '正确' : '再想想' }} · {{ checks[q.id].analysis }}
          </p>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.page {
  width: min(820px, 100%);
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
.ghost-link {
  white-space: nowrap;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(15, 107, 92, 0.25);
  color: var(--brand);
  font-size: 0.88rem;
  font-weight: 600;
}
.sub,
.hint,
.meta {
  color: var(--muted);
}
.panel {
  margin-top: 18px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 107, 92, 0.14);
  background: rgba(255, 255, 255, 0.85);
  display: grid;
  gap: 12px;
}
.file {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-weight: 600;
  color: var(--brand-deep);
}
.preview {
  max-width: 100%;
  max-height: 240px;
  border-radius: 10px;
  object-fit: contain;
  background: #edf3f8;
}
textarea,
.blank {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  font: inherit;
  resize: vertical;
}
.btn,
.check {
  justify-self: start;
  border: 0;
  border-radius: 999px;
  padding: 10px 16px;
  background: var(--brand);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}
.btn:disabled {
  opacity: 0.6;
}
.err {
  color: #b42318;
  margin: 0;
}
.result {
  margin-top: 28px;
}
h2 {
  font-family: var(--font-display);
  font-size: 1.15rem;
  margin: 18px 0 8px;
}
.stem {
  background: rgba(15, 107, 92, 0.06);
  padding: 12px;
  border-radius: 10px;
  white-space: pre-wrap;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0;
}
.tags span {
  background: rgba(232, 163, 23, 0.18);
  color: #8a5a00;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.85rem;
}
.labs,
.qs {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 10px;
}
.labs a {
  display: block;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 107, 92, 0.14);
  background: #fff;
  color: inherit;
  text-decoration: none;
}
.labs small {
  display: block;
  color: var(--muted);
  margin-top: 4px;
}
.qs li {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  background: #fff;
}
.reason {
  color: var(--brand);
  font-size: 0.82rem;
}
.qstem {
  margin: 6px 0 10px;
}
.opts {
  display: grid;
  gap: 6px;
  margin-bottom: 10px;
}
.opts label {
  display: flex;
  gap: 8px;
  align-items: center;
}
.check {
  margin-top: 8px;
  padding: 6px 12px;
  font-size: 0.85rem;
}
.verdict {
  margin: 8px 0 0;
  color: #b42318;
  font-size: 0.9rem;
}
.verdict.ok {
  color: var(--brand-deep);
}
</style>
