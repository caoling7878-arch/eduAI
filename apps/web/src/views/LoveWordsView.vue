<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import MorphIcon from '../components/MorphIcon.vue'
import WordMeaningArt from '../components/WordMeaningArt.vue'
import { api } from '../lib/api'
import { speakWord, speakEnglish, getTtsGender, setTtsGender, type TtsGender } from '../lib/speech'
import { useAuth } from '../stores/auth'

type Segment = {
  text: string
  type: string
  gloss: string
  icon: string
  color: string
}

type Meaning = { pos: string; text: string; example?: string; example_cn?: string; source?: string }

type Word = {
  id: number
  word: string
  phonetic: string
  meaning: string
  meanings: Meaning[]
  example: string
  level: string
  status: string
  image_key: string
  morph_story: string
  segments: Segment[]
  is_long: boolean
  scene: string
  frequency: string
  role: string
  wrong_count: number
  is_verb?: boolean
  verb_forms?: { ing: string; past: string; past_participle: string } | null
  image_url?: string | null
}

type Prefs = {
  bank: string
  daily_count: number
  show_morph: boolean
  auto_speak: boolean
}

type Bank = { id: string; name: string; available: boolean; desc: string }

type Summary = {
  course: string
  bank_name: string
  daily_count: number
  bank_total: number
  learned: number
  days_needed: number
  days_left: number
  percent: number
  stars_total: number
  stars_month: number
  streak_days: number
  streak_badge?: boolean
  stars_per_day?: number
  today_stars?: number
  stars_to_member: number
  today_completed: boolean
  need_reminder: boolean
}

type QuizItem = { word_id: number; word: string; prompt: string; options: string[] }

const auth = useAuth()
const router = useRouter()
const phase = ref<'study' | 'quiz' | 'done'>('study')
const words = ref<Word[]>([])
const idx = ref(0)
const flipped = ref(false)
const showMorph = ref(true)
const showSettings = ref(false)
const banks = ref<Bank[]>([])
const summary = ref<Summary | null>(null)
const prefs = reactive<Prefs>({
  bank: 'zhongkao_800',
  daily_count: 20,
  show_morph: true,
  auto_speak: false,
})
const saving = ref(false)
const tip = ref('')
const loadError = ref('')
const quiz = ref<QuizItem[]>([])
const answers = reactive<Record<number, string>>({})
const quizResult = ref<any>(null)
const submitting = ref(false)
const speaking = ref(false)
const speakTip = ref('')
const ttsGender = ref<TtsGender>(getTtsGender())

function chooseGender(g: TtsGender) {
  ttsGender.value = g
  setTtsGender(g)
  speakTip.value = g === 'female' ? '已切换女声' : '已切换男声'
}

const current = () => words.value[idx.value]
const newCount = computed(() => words.value.filter((w) => w.role === 'new').length)
const reviewCount = computed(() => words.value.filter((w) => w.role !== 'new').length)

async function load() {
  if (!auth.isLoggedIn.value) {
    router.push({ path: '/auth', query: { redirect: '/courses/love-words' } })
    return
  }
  loadError.value = ''
  try {
    ;[banks.value, summary.value] = await Promise.all([
      api<Bank[]>('/vocab/banks'),
      api<Summary>('/vocab/course/summary'),
    ])
    const p = await api<Prefs>('/vocab/prefs')
    Object.assign(prefs, {
      bank: p.bank || 'zhongkao_800',
      daily_count: Math.max(5, Math.min(100, p.daily_count || 20)),
      show_morph: p.show_morph !== false,
      auto_speak: !!p.auto_speak,
    })
    showMorph.value = prefs.show_morph
    words.value = await api('/vocab/course/today')
    idx.value = 0
    flipped.value = false
    phase.value = summary.value?.today_completed ? 'done' : 'study'
    syncStreak(summary.value)
    await auth.track('love-words', 'course', 'started', { title: '我爱背单词' }, summary.value?.percent || 5)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载失败，请稍后重试'
  }
}

async function savePrefs() {
  saving.value = true
  tip.value = ''
  try {
    const p = await api<Prefs>('/vocab/prefs', {
      method: 'PUT',
      body: JSON.stringify(prefs),
    })
    Object.assign(prefs, p)
    showMorph.value = p.show_morph
    tip.value = '设置已保存：已按考试词库、每日数量与艾宾浩斯复习刷新今日词单'
    summary.value = await api('/vocab/course/summary')
    syncStreak(summary.value)
    words.value = await api('/vocab/course/today')
    idx.value = 0
    phase.value = 'study'
    quizResult.value = null
  } catch (e) {
    tip.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function mark(status: string) {
  const w = current()
  if (!w) return
  await api(`/vocab/${w.id}/progress`, { method: 'POST', body: JSON.stringify({ status }) })
  w.status = status
  next()
}

function senseExamples(w: Word | undefined) {
  if (!w) return [] as string[]
  const fromMeanings = (w.meanings || []).map((m) => (m.example || '').trim()).filter(Boolean)
  if (fromMeanings.length) return fromMeanings
  const fallback = (w.example || '').trim()
  return fallback ? [fallback] : []
}

function syncStreak(s: Summary | null) {
  if (!s) return
  auth.applyVocabStreak(s.streak_days || 0, !!s.streak_badge)
}

async function speak() {
  const w = current()
  if (!w || speaking.value) return
  speaking.value = true
  speakTip.value = ''
  try {
    const examples = senseExamples(w)
    let result
    if (flipped.value && examples.length) {
      result = await speakEnglish(examples.join('. '), {
        gender: ttsGender.value,
        lang: 'en',
        mode: 'sentence',
      })
    } else {
      if (flipped.value && !examples.length) speakTip.value = '暂无例句，已朗读单词'
      result = await speakWord(w.word, { gender: ttsGender.value })
    }
    if (result.fallback) {
      speakTip.value = '神经朗读暂不可用，已用系统音色'
    }
  } catch (e) {
    speakTip.value = e instanceof Error ? e.message : '朗读失败'
  } finally {
    speaking.value = false
  }
}

function next() {
  flipped.value = false
  if (idx.value < words.value.length - 1) {
    idx.value += 1
    if (prefs.auto_speak) void speak()
  }
}

function prev() {
  flipped.value = false
  idx.value = idx.value > 0 ? idx.value - 1 : 0
}

function typeLabel(t: string) {
  if (t === 'prefix') return '前缀'
  if (t === 'suffix') return '后缀'
  return '词根'
}

async function startQuiz() {
  quiz.value = await api('/vocab/course/quiz')
  for (const q of quiz.value) delete answers[q.word_id]
  quizResult.value = null
  phase.value = 'quiz'
}

async function submitQuiz() {
  submitting.value = true
  try {
    const payload: Record<string, string> = {}
    for (const q of quiz.value) {
      if (answers[q.word_id]) payload[String(q.word_id)] = answers[q.word_id]
    }
    quizResult.value = await api('/vocab/course/quiz/submit', {
      method: 'POST',
      body: JSON.stringify({ answers: payload }),
    })
    summary.value = await api('/vocab/course/summary')
    syncStreak(summary.value)
    phase.value = 'done'
    if (quizResult.value?.all_correct) {
      await auth.track('love-words', 'course', 'completed', { title: '我爱背单词' }, summary.value?.percent || 10)
    }
  } finally {
    submitting.value = false
  }
}

async function redeem() {
  try {
    const r = await api<{ message: string }>('/vocab/course/redeem', { method: 'POST' })
    tip.value = r.message
    summary.value = await api('/vocab/course/summary')
    syncStreak(summary.value)
  } catch (e) {
    tip.value = e instanceof Error ? e.message : '兑换失败'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="head">
      <div>
        <p class="kicker">独立课程</p>
        <h1>我爱背单词</h1>
        <p v-if="loadError" class="lead err-line">
          {{ loadError }}
          <button type="button" class="ghost-btn" @click="load">重试</button>
        </p>
        <p class="sub">
          艾宾浩斯复习 + 卡片拆解记忆。今日
          <b>{{ newCount }}</b> 个新词 · <b>{{ reviewCount }}</b> 个复习
        </p>
      </div>
      <div class="head-actions">
        <button type="button" class="ghost-btn" @click="showSettings = !showSettings">
          {{ showSettings ? '收起设置' : '学习设置' }}
        </button>
        <RouterLink class="ghost-btn" to="/">回首页</RouterLink>
      </div>
    </header>

    <section v-if="summary" class="stats">
      <div><b>{{ summary.learned }}/{{ summary.bank_total }}</b><span>{{ summary.bank_name }}</span></div>
      <div><b>{{ summary.days_needed }}</b><span>预计总天数</span></div>
      <div><b>{{ summary.days_left }}</b><span>剩余天数</span></div>
      <div>
        <b>
          {{ summary.streak_days }}
          <i v-if="summary.streak_badge" class="mini-badge" title="连续打卡徽章">连</i>
        </b>
        <span>连续打卡</span>
      </div>
      <div><b>{{ summary.today_completed ? (summary.today_stars || summary.stars_per_day || 1) : (summary.stars_per_day || 1) }}★</b><span>{{ summary.today_completed ? '今日已得' : '今日可得' }}</span></div>
      <div><b>{{ summary.stars_total }}★</b><span>累计星星</span></div>
      <div><b>{{ summary.stars_month }}/30</b><span>本月兑会员</span></div>
    </section>

    <section v-if="showSettings" class="settings">
      <h3>词库与每日数量</h3>
      <div class="settings-grid">
        <label class="wide">
          考试分类
          <select v-model="prefs.bank">
            <option v-for="b in banks" :key="b.id" :value="b.id" :disabled="!b.available">
              {{ b.name }}{{ b.available ? '' : '（即将上线）' }}
            </option>
          </select>
        </label>
        <label>
          每日背单词数量（5–100）
          <input v-model.number="prefs.daily_count" type="number" min="5" max="100" />
        </label>
        <label class="check">
          <input v-model="prefs.show_morph" type="checkbox" />
          默认显示词根词缀
        </label>
        <label class="check">
          <input v-model="prefs.auto_speak" type="checkbox" />
          切词自动朗读
        </label>
        <label class="wide">
          朗读音色
          <div class="voice-row">
            <button
              type="button"
              class="voice-btn"
              :class="{ on: ttsGender === 'female' }"
              @click="chooseGender('female')"
            >
              女声
            </button>
            <button
              type="button"
              class="voice-btn"
              :class="{ on: ttsGender === 'male' }"
              @click="chooseGender('male')"
            >
              男声
            </button>
          </div>
        </label>
      </div>
      <p class="calc" v-if="summary">
        按每日 {{ prefs.daily_count }} 个新词、词库 {{ summary.bank_total }} 词计算，大约需要
        <b>{{ Math.ceil((summary.bank_total || 0) / (prefs.daily_count || 1)) }}</b> 天背完；
        每天还会按艾宾浩斯穿插复习，答错题下次优先出现。
      </p>
      <div class="settings-actions">
        <button type="button" class="save" :disabled="saving" @click="savePrefs">
          {{ saving ? '保存中…' : '保存并刷新今日词单' }}
        </button>
        <button
          v-if="(summary?.stars_month || 0) >= 30"
          type="button"
          class="redeem"
          @click="redeem"
        >
          用 30★ 兑换一个月会员
        </button>
        <span v-if="tip" class="tip">{{ tip }}</span>
      </div>
    </section>

    <!-- 学习卡片 -->
    <template v-if="phase === 'study'">
      <p class="count" v-if="words.length">{{ idx + 1 }} / {{ words.length }}</p>
      <p v-else class="empty">今日词单为空，请先在设置中选择词库。</p>

      <article v-if="current()" class="card" @click="flipped = !flipped">
        <div class="role" :class="current().role">
          {{ current().role === 'new' ? '新词' : current().role === 'wrong' ? '错题优先' : '复习' }}
          <span v-if="current().scene"> · {{ current().scene }}</span>
        </div>
        <div class="card-top">
          <WordMeaningArt
            :image-key="current().image_key"
            :image-url="current().image_url"
            :meaning="current().meaning"
            :word="current().word"
          />
          <div class="meta">
            <template v-if="!flipped">
              <h2 class="word">{{ current().word }}</h2>
              <p class="ph">{{ current().phonetic || '点下方朗读听单词' }}</p>
              <small>{{ current().frequency || current().level }}</small>
              <p class="hint">点击卡片查看释义与例句</p>
            </template>
            <template v-else>
              <ul class="meanings">
                <li v-for="(m, i) in current().meanings" :key="i" class="sense">
                  <p class="sense-head">
                    <em v-if="m.pos">{{ m.pos }}</em>
                    {{ m.text }}
                  </p>
                  <p v-if="m.example" class="example">{{ m.example }}</p>
                  <p v-if="m.example_cn" class="example-cn">{{ m.example_cn }}</p>
                  <p v-if="m.source" class="exam-src">{{ m.source }}</p>
                </li>
              </ul>
              <p v-if="!current().meanings?.length" class="example">{{ current().example }}</p>
              <div v-if="current().is_verb && current().verb_forms" class="verb-forms" @click.stop>
                <div class="vf-title">动词变形</div>
                <div class="vf-row">
                  <span><i>进行时</i>{{ current().verb_forms.ing }}</span>
                  <span><i>过去式</i>{{ current().verb_forms.past }}</span>
                  <span><i>过去分词</i>{{ current().verb_forms.past_participle }}</span>
                </div>
              </div>
              <p class="ph">{{ senseExamples(current()).length ? '点下方朗读听例句' : current().word }}</p>
            </template>
          </div>
        </div>

        <!-- 正面也显示动词变形，方便不翻牌也能看 -->
        <div
          v-if="!flipped && current().is_verb && current().verb_forms"
          class="verb-forms front"
          @click.stop
        >
          <div class="vf-title">动词变形</div>
          <div class="vf-row">
            <span><i>进行时</i>{{ current().verb_forms.ing }}</span>
            <span><i>过去式</i>{{ current().verb_forms.past }}</span>
            <span><i>过去分词</i>{{ current().verb_forms.past_participle }}</span>
          </div>
        </div>

        <section
          v-if="showMorph && (current().segments?.length || current().morph_story)"
          class="morph"
          @click.stop
        >
          <div class="morph-head">
            <span class="badge">{{ current().segments?.length >= 2 ? '词根词缀拆解' : '图画联想记忆' }}</span>
            <span v-if="current().is_long" class="tip">长单词拆解</span>
          </div>
          <div v-if="current().segments?.length" class="segments">
            <div
              v-for="(s, i) in current().segments"
              :key="s.text + i"
              class="seg"
              :style="{ '--c': s.color }"
            >
              <MorphIcon :name="s.icon" :color="s.color" />
              <div>
                <strong>{{ s.text }}</strong>
                <em>{{ typeLabel(s.type) }} · {{ s.gloss }}</em>
              </div>
              <span v-if="i < current().segments.length - 1" class="plus">+</span>
            </div>
          </div>
          <p v-if="current().morph_story" class="story">→ {{ current().morph_story }}</p>
        </section>
      </article>

      <div class="actions" v-if="current()">
        <button type="button" @click="prev">上一个</button>
        <button type="button" :disabled="speaking" @click="void speak()">
          {{ speaking ? '朗读中…' : flipped ? '朗读例句' : '朗读单词' }}
        </button>
        <button
          type="button"
          class="voice-mini"
          :title="ttsGender === 'female' ? '当前女声，点击切男声' : '当前男声，点击切女声'"
          @click="chooseGender(ttsGender === 'female' ? 'male' : 'female')"
        >
          {{ ttsGender === 'female' ? '女声' : '男声' }}
        </button>
        <button type="button" class="ok" @click="mark('known')">认识</button>
        <button type="button" class="hard" @click="mark('hard')">较难</button>
        <button type="button" @click="next">下一个</button>
      </div>
      <p v-if="speakTip" class="speak-tip">{{ speakTip }}</p>
      <div class="footer-actions" v-if="words.length">
        <button type="button" class="primary" @click="startQuiz">背完了，开始测验</button>
      </div>
    </template>

    <!-- 测验 -->
    <template v-else-if="phase === 'quiz'">
      <h2 class="phase-title">今日测验</h2>
      <p class="sub">全部答对才能打卡得星；答错会进入下次优先复习。</p>
      <ul class="quiz">
        <li v-for="q in quiz" :key="q.word_id">
          <h3>{{ q.prompt }}</h3>
          <label v-for="opt in q.options" :key="opt" class="opt">
            <input v-model="answers[q.word_id]" type="radio" :value="opt" />
            {{ opt }}
          </label>
        </li>
      </ul>
      <button type="button" class="primary" :disabled="submitting" @click="submitQuiz">
        {{ submitting ? '提交中…' : '提交测验' }}
      </button>
    </template>

    <!-- 结果 -->
    <template v-else>
      <div class="done" v-if="quizResult || summary?.today_completed">
        <h2>{{ quizResult?.all_correct || summary?.today_completed ? '今日打卡成功' : '继续加油' }}</h2>
        <p v-if="quizResult">{{ quizResult.message }}</p>
        <p v-else>今天已经完成背单词打卡。</p>
        <p v-if="summary?.streak_badge || quizResult?.streak_badge" class="badge-lit">
          连续打卡徽章已点亮，展示在头像旁
        </p>
        <p v-else-if="summary" class="badge-hint">
          再连续打卡 {{ Math.max(10 - (summary.streak_days || 0), 0) }} 天可点亮徽章；从第 11 天起每天 2 颗星
        </p>
        <div class="done-stats" v-if="summary">
          <span>连续 {{ summary.streak_days }} 天</span>
          <span>今日 {{ quizResult?.stars_earned || summary.today_stars || 0 }}★</span>
          <span>本月 {{ summary.stars_month }}★</span>
          <span>累计 {{ summary.stars_total }}★</span>
        </div>
        <div class="footer-actions">
          <button type="button" class="ghost-btn" @click="phase = 'study'">再看一遍卡片</button>
          <button type="button" class="primary" @click="startQuiz">重新测验</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  width: min(860px, 100%);
  margin: 0 auto;
  padding: 28px 20px 72px;
}
.kicker {
  margin: 0;
  color: var(--brand);
  font-size: 0.85rem;
  letter-spacing: 0.06em;
}
h1 {
  font-family: 'Noto Serif SC', serif;
  margin: 4px 0 8px;
}
.sub {
  color: var(--muted);
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.head-actions {
  display: flex;
  gap: 8px;
}
.ghost-btn {
  border: 1px solid rgba(15, 107, 92, 0.25);
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  color: var(--brand-deep);
  text-decoration: none;
  cursor: pointer;
}
.err-line {
  color: #a35 !important;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin: 18px 0;
}
.stats div {
  background: #fff;
  border: 1px solid rgba(15, 107, 92, 0.12);
  border-radius: 12px;
  padding: 12px;
}
.stats b {
  display: block;
  font-size: 1.2rem;
  color: var(--brand-deep);
}
.stats span {
  color: var(--muted);
  font-size: 0.8rem;
}
.settings {
  background: rgba(15, 107, 92, 0.05);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 16px;
}
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.settings-grid label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
}
.settings-grid .wide {
  grid-column: 1 / -1;
}
.settings-grid input,
.settings-grid select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(15, 107, 92, 0.2);
}
.check {
  display: flex !important;
  align-items: center;
  gap: 8px;
  grid-template-columns: none !important;
}
.calc {
  color: var(--muted);
  font-size: 0.9rem;
}
.settings-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
}
.save,
.primary,
.redeem {
  background: var(--brand);
  color: #fff;
  border: 0;
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
}
.redeem {
  background: #c98500;
}
.tip {
  color: var(--brand-deep);
}
.count {
  color: var(--brand-deep);
  font-weight: 600;
}
.card {
  background: #fff;
  border-radius: 18px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  padding: 16px;
  cursor: pointer;
}
.role {
  font-size: 0.8rem;
  color: var(--brand);
  margin-bottom: 8px;
}
.role.wrong {
  color: #b45309;
}
.role.review {
  color: #0b5a4e;
}
.card-top {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}
.card-top :deep(.art) {
  width: 160px;
  max-width: 100%;
  height: 120px;
}
.meta {
  min-width: 0;
}
.word {
  font-size: 2rem;
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  word-break: break-word;
}
.ph {
  color: var(--muted);
}
.meanings {
  list-style: none;
  padding: 0;
  margin: 0 0 10px;
  display: grid;
  gap: 10px;
}
.sense-head {
  margin: 0 0 6px;
  font-weight: 600;
  color: var(--brand-deep);
}
.meanings em {
  color: var(--brand);
  margin-right: 6px;
  font-style: normal;
  font-size: 0.85rem;
}
.example {
  background: rgba(232, 163, 23, 0.12);
  padding: 8px 12px;
  border-radius: 10px;
  margin: 0;
  line-height: 1.5;
}
.example-cn {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.exam-src {
  margin: 4px 0 0;
  color: #b45309;
  font-size: 0.75rem;
  font-weight: 600;
}
.mini-badge {
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  margin-left: 4px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8a317, #d97706);
  color: #fff;
  font-size: 0.62rem;
  font-style: normal;
  font-weight: 800;
  vertical-align: middle;
}
.badge-lit {
  color: #b45309;
  font-weight: 700;
}
.badge-hint {
  color: var(--muted);
  font-size: 0.9rem;
}
.verb-forms {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 107, 92, 0.07);
  border: 1px solid rgba(15, 107, 92, 0.14);
}
.verb-forms.front {
  margin-top: 12px;
}
.vf-title {
  font-size: 0.78rem;
  color: var(--brand-deep);
  font-weight: 700;
  margin-bottom: 6px;
  letter-spacing: 0.04em;
}
.vf-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.vf-row span {
  display: grid;
  gap: 2px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #143;
  word-break: break-word;
}
.vf-row i {
  font-style: normal;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--muted);
}
@media (max-width: 640px) {
  .vf-row {
    grid-template-columns: 1fr;
  }
}
.hint {
  color: var(--muted);
  font-size: 0.85rem;
}
.morph {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(15, 107, 92, 0.2);
}
.morph-head {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}
.badge {
  background: rgba(15, 107, 92, 0.12);
  color: var(--brand-deep);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.75rem;
}
.segments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.seg {
  display: flex;
  gap: 8px;
  align-items: center;
  background: color-mix(in srgb, var(--c) 12%, white);
  border-radius: 12px;
  padding: 8px 10px;
}
.seg strong {
  display: block;
}
.seg em {
  font-style: normal;
  color: var(--muted);
  font-size: 0.8rem;
}
.plus {
  color: var(--muted);
}
.story {
  color: var(--brand-deep);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.actions button {
  border: 1px solid rgba(15, 107, 92, 0.2);
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
}
.actions button:disabled {
  opacity: 0.6;
  cursor: wait;
}
.speak-tip {
  margin: 8px 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}
.voice-row {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.voice-btn {
  border: 1px solid rgba(15, 107, 92, 0.22);
  background: #fff;
  border-radius: 999px;
  padding: 6px 14px;
  cursor: pointer;
  color: var(--muted);
}
.voice-btn.on {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.voice-mini {
  font-size: 0.85rem;
  color: var(--brand-deep) !important;
}
.actions .ok {
  background: rgba(15, 107, 92, 0.12);
}
.actions .hard {
  background: rgba(232, 163, 23, 0.2);
}
.footer-actions {
  margin-top: 18px;
  display: flex;
  gap: 10px;
}
.quiz {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 12px;
}
.quiz li {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
}
.opt {
  display: flex;
  gap: 8px;
  margin: 6px 0;
  cursor: pointer;
}
.done {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  text-align: center;
}
.done-stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin: 14px 0;
  color: var(--brand-deep);
  font-weight: 600;
}
.phase-title {
  font-family: 'Noto Serif SC', serif;
}
@media (max-width: 640px) {
  .card-top {
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
  }
  .meta {
    width: 100%;
  }
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
