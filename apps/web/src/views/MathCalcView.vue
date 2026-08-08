<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import MathExpr from '../components/MathExpr.vue'
import { api } from '../lib/api'
import { useAuth } from '../stores/auth'

type Grade = {
  grade: number
  topic: string
  prompt_hint: string
  bank_count: number
}

type Prefs = {
  grade: number
  daily_count: number
  topic: string
  prompt_hint: string
}

type Item = {
  id: number
  grade: number
  topic: string
  stem: string
  prompt_hint: string
  answer_kind: string
}

type Today = {
  day: string
  grade: number
  topic: string
  prompt_hint: string
  submitted: boolean
  correct_count: number
  total_count: number
  elapsed_seconds: number
  items: Item[]
  answers: Record<string, string>
  results: Record<string, { correct?: boolean; user_answer?: string; correct_answer?: string; fixed?: boolean }>
}

type Summary = {
  course: string
  grade: number
  topic: string
  daily_count: number
  bank_count: number
  today_submitted: boolean
  today_correct: number
  today_total: number
  today_elapsed_seconds: number
  wrong_open: number
  prompt_hint: string
  streak_days: number
  completed_days: number
  need_reminder: boolean
}

type HistoryRow = {
  day: string
  grade: number
  topic: string
  correct_count: number
  total_count: number
  elapsed_seconds: number
  accuracy: number
  submitted: boolean
}

const auth = useAuth()
const router = useRouter()
const grades = ref<Grade[]>([])
const summary = ref<Summary | null>(null)
const today = ref<Today | null>(null)
const historyRows = ref<HistoryRow[]>([])
const prefs = reactive<Prefs>({
  grade: 1,
  daily_count: 20,
  topic: '',
  prompt_hint: '',
})
const answers = reactive<Record<string, string>>({})
const fixDraft = reactive<Record<string, string>>({})
const showSettings = ref(false)
const showHistory = ref(false)
const saving = ref(false)
const submitting = ref(false)
const tip = ref('')
const draftTip = ref('')
const phase = ref<'practice' | 'review'>('practice')
const elapsed = ref(0)
let timerId: ReturnType<typeof setInterval> | null = null
let draftTimer: ReturnType<typeof setTimeout> | null = null
let draftSaving = false
let lastDraftAt = 0

const wrongItems = computed(() => {
  if (!today.value?.submitted) return []
  return today.value.items.filter((it) => {
    const r = today.value!.results[String(it.id)]
    return r && !r.correct && !r.fixed
  })
})

const allFixed = computed(() => today.value?.submitted && wrongItems.value.length === 0)

const timerLabel = computed(() => formatElapsed(elapsed.value))

function formatElapsed(sec: number) {
  const s = Math.max(0, Math.floor(sec || 0))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m} 分 ${String(r).padStart(2, '0')} 秒`
}

function stopTimer() {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
}

function startTimer(from = 0) {
  stopTimer()
  elapsed.value = from
  timerId = setInterval(() => {
    elapsed.value += 1
    if (elapsed.value > 0 && elapsed.value % 30 === 0) {
      void persistDraft(true)
    }
  }, 1000)
}

function displayStem(it: Item) {
  // 比大小：题干里的 ○ 留给学生填，展示时去掉 ○ 两侧空白更像空白圈
  if (it.answer_kind === 'compare') {
    return it.stem.replace(/\s*○\s*/, ' ○ ')
  }
  return it.stem
}

async function persistDraft(silent = false) {
  if (!today.value || today.value.submitted || draftSaving) return
  const now = Date.now()
  if (silent && now - lastDraftAt < 8000) return
  draftSaving = true
  try {
    await api('/math-calc/today/draft', {
      method: 'POST',
      body: JSON.stringify({ answers, elapsed_seconds: elapsed.value }),
    })
    lastDraftAt = Date.now()
    if (!silent) {
      draftTip.value = '草稿已保存'
      setTimeout(() => {
        if (draftTip.value === '草稿已保存') draftTip.value = ''
      }, 1800)
    }
  } catch {
    /* 自动保存失败不打断作答 */
  } finally {
    draftSaving = false
  }
}

function scheduleDraft() {
  if (!today.value || today.value.submitted) return
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => {
    void persistDraft(false)
  }, 1200)
}

function onPageHide() {
  void persistDraft(true)
}

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/courses/math-calc' } })
    return
  }
  tip.value = ''
  grades.value = await api<Grade[]>('/math-calc/grades')
  const p = await api<Prefs>('/math-calc/prefs')
  Object.assign(prefs, p)
  summary.value = await api<Summary>('/math-calc/summary')
  historyRows.value = await api<HistoryRow[]>('/math-calc/history?limit=14')
  const t = await api<Today>('/math-calc/today')
  today.value = t
  Object.keys(answers).forEach((k) => delete answers[k])
  Object.assign(answers, t.answers || {})
  phase.value = t.submitted ? 'review' : 'practice'
  if (t.submitted) {
    stopTimer()
    elapsed.value = t.elapsed_seconds || 0
  } else {
    startTimer(t.elapsed_seconds || 0)
    if (Object.keys(t.answers || {}).length) {
      draftTip.value = '已恢复上次未提交的草稿'
    }
  }
  await auth.track('math-calc', 'course', 'started', { title: '小学数学计算专项' }, 5)
}

async function savePrefs() {
  saving.value = true
  tip.value = ''
  try {
    if (prefs.daily_count < 10 || prefs.daily_count > 100) {
      tip.value = '每日题量请在 10–100 之间'
      return
    }
    const p = await api<Prefs>('/math-calc/prefs', {
      method: 'PUT',
      body: JSON.stringify({ grade: prefs.grade, daily_count: prefs.daily_count }),
    })
    Object.assign(prefs, p)
    tip.value = '已保存，正在刷新今日练习页'
    showSettings.value = false
    await load()
  } catch (e) {
    tip.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function submit() {
  if (!today.value || today.value.submitted) return
  submitting.value = true
  tip.value = ''
  try {
    stopTimer()
    const t = await api<Today>('/math-calc/today/submit', {
      method: 'POST',
      body: JSON.stringify({ answers, elapsed_seconds: elapsed.value }),
    })
    today.value = t
    phase.value = 'review'
    draftTip.value = ''
    summary.value = await api<Summary>('/math-calc/summary')
    historyRows.value = await api<HistoryRow[]>('/math-calc/history?limit=14')
    const wrong = t.total_count - t.correct_count
    tip.value =
      wrong > 0
        ? `已提交：对 ${t.correct_count} 题，错 ${wrong} 题，用时 ${formatElapsed(t.elapsed_seconds)}。请订正错题。`
        : `全对！今日 ${t.total_count} 题，用时 ${formatElapsed(t.elapsed_seconds)}。`
    await auth.track(
      'math-calc',
      'course',
      'completed',
      { title: '小学数学计算专项', correct: t.correct_count, total: t.total_count },
      Math.round((t.correct_count / Math.max(t.total_count, 1)) * 100),
    )
  } catch (e) {
    tip.value = e instanceof Error ? e.message : '提交失败'
    if (!today.value?.submitted) startTimer(elapsed.value)
  } finally {
    submitting.value = false
  }
}

async function fixOne(itemId: number) {
  tip.value = ''
  try {
    const r = await api<{ correct: boolean; message: string }>('/math-calc/fix', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, answer: fixDraft[itemId] || '' }),
    })
    tip.value = r.message
    const t = await api<Today>('/math-calc/today')
    today.value = t
    summary.value = await api<Summary>('/math-calc/summary')
  } catch (e) {
    tip.value = e instanceof Error ? e.message : '订正失败'
  }
}

function resultClass(id: number) {
  const r = today.value?.results[String(id)]
  if (!r) return ''
  if (r.correct || r.fixed) return 'ok'
  return 'bad'
}

function onVisibility() {
  if (document.visibilityState === 'hidden') onPageHide()
}

watch(answers, () => scheduleDraft(), { deep: true })

onMounted(() => {
  void load()
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pagehide', onPageHide)
})
onUnmounted(() => {
  stopTimer()
  if (draftTimer) clearTimeout(draftTimer)
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('pagehide', onPageHide)
  void persistDraft(true)
})
</script>

<template>
  <div class="page">
    <header class="head">
      <div>
        <p class="kicker">学习中心</p>
        <h1>小学数学计算专项练习</h1>
        <p class="sub">
          依据 1–6 年级计算专项题库 · 每日一页 · 提交判分 · 错题订正入库
        </p>
      </div>
      <div class="head-actions">
        <button type="button" class="ghost-btn" @click="showSettings = !showSettings">
          {{ showSettings ? '收起设置' : '年级与题量' }}
        </button>
        <button type="button" class="ghost-btn" @click="showHistory = !showHistory">
          {{ showHistory ? '收起记录' : '练习记录' }}
        </button>
        <RouterLink class="ghost-btn" to="/wrongbook">错题本</RouterLink>
        <RouterLink class="ghost-btn" to="/">回首页</RouterLink>
      </div>
    </header>

    <section v-if="summary" class="stats">
      <div>
        <b>{{ summary.grade }} 年级</b>
        <span>{{ summary.topic }}</span>
      </div>
      <div>
        <b>{{ summary.daily_count }}</b>
        <span>每日题量</span>
      </div>
      <div>
        <b>{{ summary.streak_days }}</b>
        <span>连续打卡</span>
      </div>
      <div>
        <b>{{ summary.completed_days }}</b>
        <span>累计天数</span>
      </div>
      <div>
        <b>{{ summary.wrong_open }}</b>
        <span>未掌握错题</span>
      </div>
      <div v-if="summary.today_submitted">
        <b>{{ summary.today_correct }}/{{ summary.today_total }}</b>
        <span>今日得分</span>
      </div>
      <div v-else>
        <b>{{ timerLabel }}</b>
        <span>计时中</span>
      </div>
    </section>

    <section v-if="showSettings" class="settings">
      <h3>选择年级与每日题量</h3>
      <div class="grade-grid">
        <button
          v-for="g in grades"
          :key="g.grade"
          type="button"
          class="grade-card"
          :class="{ active: prefs.grade === g.grade }"
          @click="prefs.grade = g.grade"
        >
          <em>{{ g.grade }} 年级</em>
          <span>{{ g.topic }}</span>
          <small>{{ g.bank_count }} 题</small>
        </button>
      </div>
      <label class="count-lab">
        每日练习题量（10–100）
        <input v-model.number="prefs.daily_count" type="number" min="10" max="100" />
      </label>
      <p class="hint">{{ prefs.prompt_hint || '保存后将按新设置生成今日练习页（未提交时可重建）。' }}</p>
      <div class="settings-actions">
        <button type="button" class="save" :disabled="saving" @click="savePrefs">
          {{ saving ? '保存中…' : '保存并刷新今日页' }}
        </button>
      </div>
    </section>

    <section v-if="showHistory" class="history">
      <h3>近两周练习记录</h3>
      <p v-if="!historyRows.length" class="hint">暂无记录，完成今日练习后会出现在这里。</p>
      <ul v-else>
        <li v-for="h in historyRows" :key="h.day">
          <span class="hd">{{ h.day }}</span>
          <span>{{ h.grade }}年级 · {{ h.topic }}</span>
          <span class="score">{{ h.correct_count }}/{{ h.total_count }}（{{ h.accuracy }}%）</span>
          <span class="time">{{ formatElapsed(h.elapsed_seconds) }}</span>
        </li>
      </ul>
    </section>

    <p v-if="tip" class="tip">{{ tip }}</p>
    <p v-else-if="draftTip" class="tip draft">{{ draftTip }}</p>

    <section v-if="today && phase === 'practice'" class="sheet">
      <div class="sheet-head">
        <div>
          <h2>{{ today.day }} · {{ today.grade }}年级 · {{ today.topic }}</h2>
          <p>{{ today.prompt_hint }} · 共 {{ today.items.length }} 题</p>
        </div>
        <div class="timer-pill" aria-live="polite">⏱ {{ timerLabel }}</div>
      </div>
      <ol class="q-list cols">
        <li v-for="(it, i) in today.items" :key="it.id">
          <span class="no">{{ i + 1 }}.</span>
          <MathExpr class="stem" :text="displayStem(it)" />
          <input
            v-model="answers[String(it.id)]"
            class="ans"
            :class="{ compare: it.answer_kind === 'compare' }"
            :placeholder="
              it.answer_kind === 'compare' ? '> < =' : it.answer_kind === 'fraction' ? '如 5/6' : '答案'
            "
            autocomplete="off"
          />
        </li>
      </ol>
      <div class="footer-actions">
        <button type="button" class="save" :disabled="submitting" @click="submit">
          {{ submitting ? '判分中…' : '提交判分' }}
        </button>
      </div>
    </section>

    <section v-if="today && phase === 'review'" class="sheet">
      <div class="sheet-head">
        <div>
          <h2>判分结果 · {{ today.correct_count }}/{{ today.total_count }}</h2>
          <p v-if="!allFixed">请订正错题；订正正确后将标记错题本为已掌握。</p>
          <p v-else class="ok-msg">今日错题已全部订正完成。</p>
        </div>
        <div class="timer-pill done">用时 {{ formatElapsed(today.elapsed_seconds) }}</div>
      </div>

      <ol class="q-list cols review">
        <li v-for="(it, i) in today.items" :key="it.id" :class="resultClass(it.id)">
          <span class="no">{{ i + 1 }}.</span>
          <MathExpr class="stem" :text="displayStem(it)" />
          <span class="mark">
            <template v-if="today.results[String(it.id)]?.correct || today.results[String(it.id)]?.fixed">
              ✓
              <MathExpr
                :text="today.results[String(it.id)]?.user_answer || answers[String(it.id)] || ''"
              />
            </template>
            <template v-else>
              ✗
              <MathExpr :text="today.results[String(it.id)]?.user_answer || '（空）'" />
            </template>
          </span>
        </li>
      </ol>

      <div v-if="wrongItems.length" class="fix-box">
        <h3>错题订正（{{ wrongItems.length }}）</h3>
        <div v-for="it in wrongItems" :key="'fix-' + it.id" class="fix-row">
          <p class="stem-line"><MathExpr :text="displayStem(it)" /></p>
          <div class="fix-actions">
            <input
              v-model="fixDraft[it.id]"
              class="ans"
              :placeholder="
                it.answer_kind === 'compare' ? '填 >、< 或 =' : it.answer_kind === 'fraction' ? '如 5/6' : '重新作答'
              "
            />
            <button type="button" class="save sm" @click="fixOne(it.id)">提交订正</button>
          </div>
        </div>
      </div>

      <div class="footer-actions">
        <RouterLink class="ghost-btn" to="/wrongbook">查看错题本</RouterLink>
        <button type="button" class="ghost-btn" @click="showSettings = true">改年级/题量</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  width: min(960px, 100%);
  margin: 0 auto;
  padding: 28px 20px 72px;
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}
.kicker {
  margin: 0 0 4px;
  color: var(--muted);
  letter-spacing: 0.08em;
  font-size: 12px;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-size: clamp(1.6rem, 3vw, 2rem);
  font-weight: 700;
}
.sub {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ghost-btn {
  text-decoration: none;
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
  background: color-mix(in srgb, var(--bg) 70%, white);
  color: inherit;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.stats > div {
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(160deg, #f3f7f4, #e8f0ea);
  display: grid;
  gap: 4px;
}
.stats b {
  font-size: 1.15rem;
}
.stats span {
  color: var(--muted);
  font-size: 12px;
}
.settings,
.history {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(165deg, #fffaf2, #f4f7f5);
  border: 1px solid color-mix(in srgb, #c9a66b 25%, transparent);
}
.settings h3,
.history h3 {
  margin: 0 0 12px;
  font-family: 'Noto Serif SC', serif;
}
.history ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.history li {
  display: grid;
  grid-template-columns: 7.2rem 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  background: #fff;
  border-radius: 10px;
  font-size: 13px;
}
.history .hd {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.history .score {
  color: #2f6f57;
  font-weight: 600;
}
.history .time {
  color: var(--muted);
}
.grade-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.grade-card {
  text-align: left;
  border: 1px solid color-mix(in srgb, var(--line) 70%, transparent);
  background: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  display: grid;
  gap: 2px;
}
.grade-card.active {
  border-color: #2f6f57;
  box-shadow: inset 0 0 0 1px #2f6f57;
  background: #eff8f3;
}
.grade-card em {
  font-style: normal;
  font-weight: 700;
}
.grade-card span {
  font-size: 12px;
  color: #345;
}
.grade-card small {
  color: var(--muted);
}
.count-lab {
  display: grid;
  gap: 6px;
  font-size: 14px;
  max-width: 240px;
}
.count-lab input,
.ans {
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 15px;
  background: #fff;
}
.ans.compare {
  max-width: 72px;
  text-align: center;
}
.hint {
  color: var(--muted);
  font-size: 13px;
}
.settings-actions,
.footer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
  align-items: center;
}
.save {
  border: none;
  background: #2f6f57;
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}
.save.sm {
  padding: 8px 12px;
  font-size: 13px;
}
.save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.tip {
  padding: 10px 12px;
  border-radius: 10px;
  background: #eef6ff;
  color: #1d4a7a;
  margin: 0 0 14px;
}
.tip.draft {
  background: #eef8f4;
  color: #0f6b5c;
}
.sheet {
  border-radius: 16px;
  padding: 18px 16px 22px;
  background: linear-gradient(180deg, #ffffff, #f7faf8);
  border: 1px solid color-mix(in srgb, var(--line) 60%, transparent);
}
.sheet-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.sheet-head h2 {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 1.15rem;
}
.sheet-head p {
  margin: 6px 0 0;
  color: var(--muted);
}
.timer-pill {
  flex-shrink: 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: #e8f3ec;
  color: #1f5a42;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: 13px;
}
.timer-pill.done {
  background: #eef2f6;
  color: #445;
}
.ok-msg {
  color: #2f6f57 !important;
  font-weight: 600;
}
.q-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.q-list.cols {
  grid-template-columns: 1fr 1fr;
}
.q-list li {
  display: grid;
  grid-template-columns: 2rem 1fr minmax(72px, 110px);
  gap: 8px;
  align-items: center;
  padding: 12px;
  min-height: 3.6rem;
  border-radius: 10px;
  background: color-mix(in srgb, #f4f7f5 80%, white);
}
.q-list.review li {
  grid-template-columns: 2rem 1fr auto;
}
.q-list li.ok {
  background: #e9f7ef;
}
.q-list li.bad {
  background: #fdf0ef;
}
.stem-line {
  margin: 0;
}
.mark {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.no {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.fix-box {
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px dashed color-mix(in srgb, var(--line) 70%, transparent);
}
.fix-box h3 {
  margin: 0 0 10px;
  font-size: 1rem;
}
.fix-row {
  margin-bottom: 12px;
  padding: 10px;
  border-radius: 10px;
  background: #fff7f5;
}
.fix-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
@media (max-width: 720px) {
  .head {
    flex-direction: column;
  }
  .q-list.cols {
    grid-template-columns: 1fr;
  }
  .history li {
    grid-template-columns: 1fr 1fr;
  }
  .q-list li {
    grid-template-columns: 1.5rem 1fr;
  }
  .q-list li .ans,
  .q-list.review li .mark {
    grid-column: 2;
  }
}
</style>
