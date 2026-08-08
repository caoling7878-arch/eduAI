<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { englishScenarios, hotCourses, type EnglishScenario } from '../data/courses'
import { coachReply, type ChatMessage } from '../lib/englishCoach'
import {
  createRecognizer,
  getSpeechSupport,
  speakEnglish,
  stopSpeaking,
} from '../lib/speech'
import { scoreSpeech } from '../lib/api'
import ProgressBar from '../components/ProgressBar.vue'
import { useAuth } from '../stores/auth'

const course = hotCourses.find((c) => c.id === 'english-coach')!
const auth = useAuth()
const support = getSpeechSupport()

const scenario = ref<EnglishScenario>(englishScenarios[0]!)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const busy = ref(false)
const listening = ref(false)
const speaking = ref(false)
const autoSpeak = ref(true)
const source = ref<'local' | 'api'>('local')
const voiceEngine = ref<'neural' | 'browser' | ''>('')
const voiceError = ref('')
const speechScore = ref<{ score: number; level: string; feedback: string } | null>(null)
const listEl = ref<HTMLElement | null>(null)
let recognizer: ReturnType<typeof createRecognizer> | null = null

const userTurns = computed(() => messages.value.filter((m) => m.role === 'user').length)
const percent = computed(() => auth.coursePercent('english-coach'))

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function bootScenario(s: EnglishScenario) {
  stopSpeaking()
  stopListening()
  scenario.value = s
  messages.value = [
    {
      id: uid(),
      role: 'assistant',
      content: `Scene: ${s.setting}\nGoals: ${s.goals.join(' · ')}\n\nYou can start with:\n“${s.starter}”`,
    },
  ]
  draft.value = s.starter
  source.value = 'local'
  voiceError.value = ''
  void auth.track('english-coach', s.id, 'started', { scenario: s.title })
}

bootScenario(scenario.value)

watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  },
)

async function markProgress() {
  const turns = userTurns.value
  if (turns >= 3) {
    await auth.track('english-coach', scenario.value.id, 'completed', {
      scenario: scenario.value.title,
      turns,
    }, Math.min(100, 40 + turns * 10))
  } else if (turns >= 1) {
    await auth.track('english-coach', scenario.value.id, 'started', {
      scenario: scenario.value.title,
      turns,
    })
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text || busy.value) return
  messages.value.push({ id: uid(), role: 'user', content: text })
  draft.value = ''
  busy.value = true
  try {
    const res = await coachReply(scenario.value, messages.value)
    source.value = res.source
    messages.value.push({ id: uid(), role: 'assistant', content: res.content })
    await markProgress()
    if (autoSpeak.value && support.synthesis) {
      await playVoice(res.content)
    }
  } finally {
    busy.value = false
  }
}

async function playVoice(content: string) {
  speaking.value = true
  voiceError.value = ''
  try {
    const result = await speakEnglish(content, { gender: undefined, lang: 'en' })
    voiceEngine.value = result.engine
    if (result.fallback) {
      voiceError.value = '神经朗读暂不可用，已切换系统音色'
    }
  } catch (err) {
    voiceError.value = err instanceof Error ? err.message : '播报失败'
  } finally {
    speaking.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void send()
  }
}

function speakLast() {
  const last = [...messages.value].reverse().find((m) => m.role === 'assistant')
  if (!last) return
  void playVoice(last.content)
}

function stopListening() {
  if (recognizer) {
    try {
      recognizer.stop()
    } catch {
      /* ignore */
    }
    recognizer = null
  }
  listening.value = false
}

function toggleListen() {
  voiceError.value = ''
  if (!support.recognition) {
    voiceError.value = '当前浏览器不支持语音识别，请使用 Chrome / Edge'
    return
  }
  if (listening.value) {
    stopListening()
    return
  }
  stopSpeaking()
  try {
    recognizer = createRecognizer({
      lang: 'en-US',
      onInterim: (text) => {
        draft.value = text
      },
      onFinal: (text) => {
        draft.value = text
        // 只用情景 starter 作对照句，避免把整段 Scene/Goals 开场送入评分
        const expected = (scenario.value.starter || '').trim() || text
        void scoreSpeech(expected.slice(0, 280), text)
          .then((r) => {
            speechScore.value = { score: r.score, level: r.level, feedback: r.feedback }
          })
          .catch(() => {
            speechScore.value = null
          })
      },
      onError: (message) => {
        voiceError.value = message
        listening.value = false
      },
      onEnd: () => {
        listening.value = false
        recognizer = null
      },
    })
    recognizer.start()
    listening.value = true
  } catch (err) {
    voiceError.value = err instanceof Error ? err.message : '无法启动麦克风'
    listening.value = false
  }
}

onBeforeUnmount(() => {
  stopListening()
  stopSpeaking()
})
</script>

<template>
  <div class="page fade-up">
    <RouterLink class="back" to="/">← 返回首页</RouterLink>
    <div class="head">
      <div>
        <p class="eyebrow">{{ course.tag }} · 语音对话</p>
        <h1 class="page-title">{{ course.title }}</h1>
        <p class="lead">
          支持麦克风说英语、听陪练朗读。
          {{
            auth.isLoggedIn.value
              ? '每个情景完成约 3 轮对话后记为已完成。'
              : '登录后可把情景进度同步到账号。'
          }}
        </p>
        <ProgressBar
          v-if="auth.isLoggedIn.value"
          class="course-progress"
          :percent="percent"
          label="英语陪练总进度"
        />
      </div>
      <div class="badges">
        <span class="mode">
          <i class="live" />
          {{ source === 'api' ? '大模型陪练' : '本地情景陪练' }}
        </span>
        <RouterLink v-if="!auth.isLoggedIn.value" class="login-hint" to="/auth?redirect=/courses/english-coach">登录同步进度</RouterLink>
      </div>
    </div>

    <div class="layout">
      <aside class="panel scenarios">
        <h2>情景</h2>
        <div class="scenario-list">
          <button
            v-for="s in englishScenarios"
            :key="s.id"
            class="scenario"
            type="button"
            :class="{
              active: scenario.id === s.id,
              done: auth.isCompleted('english-coach', s.id),
            }"
            @click="bootScenario(s)"
          >
            <strong>{{ s.title }}</strong>
            <span>
              CEFR {{ s.level }}
              <template v-if="auth.isCompleted('english-coach', s.id)"> · 已完成</template>
            </span>
          </button>
        </div>
      </aside>

      <section class="panel chat">
        <div class="voice-bar">
          <label class="auto">
            <input v-model="autoSpeak" type="checkbox" :disabled="!support.synthesis" />
            自动朗读回复
          </label>
          <span v-if="voiceEngine" class="engine" :data-engine="voiceEngine">
            {{ voiceEngine === 'neural' ? '神经音色' : '系统音色' }}
            <template v-if="speaking"> · 朗读中</template>
          </span>
          <button
            class="btn btn-ghost"
            type="button"
            :disabled="!support.synthesis || speaking"
            @click="speakLast"
          >
            {{ speaking ? '朗读中…' : '朗读上一条' }}
          </button>
          <button
            class="btn"
            :class="listening ? 'btn-accent' : 'btn-primary'"
            type="button"
            :disabled="!support.recognition || busy"
            @click="toggleListen"
          >
            {{ listening ? '停止录音' : '开始说话' }}
          </button>
        </div>
        <p v-if="voiceError" class="voice-error">{{ voiceError }}</p>
        <p v-if="speechScore" class="speech-score">
          语音评分 {{ speechScore.score }} · {{ speechScore.level }}
          <span>对照句：「{{ scenario.starter }}」· {{ speechScore.feedback }}</span>
        </p>
        <p class="voice-hint">
          优先使用平台神经朗读；不可用时自动切换系统音色。
          <template v-if="!support.recognition"> 语音识别需 Chrome / Edge。</template>
        </p>

        <div ref="listEl" class="messages">
          <div v-for="m in messages" :key="m.id" class="bubble" :class="m.role">
            <pre>{{ m.content }}</pre>
          </div>
          <div v-if="busy" class="bubble assistant typing">陪练正在输入…</div>
        </div>
        <div class="composer">
          <textarea
            v-model="draft"
            rows="3"
            placeholder="用英语回复，或点击「开始说话」…（Enter 发送）"
            @keydown="onKeydown"
          />
          <button class="btn btn-accent" type="button" :disabled="busy || !draft.trim()" @click="send">
            发送
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.back {
  display: inline-block;
  color: var(--muted);
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 22px;
}

.course-progress {
  max-width: 280px;
  margin-top: 12px;
}

.badges {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.mode,
.login-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 0.85rem;
  white-space: nowrap;
}

.mode {
  background: var(--accent-soft);
  color: var(--ink);
}

.login-hint {
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-weight: 600;
}

.live {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
  animation: pulseDot 1.6s ease-in-out infinite;
}

.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
  min-height: 560px;
}

.scenarios {
  padding: 16px;
}

.scenarios h2 {
  margin: 0 0 12px;
  font-size: 0.95rem;
  color: var(--muted);
  font-weight: 600;
}

.scenario {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  display: grid;
  gap: 4px;
  margin-bottom: 6px;
}

.scenario span {
  color: var(--muted);
  font-size: 0.8rem;
}

.scenario.active,
.scenario:hover {
  background: var(--brand-soft);
  border-color: rgba(15, 107, 92, 0.2);
}

.scenario.done strong::after {
  content: ' ✓';
  color: var(--brand);
}

.chat {
  display: flex;
  flex-direction: column;
  min-height: 560px;
  overflow: hidden;
}

.voice-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.55);
}

.auto {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.88rem;
  color: var(--muted);
  margin-right: auto;
}

.engine {
  font-size: 0.8rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-deep);
}

.engine[data-engine='browser'] {
  background: rgba(20, 33, 43, 0.06);
  color: var(--muted);
}

.voice-error {
  margin: 0;
  padding: 8px 14px 0;
  color: #b42318;
  font-size: 0.86rem;
}

.speech-score {
  margin: 8px 14px 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 107, 92, 0.08);
  color: var(--brand-deep);
  font-size: 0.9rem;
  text-align: left;
}

.speech-score span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 0.84rem;
}

.voice-hint {
  margin: 0;
  padding: 8px 14px 0;
  color: var(--muted);
  font-size: 0.86rem;
}

.messages {
  flex: 1;
  overflow: auto;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bubble {
  max-width: min(520px, 92%);
  padding: 12px 14px;
  border-radius: 14px;
  line-height: 1.55;
}

.bubble pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
}

.bubble.user {
  align-self: flex-end;
  background: var(--brand);
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble.assistant {
  align-self: flex-start;
  background: #f7faf8;
  border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
}

.typing {
  color: var(--muted);
  font-style: italic;
}

.composer {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 14px;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.65);
}

textarea {
  resize: vertical;
  min-height: 72px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: white;
  color: var(--ink);
}

textarea:focus {
  outline: 2px solid var(--brand-soft);
  border-color: rgba(15, 107, 92, 0.45);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 840px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .scenarios {
    padding: 12px;
  }

  .scenario-list {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
  }

  .scenario {
    flex: 0 0 auto;
    width: auto;
    min-width: 140px;
    margin-bottom: 0;
  }

  .chat {
    min-height: 420px;
  }

  .head {
    flex-direction: column;
  }

  .badges {
    justify-items: start;
  }
}
</style>
