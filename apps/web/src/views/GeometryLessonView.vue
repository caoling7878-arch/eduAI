<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { geometryLessons } from '../data/courses'
import { api } from '../lib/api'
import { useAuth } from '../stores/auth'

const props = defineProps<{ lessonId: string }>()
const auth = useAuth()
const lesson = computed(() => geometryLessons.find((l) => l.id === props.lessonId))
const dwellMs = ref(0)
const practice = ref<{
  knowledge_points: string[]
  mode?: string
  questions: Array<{
    id: number
    type: string
    stem: string
    options?: string[]
    knowledge_points: string
    difficulty: number
    reason: string
  }>
} | null>(null)
const showPractice = ref(false)
const answers = reactive<Record<number, string>>({})
const checks = reactive<Record<number, { correct: boolean; analysis: string }>>({})
let timer: number | undefined
let completed = false

async function loadPractice() {
  if (!lesson.value) return
  try {
    practice.value = await api(`/labs/pages/${lesson.value.id}/practice?limit=5`)
  } catch {
    practice.value = null
  }
}

function togglePractice() {
  showPractice.value = !showPractice.value
  if (showPractice.value) void loadPractice()
}

async function syncProgress(status: 'started' | 'completed') {
  if (!lesson.value) return
  await auth.track(
    'geometry-lab',
    lesson.value.id,
    status,
    {
      title: lesson.value.title,
      dwell_sec: Math.round(dwellMs.value / 1000),
    },
    status === 'completed' ? 100 : 20,
  )
  if (status === 'completed') {
    showPractice.value = true
    await loadPractice()
  }
}

async function check(qid: number) {
  const r = await api<{ correct: boolean; analysis: string }>('/labs/practice/check', {
    method: 'POST',
    body: JSON.stringify({ question_id: qid, answer: answers[qid] || '' }),
  })
  checks[qid] = r
}

function startTimer() {
  window.clearInterval(timer)
  dwellMs.value = 0
  completed = false
  showPractice.value = false
  practice.value = null
  timer = window.setInterval(() => {
    dwellMs.value += 1000
    if (!completed && dwellMs.value >= 20_000) {
      completed = true
      void syncProgress('completed')
    }
  }, 1000)
}

watch(
  () => props.lessonId,
  () => {
    void syncProgress('started')
    startTimer()
  },
)

onMounted(() => {
  void syncProgress('started')
  startTimer()
})

onUnmounted(() => {
  window.clearInterval(timer)
})
</script>

<template>
  <div v-if="lesson" class="lab-page fade-up">
    <div class="bar">
      <RouterLink class="back" to="/courses/geometry-lab">← 实验室</RouterLink>
      <div class="meta">
        <h1>{{ lesson.title }}</h1>
        <p>
          {{ lesson.blurb }}
          <template v-if="auth.isLoggedIn.value">
            · 已停留 {{ Math.floor(dwellMs / 1000) }}s
            <span v-if="auth.isCompleted('geometry-lab', lesson.id)">· 已记入进度</span>
          </template>
        </p>
      </div>
      <div class="actions">
        <button
          v-if="auth.isLoggedIn.value"
          class="btn btn-primary"
          type="button"
          @click="syncProgress('completed')"
        >
          标记学完
        </button>
        <button class="btn btn-ghost" type="button" @click="togglePractice">
          {{ lesson.id === 'random-7' ? '变式巩固练习' : '相关练习' }}
        </button>
        <a class="btn btn-ghost" :href="lesson.path" target="_blank" rel="noopener">新窗口打开</a>
      </div>
    </div>
    <div class="stage">
      <iframe class="frame" :src="lesson.path" :title="lesson.title" />
    </div>
    <aside v-if="showPractice" class="practice-panel">
      <div class="practice-head">
        <h2>{{ practice?.mode === 'variant' ? '变式巩固练习' : '学完推荐练习' }}</h2>
        <button type="button" class="close" @click="showPractice = false">关闭</button>
      </div>
      <p v-if="practice?.knowledge_points?.length" class="kps">
        知识点：{{ practice.knowledge_points.join('、') }}
      </p>
      <ul v-if="practice?.questions?.length">
        <li v-for="q in practice.questions" :key="q.id">
          <div class="reason">{{ q.reason }}</div>
          <p class="qstem">{{ q.stem }}</p>
          <div v-if="q.options?.length" class="opts">
            <label v-for="(opt, idx) in q.options" :key="idx">
              <input v-model="answers[q.id]" type="radio" :value="String(idx)" />
              {{ opt }}
            </label>
          </div>
          <input v-else v-model="answers[q.id]" class="blank" placeholder="填写答案" />
          <button type="button" class="check" @click="check(q.id)">核对</button>
          <p v-if="checks[q.id]" class="verdict" :class="{ ok: checks[q.id].correct }">
            {{ checks[q.id].correct ? '正确' : '再想想' }} · {{ checks[q.id].analysis }}
          </p>
        </li>
      </ul>
      <p v-else class="empty">暂无关联题目，可先去薄弱推荐看看。</p>
      <RouterLink class="go" to="/recommend">薄弱点练习推送</RouterLink>
      <RouterLink class="go ghost" to="/practice">去试卷练习</RouterLink>
    </aside>
  </div>
  <div v-else class="lab-page">
    <p>未找到该课页。</p>
    <RouterLink to="/courses/geometry-lab">返回实验室</RouterLink>
  </div>
</template>

<style scoped>
.lab-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--nav-h) - 24px);
  min-height: 680px;
  gap: 10px;
  position: relative;
}

.bar {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
}

.back {
  color: var(--muted);
  white-space: nowrap;
}

.meta {
  min-width: 0;
}

h1 {
  margin: 0 0 2px;
  font-family: var(--font-display);
  font-size: clamp(1.05rem, 1.6vw, 1.35rem);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

p {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.stage {
  flex: 1;
  min-height: 0;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  background: #edf3f8;
}

.frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #edf3f8;
}

.practice-panel {
  position: absolute;
  right: 12px;
  top: 72px;
  bottom: 12px;
  width: min(380px, calc(100% - 24px));
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(15, 107, 92, 0.18);
  border-radius: 14px;
  box-shadow: 0 12px 40px rgba(15, 40, 35, 0.12);
  padding: 14px;
  overflow: auto;
  z-index: 5;
}

.practice-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.practice-head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.05rem;
}

.close {
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.kps {
  margin-bottom: 10px !important;
  white-space: normal !important;
  color: var(--brand-deep) !important;
}

.practice-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

.practice-panel li {
  padding: 10px;
  border-radius: 10px;
  background: rgba(15, 107, 92, 0.05);
  border: 1px solid rgba(15, 107, 92, 0.1);
}

.reason {
  color: var(--brand);
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.qstem {
  white-space: normal !important;
  color: #1a2e2a !important;
  margin-bottom: 8px !important;
  font-size: 0.92rem !important;
}

.opts {
  display: grid;
  gap: 4px;
  margin-bottom: 8px;
}

.opts label {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  white-space: normal;
  color: #1a2e2a;
  font-size: 0.88rem;
}

.blank {
  width: 100%;
  margin-bottom: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
}

.check {
  border: 0;
  border-radius: 999px;
  padding: 5px 12px;
  background: var(--brand);
  color: #fff;
  cursor: pointer;
  font-size: 0.82rem;
}

.verdict {
  margin-top: 8px !important;
  white-space: normal !important;
  color: #b42318 !important;
  font-size: 0.85rem !important;
}

.verdict.ok {
  color: var(--brand-deep) !important;
}

.empty {
  white-space: normal !important;
  margin: 12px 0 !important;
}

.go {
  display: inline-block;
  margin: 12px 8px 0 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-size: 0.85rem;
}

.go.ghost {
  background: transparent;
  color: var(--brand);
  border: 1px solid rgba(15, 107, 92, 0.3);
}

@media (max-width: 900px) {
  .lab-page {
    min-height: 560px;
    height: calc(100vh - var(--nav-h) - 16px);
  }

  .bar {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  h1,
  p {
    white-space: normal;
  }

  .practice-panel {
    top: auto;
    bottom: 0;
    right: 0;
    left: 0;
    width: 100%;
    max-height: 45%;
    border-radius: 14px 14px 0 0;
  }
}
</style>
