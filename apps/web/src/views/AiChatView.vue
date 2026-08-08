<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  createSession,
  deleteSession,
  fetchCompanions,
  fetchMessages,
  fetchSessions,
  renameSession,
  streamChat,
  type ChatMsg,
  type ChatSession,
  type Companion,
} from '../lib/chat'
import { fetchMyBilling } from '../lib/api'
import { renderMarkdown } from '../lib/markdown'
import { useAuth } from '../stores/auth'

const props = defineProps<{ assistantId: string }>()
const auth = useAuth()
const router = useRouter()

const companion = ref<Companion | null>(null)
const sessions = ref<ChatSession[]>([])
const sessionId = ref<number | null>(null)
const messages = ref<ChatMsg[]>([])
const input = ref('')
const streaming = ref(false)
const loading = ref(true)
const err = ref('')
const quotaBlocked = ref(false)
const billing = ref<Awaited<ReturnType<typeof fetchMyBilling>> | null>(null)
const sideOpen = ref(true)
const listEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const citeOpen = ref<number | null>(null)
const renamingId = ref<number | null>(null)
const renameDraft = ref('')
let abort: AbortController | null = null
let mq: MediaQueryList | null = null

const aid = computed(() => Number(props.assistantId))
const tokenPct = computed(() => billing.value?.subscription?.token_pct ?? 0)
const requestPct = computed(() => billing.value?.subscription?.request_pct ?? 0)
const quotaTight = computed(() => tokenPct.value >= 80 || requestPct.value >= 80)
const isMobile = ref(false)
const prompts = computed(() => companion.value?.suggested_prompts || [])
const canRegenerate = computed(() => {
  if (streaming.value || !sessionId.value || !messages.value.length) return false
  const last = messages.value[messages.value.length - 1]
  return last?.role === 'assistant' && !last.streaming && !!last.content
})

function md(html: string) {
  return renderMarkdown(html)
}

async function scrollBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

async function loadBilling() {
  try {
    billing.value = await fetchMyBilling()
  } catch {
    billing.value = null
  }
}

async function boot() {
  if (!auth.isLoggedIn.value) {
    router.replace({ path: '/auth', query: { redirect: `/ai/${props.assistantId}` } })
    return
  }
  loading.value = true
  quotaBlocked.value = false
  err.value = ''
  void loadBilling()
  try {
    const all = await fetchCompanions()
    companion.value = all.find((c) => c.id === aid.value) || null
    if (!companion.value) {
      err.value = '助手不存在或未启用'
      return
    }
    sessions.value = await fetchSessions(aid.value)
    if (sessions.value[0]) {
      sessionId.value = sessions.value[0].id
      messages.value = await fetchMessages(sessionId.value)
    } else {
      const s = await createSession(aid.value)
      sessions.value = [s]
      sessionId.value = s.id
      messages.value = []
    }
    await scrollBottom()
  } catch (e) {
    err.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function newChat() {
  if (!companion.value || streaming.value) return
  try {
    const s = await createSession(companion.value.id)
    sessions.value = [s, ...sessions.value]
    sessionId.value = s.id
    messages.value = []
    err.value = ''
    if (isMobile.value) sideOpen.value = false
    await nextTick()
    inputEl.value?.focus()
  } catch (e) {
    err.value = e instanceof Error ? e.message : '新建失败'
  }
}

async function switchSession(id: number) {
  if (streaming.value || renamingId.value === id) return
  try {
    sessionId.value = id
    messages.value = await fetchMessages(id)
    err.value = ''
    await scrollBottom()
    if (isMobile.value) sideOpen.value = false
  } catch (e) {
    err.value = e instanceof Error ? e.message : '切换会话失败'
  }
}

function startRename(s: ChatSession, ev: Event) {
  ev.stopPropagation()
  if (streaming.value) return
  renamingId.value = s.id
  renameDraft.value = s.title
}

async function commitRename() {
  const id = renamingId.value
  if (!id) return
  const title = renameDraft.value.trim()
  renamingId.value = null
  if (!title) return
  try {
    const updated = await renameSession(id, title)
    const row = sessions.value.find((x) => x.id === id)
    if (row) row.title = updated.title
  } catch (e) {
    err.value = e instanceof Error ? e.message : '重命名失败'
  }
}

async function removeSession(id: number, ev?: Event) {
  ev?.stopPropagation()
  if (streaming.value) return
  if (!window.confirm('删除该对话？消息不可恢复。')) return
  try {
    await deleteSession(id)
    sessions.value = sessions.value.filter((s) => s.id !== id)
    if (sessionId.value === id) {
      if (sessions.value[0]) {
        sessionId.value = sessions.value[0].id
        messages.value = await fetchMessages(sessionId.value)
      } else if (companion.value) {
        const s = await createSession(companion.value.id)
        sessions.value = [s]
        sessionId.value = s.id
        messages.value = []
      }
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function stop() {
  abort?.abort()
  abort = null
  streaming.value = false
  const last = messages.value[messages.value.length - 1]
  if (last?.streaming) {
    last.streaming = false
    if (last.content && !last.content.includes('已停止')) {
      last.content = `${last.content}\n\n（已停止生成）`
    }
  }
  // 与服务端落库对齐
  if (sessionId.value) {
    try {
      messages.value = await fetchMessages(sessionId.value)
    } catch {
      /* keep local */
    }
  }
}

async function runStream(text: string, regenerate: boolean) {
  if (!sessionId.value || streaming.value || quotaBlocked.value) return
  err.value = ''

  let bot: ChatMsg
  if (regenerate) {
    const last = messages.value[messages.value.length - 1]
    if (last?.role === 'assistant') {
      last.content = ''
      last.citations = []
      last.streaming = true
      bot = last
    } else {
      bot = { role: 'assistant', content: '', citations: [], streaming: true }
      messages.value.push(bot)
    }
  } else {
    messages.value.push({ role: 'user', content: text })
    bot = { role: 'assistant', content: '', citations: [], streaming: true }
    messages.value.push(bot)
  }

  streaming.value = true
  await scrollBottom()
  abort = new AbortController()

  try {
    await streamChat(
      sessionId.value,
      text,
      {
        onCitations(items) {
          bot.citations = items
        },
        onDelta(delta) {
          bot.content += delta
          void scrollBottom()
        },
        onDone(full) {
          bot.content = full || bot.content
          bot.streaming = false
          void loadBilling()
        },
        onError(message, code) {
          err.value = message
          quotaBlocked.value = code === 'quota_exceeded'
          if (!bot.content) {
            bot.content =
              code === 'quota_exceeded'
                ? `（学校 AI 配额不足：${message}）`
                : `（${message}）`
          }
          bot.streaming = false
        },
      },
      abort.signal,
      { regenerate },
    )
  } catch (e) {
    if ((e as Error).name !== 'AbortError') {
      err.value = e instanceof Error ? e.message : '发送失败'
    }
  } finally {
    bot.streaming = false
    streaming.value = false
    abort = null
    try {
      sessions.value = await fetchSessions(aid.value)
    } catch {
      /* ignore */
    }
    await nextTick()
    inputEl.value?.focus()
  }
}

async function send() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  await runStream(text, false)
}

async function regenerate() {
  if (!canRegenerate.value) return
  await runStream('', true)
}

function usePrompt(p: string) {
  if (streaming.value || quotaBlocked.value) return
  input.value = p
  void send()
}

function onMq() {
  isMobile.value = !!mq?.matches
  if (isMobile.value) sideOpen.value = false
}

onMounted(() => {
  void boot()
  if (typeof window !== 'undefined') {
    mq = window.matchMedia('(max-width: 860px)')
    onMq()
    mq.addEventListener('change', onMq)
  }
})

onUnmounted(() => {
  abort?.abort()
  mq?.removeEventListener('change', onMq)
})

watch(
  () => props.assistantId,
  () => {
    void boot()
  },
)
</script>

<template>
  <div class="chat" v-if="companion" :class="{ 'side-collapsed': !sideOpen }">
    <aside class="side" v-show="sideOpen">
      <RouterLink to="/ai" class="back">← 学伴列表</RouterLink>
      <div class="who">
        <div class="avatar">
          {{ companion.avatar }}
          <i class="dot" :class="{ on: companion.online }" :title="companion.online ? '大模型在线' : '本地演示'" />
        </div>
        <div>
          <h1>{{ companion.name }}</h1>
          <p>
            {{ companion.online ? companion.model : '本地演示' }}
            <span v-if="companion.knowledge_base_id"> · 知识库</span>
          </p>
        </div>
      </div>
      <div v-if="billing?.subscription" class="quota" :class="{ warn: quotaTight || quotaBlocked }">
        <div class="quota-head">
          <span>{{ billing.tenant?.name || '学校' }} · {{ billing.subscription.pack_name }}</span>
          <RouterLink to="/me">详情</RouterLink>
        </div>
        <div class="qbar">
          <span>Token {{ Math.min(100, tokenPct) }}%</span>
          <i><b :style="{ width: Math.min(100, tokenPct) + '%' }" /></i>
        </div>
        <div class="qbar">
          <span>调用 {{ Math.min(100, requestPct) }}%</span>
          <i><b :style="{ width: Math.min(100, requestPct) + '%' }" /></i>
        </div>
      </div>
      <button type="button" class="new" @click="newChat">新建对话</button>
      <ul class="sessions">
        <li
          v-for="s in sessions"
          :key="s.id"
          :class="{ active: s.id === sessionId }"
          @click="switchSession(s.id)"
        >
          <input
            v-if="renamingId === s.id"
            v-model="renameDraft"
            class="rename"
            maxlength="80"
            @click.stop
            @keydown.enter.prevent="commitRename"
            @keydown.esc="renamingId = null"
            @blur="commitRename"
          />
          <span v-else class="stitle" :title="s.title" @dblclick="startRename(s, $event)">{{ s.title }}</span>
          <button type="button" class="ren" title="重命名" @click="startRename(s, $event)">✎</button>
          <button type="button" class="del" title="删除" @click="removeSession(s.id, $event)">×</button>
        </li>
      </ul>
      <p v-if="!sessions.length" class="side-empty">还没有对话，点上方新建。</p>
    </aside>

    <div v-if="sideOpen && isMobile" class="mask" @click="sideOpen = false" />

    <section class="main">
      <div class="main-top">
        <button type="button" class="side-toggle" @click="sideOpen = !sideOpen">
          {{ sideOpen ? '收起会话' : '会话列表' }}
        </button>
        <span class="main-title">{{ companion.name }}</span>
      </div>
      <div ref="listEl" class="messages">
        <div v-if="loading" class="empty">
          <p class="muted">加载对话中…</p>
        </div>
        <div v-else-if="!messages.length" class="empty">
          <p>{{ companion.persona }}</p>
          <p class="muted">点下方建议开始，或直接输入问题。</p>
          <div v-if="prompts.length" class="suggest">
            <button
              v-for="p in prompts"
              :key="p"
              type="button"
              class="chip"
              :disabled="streaming || quotaBlocked"
              @click="usePrompt(p)"
            >
              {{ p }}
            </button>
          </div>
        </div>
        <article
          v-for="(m, i) in messages"
          :key="m.id ?? i"
          class="msg"
          :class="m.role"
        >
          <div class="bubble">
            <div
              v-if="m.role === 'assistant'"
              class="md"
              v-html="md(m.content) + (m.streaming ? '<span class=&quot;cursor&quot;>▍</span>' : '')"
            />
            <pre v-else>{{ m.content }}</pre>
            <div v-if="m.citations?.length" class="cites">
              <button
                v-for="(c, ci) in m.citations"
                :key="c.doc_id"
                type="button"
                class="cite"
                @click="citeOpen = citeOpen === c.doc_id ? null : c.doc_id"
              >
                <strong>[{{ ci + 1 }}] {{ c.title }}</strong>
                <span v-if="citeOpen === c.doc_id">{{ c.snippet }}</span>
                <span v-else class="snip">{{ c.snippet.slice(0, 48) }}{{ c.snippet.length > 48 ? '…' : '' }}</span>
              </button>
            </div>
            <div
              v-if="m.role === 'assistant' && i === messages.length - 1 && !m.streaming && m.content"
              class="msg-actions"
            >
              <button type="button" class="retry" :disabled="!canRegenerate" @click="regenerate">
                重新生成
              </button>
            </div>
          </div>
        </article>
      </div>

      <p v-if="err" class="err">
        {{ err }}
        <button v-if="!companion" type="button" class="retry-inline" @click="boot">重试</button>
        <RouterLink v-if="quotaBlocked" class="err-link" to="/me">查看用量</RouterLink>
      </p>
      <form class="composer" @submit.prevent="send">
        <textarea
          ref="inputEl"
          v-model="input"
          rows="2"
          :placeholder="
            quotaBlocked
              ? '配额已用尽，请联系学校管理员开通用量包'
              : '输入问题，Enter 发送（Shift+Enter 换行）'
          "
          :disabled="streaming || quotaBlocked"
          @keydown.enter.exact.prevent="send"
        />
        <div class="actions">
          <button v-if="streaming" type="button" class="stop" @click="stop">停止</button>
          <button type="submit" :disabled="streaming || quotaBlocked || !input.trim()">发送</button>
        </div>
      </form>
    </section>
  </div>
  <div v-else class="page">
    <p v-if="loading">加载中…</p>
    <p v-else>{{ err || '助手不可用' }}</p>
    <button v-if="err" type="button" class="retry-inline" @click="boot">重试</button>
    <RouterLink to="/ai">返回学伴列表</RouterLink>
  </div>
</template>

<style scoped>
.chat {
  display: grid;
  grid-template-columns: 260px 1fr;
  width: min(1100px, 100%);
  margin: 0 auto;
  min-height: calc(100vh - 120px);
  padding: 12px 16px 24px;
  gap: 14px;
  position: relative;
}
.side {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 18px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 3;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 40, 35, 0.28);
  z-index: 2;
}
.back {
  color: var(--brand);
  font-size: 0.9rem;
}
.who {
  display: flex;
  gap: 10px;
  align-items: center;
}
.avatar {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: var(--brand);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
}
.dot {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
  border: 2px solid #fff;
}
.dot.on {
  background: #1a8f7a;
}
.who h1 {
  margin: 0;
  font-size: 1.05rem;
  font-family: 'Noto Serif SC', serif;
}
.who p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}
.quota {
  padding: 10px;
  border-radius: 12px;
  background: #f4faf8;
  border: 1px solid rgba(15, 107, 92, 0.12);
  display: grid;
  gap: 8px;
  font-size: 0.78rem;
}
.quota.warn {
  background: #fff7f0;
  border-color: rgba(180, 90, 40, 0.25);
}
.quota-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted);
}
.quota-head a {
  color: var(--brand);
  white-space: nowrap;
}
.qbar span {
  display: block;
  margin-bottom: 4px;
  color: var(--brand-deep);
}
.qbar i {
  display: block;
  height: 6px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.12);
  overflow: hidden;
}
.qbar b {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--brand), #e8a317);
}
.quota.warn .qbar b {
  background: linear-gradient(90deg, #c45c26, #e8a317);
}
.new {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px;
  cursor: pointer;
}
.sessions {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  flex: 1;
}
.sessions li {
  padding: 8px 4px 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  color: var(--muted);
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 2px;
}
.stitle {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rename {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(15, 107, 92, 0.3);
  border-radius: 6px;
  padding: 4px 6px;
  font: inherit;
  font-size: 0.85rem;
}
.ren,
.del {
  border: 0;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.95rem;
  line-height: 1;
  padding: 2px 5px;
  border-radius: 6px;
}
.ren:hover {
  background: rgba(15, 107, 92, 0.1);
  color: var(--brand);
}
.del:hover {
  background: rgba(180, 60, 40, 0.1);
  color: #b42318;
}
.side-empty {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}
.main-top {
  display: none;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(15, 107, 92, 0.1);
}
.side-toggle {
  border: 1px solid rgba(15, 107, 92, 0.25);
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--brand);
}
.main-title {
  font-weight: 600;
  font-size: 0.95rem;
}
.sessions li.active,
.sessions li:hover {
  background: rgba(15, 107, 92, 0.08);
  color: var(--brand-deep);
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 18px;
  overflow: hidden;
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 18px;
  min-height: 420px;
}
.empty {
  color: var(--muted);
  padding: 40px 12px;
  text-align: center;
}
.suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}
.chip {
  border: 1px solid rgba(15, 107, 92, 0.22);
  background: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 0.88rem;
  color: var(--brand-deep);
}
.chip:hover:not(:disabled) {
  border-color: var(--brand);
  background: rgba(15, 107, 92, 0.06);
}
.chip:disabled {
  opacity: 0.5;
}
.msg {
  display: flex;
  margin-bottom: 12px;
}
.msg.user {
  justify-content: flex-end;
}
.bubble {
  max-width: min(680px, 92%);
  padding: 12px 14px;
  border-radius: 16px;
  background: #f3f7f6;
}
.msg.user .bubble {
  background: rgba(15, 107, 92, 0.12);
}
.bubble pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.65;
}
.md :deep(p) {
  margin: 0 0 0.6em;
  line-height: 1.65;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(ul),
.md :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.3em;
}
.md :deep(li) {
  margin: 0.2em 0;
  line-height: 1.55;
}
.md :deep(.md-h) {
  margin: 0.6em 0 0.35em;
  font-family: 'Noto Serif SC', serif;
  font-size: 1.05rem;
}
.md :deep(.md-code) {
  margin: 8px 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #e8f0ee;
  overflow: auto;
  font-size: 0.85rem;
}
.md :deep(.md-inline) {
  background: rgba(15, 107, 92, 0.1);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.9em;
}
.md :deep(a) {
  color: var(--brand);
}
.cursor {
  animation: blink 1s step-end infinite;
  color: var(--brand);
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.cites {
  margin-top: 10px;
  display: grid;
  gap: 6px;
}
.cite {
  border-left: 3px solid var(--accent, #e8a317);
  padding: 4px 0 4px 8px;
  font-size: 0.82rem;
  color: var(--muted);
  text-align: left;
  background: transparent;
  border-top: 0;
  border-right: 0;
  border-bottom: 0;
  cursor: pointer;
  width: 100%;
}
.cite strong {
  display: block;
  color: var(--brand-deep);
}
.cite .snip {
  display: block;
}
.msg-actions {
  margin-top: 8px;
}
.retry {
  border: 1px solid rgba(15, 107, 92, 0.25);
  background: #fff;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.8rem;
  color: var(--brand);
  cursor: pointer;
}
.retry:disabled {
  opacity: 0.5;
}
.composer {
  border-top: 1px solid rgba(15, 107, 92, 0.1);
  padding: 12px;
  display: grid;
  gap: 8px;
}
.composer textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid rgba(15, 107, 92, 0.2);
  border-radius: 12px;
  padding: 12px;
  font: inherit;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.actions button {
  border: none;
  background: var(--brand);
  color: #fff;
  border-radius: 999px;
  padding: 10px 18px;
  cursor: pointer;
}
.actions button:disabled {
  opacity: 0.5;
}
.stop {
  background: #8a4b3a !important;
}
.err {
  color: #a35;
  margin: 0 12px;
  font-size: 0.9rem;
}
.err-link,
.retry-inline {
  margin-left: 8px;
  color: var(--brand);
  font-weight: 600;
  background: none;
  border: 0;
  cursor: pointer;
  font: inherit;
}
.page {
  padding: 40px;
  display: grid;
  gap: 10px;
}
@media (max-width: 860px) {
  .chat {
    grid-template-columns: 1fr;
  }
  .side {
    position: fixed;
    left: 12px;
    top: calc(var(--nav-h, 64px) + 12px);
    bottom: 12px;
    width: min(300px, calc(100vw - 48px));
    max-height: none;
    box-shadow: 0 12px 40px rgba(15, 40, 35, 0.18);
  }
  .main-top {
    display: flex;
  }
  .side-collapsed .side {
    display: none;
  }
}
</style>
