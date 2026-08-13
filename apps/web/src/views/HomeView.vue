<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import CourseCard from '../components/CourseCard.vue'
import { hotCourses } from '../data/courses'
import { sceneMeta, type SceneType } from '../data/classroom'
import {
  addStudyPlan,
  doCheckin,
  fetchAnnouncements,
  fetchCheckin,
  fetchStudyPlans,
  toggleStudyPlan,
  api,
  type Announcement,
  type CheckinInfo,
  type StudyPlan,
} from '../lib/api'
import { courseLabel, courseRoute } from '../lib/courseLabels'
import { orchestrateClassroom } from '../lib/classroomOrchestrator'
import { useAuth } from '../stores/auth'

const auth = useAuth()
const router = useRouter()
const topic = ref('30 分钟搞懂勾股定理')
const busy = ref(false)
const announcements = ref<Announcement[]>([])
const checkin = ref<CheckinInfo | null>(null)
const plans = ref<StudyPlan[]>([])
const newPlan = ref('')
const toast = ref('')
const vocabSummary = ref<{
  need_reminder: boolean
  today_completed: boolean
  streak_days: number
  streak_badge?: boolean
  stars_month: number
  stars_total: number
  bank_name: string
  daily_count: number
} | null>(null)
const mathSummary = ref<{
  need_reminder: boolean
  need_practice?: boolean
  need_fix?: boolean
  today_submitted: boolean
  streak_days: number
  grade: number
  topic: string
  daily_count: number
  today_correct: number
  today_total: number
  wrong_open?: number
} | null>(null)

const showVocabRemind = computed(() => !!vocabSummary.value?.need_reminder)
const showMathRemind = computed(() => !!mathSummary.value?.need_reminder)
const showVocabDone = computed(
  () => !!vocabSummary.value?.today_completed && !vocabSummary.value?.need_reminder,
)
const showMathDone = computed(
  () =>
    !!mathSummary.value?.today_submitted &&
    !(mathSummary.value.wrong_open && mathSummary.value.wrong_open > 0),
)

const pillars: { type: SceneType; desc: string }[] = [
  { type: 'slide', desc: 'AI 教师语音讲解，要点逐层展开' },
  { type: 'quiz', desc: '即时反馈，定位知识盲点' },
  { type: 'sim', desc: '交互实验与动图，动手内化' },
  { type: 'pbl', desc: '角色协作，交付可展示作品' },
]

const capabilities = [
  {
    title: '多智能体课堂',
    text: '教师、同伴与导师协同出现：授课、追问、陪伴项目交付。',
  },
  {
    title: '主题一键成课',
    text: '输入一句话或学习目标，自动编排完整课堂大纲与场景。',
  },
  {
    title: '几何与口语能力',
    text: '立体/解析动图、英语陪练语音对话，嵌进真实学习路径。',
  },
  {
    title: '进度可同步',
    text: '登录后学习进度写入账号，跨设备续学、可追踪完成度。',
  },
]

const hotlinks = [
  {
    title: '常用入口',
    items: [
      { to: '/catalog', label: '课程中心' },
      { to: '/practice', label: '试卷练习' },
      { to: '/recommend', label: '薄弱推荐' },
      { to: '/wrongbook', label: '错题本' },
      { to: '/learning', label: '学情报告' },
      { to: '/courses/love-words', label: '我爱背单词' },
      { to: '/courses/math-calc', label: '小学数学计算' },
      { to: '/courses/english-coach', label: '英语陪练' },
      { to: '/ebooks', label: '电子书' },
      { to: '/courses/geometry-lab', label: '几何实验室' },
    ],
  },
  {
    title: '沟通与服务',
    items: [
      { to: '/messages', label: '消息中心' },
      { to: '/reading', label: '每日美文' },
      { to: '/announcements', label: '全部公告' },
      { to: '/feedback', label: '反馈工单' },
      { to: '/me', label: '个人中心' },
    ],
  },
]

const continueCourses = computed(() => {
  const list = [...(auth.state.courses || [])]
  list.sort((a, b) => (b.percent || 0) - (a.percent || 0))
  return list.filter((c) => (c.started || 0) > 0 || (c.percent || 0) > 0).slice(0, 4)
})

async function startFromTopic() {
  if (!topic.value.trim() || busy.value) return
  busy.value = true
  try {
    const lesson = await orchestrateClassroom(topic.value)
    sessionStorage.setItem(`classroom:${lesson.id}`, JSON.stringify(lesson))
    await auth.track('classroom', lesson.id, 'started', { title: lesson.title })
    await router.push(`/classroom/${lesson.id}`)
  } finally {
    busy.value = false
  }
}

async function check() {
  checkin.value = await doCheckin()
  toast.value = '今日打卡成功'
  setTimeout(() => {
    toast.value = ''
  }, 2000)
}

async function add() {
  if (!newPlan.value.trim()) return
  await addStudyPlan(newPlan.value.trim())
  newPlan.value = ''
  plans.value = await fetchStudyPlans()
}

async function togglePlan(id: number) {
  await toggleStudyPlan(id)
  plans.value = await fetchStudyPlans()
}

onMounted(async () => {
  if (!auth.isLoggedIn.value) return
  try {
    ;[announcements.value, checkin.value, plans.value, vocabSummary.value, mathSummary.value] =
      await Promise.all([
        fetchAnnouncements(),
        fetchCheckin(),
        fetchStudyPlans(),
        api('/vocab/course/summary'),
        api('/math-calc/summary'),
      ])
    if (vocabSummary.value) {
      auth.applyVocabStreak(vocabSummary.value.streak_days || 0, !!vocabSummary.value.streak_badge)
    }
  } catch {
    announcements.value = announcements.value || []
  }
})
</script>

<template>
  <!-- 登录后：eStudent 风格三栏门户首页 -->
  <div v-if="auth.isLoggedIn.value" class="portal-home">
    <div class="portal-grid">
      <div class="center-col">
        <p v-if="toast" class="home-toast">{{ toast }}</p>

        <!-- 背单词打卡提醒：未完成优先；已完成折叠为紧凑条 -->
        <section
          v-if="showVocabRemind && vocabSummary"
          class="panel vocab-remind fade-up"
        >
          <header class="panel-head">我爱背单词</header>
          <div class="panel-body vocab-remind-body">
            <div>
              <h3>今日还没背单词</h3>
              <p>
                {{ vocabSummary.bank_name }} · 每日 {{ vocabSummary.daily_count }} 词 ·
                连续 {{ vocabSummary.streak_days }} 天 · 本月 {{ vocabSummary.stars_month }}★
              </p>
            </div>
            <RouterLink class="btn btn-primary" to="/courses/love-words">去背单词打卡</RouterLink>
          </div>
        </section>
        <section v-else-if="showVocabDone && vocabSummary" class="panel remind-done fade-up">
          <div class="remind-done-row">
            <span>
              我爱背单词 · 今日已打卡 ✓ · 连续 {{ vocabSummary.streak_days }} 天
              <i v-if="vocabSummary.streak_badge" class="home-streak">连</i>
            </span>
            <RouterLink to="/courses/love-words">复习</RouterLink>
          </div>
        </section>

        <!-- 小学数学：未做 / 待订正优先；完成折叠 -->
        <section
          v-if="showMathRemind && mathSummary"
          class="panel vocab-remind fade-up"
          :class="{ fix: mathSummary.need_fix && mathSummary.today_submitted }"
        >
          <header class="panel-head">小学数学计算专项</header>
          <div class="panel-body vocab-remind-body">
            <div>
              <h3 v-if="!mathSummary.today_submitted">今日计算练习还没做</h3>
              <h3 v-else>
                有 {{ mathSummary.wrong_open || 0 }} 题待订正
              </h3>
              <p>
                {{ mathSummary.grade }}年级 · {{ mathSummary.topic }} · 每日
                {{ mathSummary.daily_count }} 题 · 连续 {{ mathSummary.streak_days }} 天
                <template v-if="mathSummary.today_submitted">
                  · 今日 {{ mathSummary.today_correct }}/{{ mathSummary.today_total }}
                </template>
              </p>
            </div>
            <RouterLink class="btn btn-primary" to="/courses/math-calc">
              {{ mathSummary.today_submitted ? '去订正错题' : '去做今日练习' }}
            </RouterLink>
          </div>
        </section>
        <section v-else-if="showMathDone && mathSummary" class="panel remind-done fade-up">
          <div class="remind-done-row">
            <span
              >小学数学 · 今日已完成 {{ mathSummary.today_correct }}/{{ mathSummary.today_total }} · 连续
              {{ mathSummary.streak_days }} 天</span
            >
            <RouterLink to="/courses/math-calc">查看</RouterLink>
          </div>
        </section>

        <!-- 今日学习闭环：打卡 + 计划 + 续学 -->
        <section class="panel today-panel fade-up">
          <header class="panel-head">今日学习</header>
          <div class="panel-body today-body">
            <div class="today-check">
              <div class="nums" v-if="checkin">
                <div><strong>{{ checkin.streak }}</strong><span>连续</span></div>
                <div><strong>{{ checkin.total }}</strong><span>累计</span></div>
              </div>
              <button
                type="button"
                class="btn btn-primary check-btn"
                :disabled="checkin?.checked_today"
                @click="check"
              >
                {{ checkin?.checked_today ? '今日已打卡' : '立即打卡' }}
              </button>
            </div>

            <div class="today-plans">
              <h3>今日计划</h3>
              <form class="plan-add" @submit.prevent="add">
                <input v-model="newPlan" placeholder="添加一条计划…" />
                <button type="submit">添加</button>
              </form>
              <ul v-if="plans.length">
                <li v-for="p in plans.slice(0, 5)" :key="p.id" :class="{ done: p.done }">
                  <button type="button" class="chk" @click="togglePlan(p.id)">
                    {{ p.done ? '✓' : '○' }}
                  </button>
                  <span>{{ p.title }}</span>
                </li>
              </ul>
              <p v-else class="empty-mini">还没有计划，先写一条吧</p>
              <RouterLink class="more" to="/me">管理全部计划 →</RouterLink>
            </div>

            <div class="today-continue">
              <h3>继续学习</h3>
              <ul v-if="continueCourses.length">
                <li v-for="c in continueCourses" :key="c.course_id">
                  <RouterLink :to="courseRoute(c.course_id)">
                    <strong>{{ courseLabel(c.course_id) }}</strong>
                    <em>{{ c.percent }}%</em>
                  </RouterLink>
                  <div class="mini-bar"><i :style="{ width: c.percent + '%' }" /></div>
                </li>
              </ul>
              <p v-else class="empty-mini">
                还没有进度，
                <RouterLink to="/catalog">去课程中心</RouterLink>
                或
                <RouterLink to="/courses/love-words">背一组单词</RouterLink>
              </p>
            </div>
          </div>
        </section>

        <!-- 公告 -->
        <section class="panel notice-panel fade-up" style="animation-delay: 40ms">
          <header class="panel-head">公告</header>
          <div class="panel-body">
            <ul v-if="announcements.length" class="notice-list">
              <li v-for="a in announcements.slice(0, 5)" :key="a.id">
                <RouterLink :to="`/announcements/${a.id}`" class="notice-title">
                  {{ a.title }}
                </RouterLink>
                <time v-if="a.created_at">{{ a.created_at.slice(0, 10) }}</time>
                <p class="notice-snip">{{ a.body.slice(0, 72) }}{{ a.body.length > 72 ? '…' : '' }}</p>
              </li>
            </ul>
            <p v-else class="empty">暂无公告</p>
            <RouterLink class="more" to="/announcements">查看全部公告 →</RouterLink>
          </div>
        </section>

        <!-- AI 多智能体课堂介绍 -->
        <section class="panel intro-panel fade-up" style="animation-delay: 60ms">
          <header class="panel-head">AI 多智能体课堂</header>
          <div class="panel-body intro-body">
            <div class="intro-copy">
              <p class="welcome">{{ auth.state.user?.display_name }}，欢迎回来</p>
              <h2>把任何主题变成一场沉浸式课堂</h2>
              <p class="lead">
                教师、同伴与导师多智能体协同：讲解、追问、测验与项目交付一气呵成。
              </p>
              <form class="compose" @submit.prevent="startFromTopic">
                <input
                  v-model="topic"
                  type="text"
                  aria-label="课堂主题"
                  placeholder="描述一个主题，例如：光合作用入门"
                />
                <button class="btn btn-primary" type="submit" :disabled="busy || !topic.trim()">
                  {{ busy ? '编排中…' : '生成课堂' }}
                </button>
              </form>
              <RouterLink class="text-link" to="/classroom">浏览精选课堂 →</RouterLink>
            </div>
            <div class="intro-stage" aria-hidden="true">
              <div class="stage-window">
                <div class="stage-top">
                  <span /><span /><span />
                  <em>Classroom Live</em>
                </div>
                <div class="stage-body">
                  <div class="agent teacher">
                    <b>林老师</b>
                    <p>先看定义，再动手验证线面角。</p>
                  </div>
                  <div class="board">
                    <div class="slide-line" />
                    <div class="slide-line short" />
                    <div class="formula">sin θ = |d · n| / (|d| |n|)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 完整 AI 课堂体验 -->
        <section class="panel fade-up" style="animation-delay: 100ms">
          <header class="panel-head">完整 AI 课堂体验</header>
          <div class="panel-body">
            <p class="sec-desc">听懂 · 检验 · 动手 · 创造 — AI 统筹编排学习闭环。</p>
            <div class="pillar-grid">
              <article v-for="(p, i) in pillars" :key="p.type" class="pillar">
                <span class="idx">0{{ i + 1 }}</span>
                <h3>{{ sceneMeta[p.type].label }}</h3>
                <p>{{ p.desc }}</p>
              </article>
            </div>
          </div>
        </section>

        <!-- 平台能力 -->
        <section class="panel fade-up" style="animation-delay: 140ms">
          <header class="panel-head">平台能力介绍</header>
          <div class="panel-body">
            <div class="cap-grid">
              <article v-for="c in capabilities" :key="c.title" class="cap">
                <h3>{{ c.title }}</h3>
                <p>{{ c.text }}</p>
              </article>
            </div>
          </div>
        </section>

        <!-- 精选学习入口 -->
        <section class="panel fade-up" style="animation-delay: 180ms">
          <header class="panel-head">精选学习入口</header>
          <div class="panel-body">
            <p class="sec-desc">进度已写入账号，可直接续学。</p>
            <div class="course-grid">
              <CourseCard
                v-for="(course, i) in hotCourses"
                :key="course.id"
                :course="course"
                :delay="60 + i * 50"
                :logged-in="true"
                :percent="auth.coursePercent(course.id)"
              />
            </div>
          </div>
        </section>
      </div>

      <!-- 右侧 Hotlinks -->
      <aside class="hotlinks fade-up" style="animation-delay: 80ms">
        <header class="panel-head">Hotlinks</header>
        <div class="hot-body">
          <div v-for="group in hotlinks" :key="group.title" class="hot-group">
            <h3>{{ group.title }}</h3>
            <ul>
              <li v-for="item in group.items" :key="item.to">
                <RouterLink :to="item.to">{{ item.label }}</RouterLink>
              </li>
            </ul>
          </div>
        </div>
      </aside>
    </div>
  </div>

  <!-- 未登录：保留营销落地页 -->
  <div v-else class="landing">
    <section class="hero">
      <div class="hero-bg" aria-hidden="true" />
      <div class="hero-inner">
        <div class="hero-copy fade-up">
          <p class="kicker"><span class="pulse" /> AI 多智能体互动课堂</p>
          <h1 class="brand">eduAI</h1>
          <p class="promise">把任何主题或文档变成一场沉浸式课堂</p>
          <form class="compose" @submit.prevent="startFromTopic">
            <input
              v-model="topic"
              type="text"
              aria-label="课堂主题"
              placeholder="描述一个主题，例如：光合作用入门"
            />
            <button class="btn btn-primary" type="submit" :disabled="busy || !topic.trim()">
              {{ busy ? '编排中…' : '生成课堂' }}
            </button>
          </form>
          <div class="actions">
            <RouterLink class="btn btn-ghost" to="/classroom">浏览精选课堂</RouterLink>
            <RouterLink class="text-link" to="/auth">登录同步进度</RouterLink>
          </div>
        </div>

        <div class="hero-stage fade-up" style="animation-delay: 120ms" aria-hidden="true">
          <div class="stage-window tall">
            <div class="stage-top">
              <span /><span /><span />
              <em>Classroom Live</em>
            </div>
            <div class="stage-body">
              <div class="agent teacher">
                <b>林老师</b>
                <p>先看定义，再动手验证线面角。</p>
              </div>
              <div class="board">
                <div class="slide-line" />
                <div class="slide-line short" />
                <div class="formula">sin θ = |d · n| / (|d| |n|)</div>
              </div>
              <div class="agent peer">
                <b>安安</b>
                <p>那射影到底在哪个平面上？</p>
              </div>
            </div>
            <div class="scene-tabs">
              <span class="on">幻灯</span><span>测验</span><span>模拟</span><span>PBL</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="band scenes">
      <div class="wrap">
        <header class="sec-head fade-up">
          <p class="eyebrow">完整 AI 课堂体验</p>
          <h2>听懂 · 检验 · 动手 · 创造</h2>
          <p>AI 统筹编排学习闭环，而不是堆砌功能模块。</p>
        </header>
        <div class="pillar-grid">
          <article
            v-for="(p, i) in pillars"
            :key="p.type"
            class="pillar fade-up"
            :style="{ animationDelay: `${100 + i * 70}ms` }"
          >
            <span class="idx">0{{ i + 1 }}</span>
            <h3>{{ sceneMeta[p.type].label }}</h3>
            <p>{{ p.desc }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="band caps">
      <div class="wrap">
        <header class="sec-head fade-up">
          <p class="eyebrow">平台能力</p>
          <h2>为真实教学而设计</h2>
          <p>从成课到续学，覆盖学校、教培与自学场景。</p>
        </header>
        <div class="cap-grid">
          <article
            v-for="(c, i) in capabilities"
            :key="c.title"
            class="cap fade-up"
            :style="{ animationDelay: `${80 + i * 60}ms` }"
          >
            <h3>{{ c.title }}</h3>
            <p>{{ c.text }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="band courses-band">
      <div class="wrap">
        <header class="sec-head fade-up">
          <p class="eyebrow">开始学习</p>
          <h2>精选学习入口</h2>
          <p>先体验，登录后可同步进度。</p>
        </header>
        <div class="course-grid">
          <CourseCard
            v-for="(course, i) in hotCourses"
            :key="course.id"
            :course="course"
            :delay="100 + i * 80"
            :logged-in="false"
            :percent="0"
          />
        </div>
      </div>
    </section>

    <section class="cta-band">
      <div class="wrap cta-inner fade-up">
        <h2>下一堂课，从一句话开始</h2>
        <p>描述主题，让 AI 多智能体为你搭好课堂骨架。</p>
        <RouterLink class="btn btn-accent" to="/classroom">进入课堂大厅</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* —— 登录后门户首页 —— */
.portal-home {
  padding: 16px;
  min-height: calc(100vh - var(--nav-h));
}

.portal-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 14px;
  align-items: start;
  max-width: 1280px;
  margin: 0 auto;
}

.center-col {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.home-toast {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(15, 107, 92, 0.12);
  color: var(--brand-deep);
  font-weight: 600;
}
.vocab-remind .vocab-remind-body {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.vocab-remind h3 {
  margin: 0 0 6px;
  font-size: 1.1rem;
}
.vocab-remind p {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}
.vocab-remind.done h3 {
  color: var(--brand-deep);
}
.vocab-remind.fix {
  border-color: rgba(196, 92, 38, 0.25);
}
.remind-done {
  padding: 0;
  margin-bottom: 10px;
}
.remind-done-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  font-size: 0.9rem;
  color: var(--muted);
}
.remind-done-row a {
  color: var(--brand);
  font-weight: 600;
  white-space: nowrap;
}
.home-streak {
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  margin-left: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e8a317, #d97706);
  color: #fff;
  font-size: 0.62rem;
  font-style: normal;
  font-weight: 800;
  vertical-align: middle;
}

.today-body {
  display: grid;
  grid-template-columns: 160px 1fr 1fr;
  gap: 16px;
  align-items: start;
}

.today-check .nums {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}

.today-check .nums div {
  background: rgba(15, 107, 92, 0.06);
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
}

.today-check strong {
  display: block;
  font-size: 1.35rem;
  color: var(--brand);
}

.today-check span {
  font-size: 0.75rem;
  color: var(--muted);
}

.check-btn {
  width: 100%;
}

.today-plans h3,
.today-continue h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-family: var(--font-display);
}

.plan-add {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.plan-add input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 10px;
  font: inherit;
}

.plan-add button {
  border: 0;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  padding: 7px 10px;
  cursor: pointer;
  font-weight: 600;
}

.today-plans ul,
.today-continue ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.today-plans li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(15, 107, 92, 0.06);
  font-size: 0.9rem;
}

.today-plans li.done span {
  text-decoration: line-through;
  color: var(--muted);
}

.chk {
  border: 0;
  background: transparent;
  color: var(--brand);
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
}

.empty-mini {
  margin: 6px 0;
  color: var(--muted);
  font-size: 0.88rem;
}

.today-continue li {
  margin-bottom: 10px;
}

.today-continue a {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: inherit;
  font-size: 0.9rem;
}

.today-continue em {
  color: var(--brand);
  font-style: normal;
  font-weight: 700;
}

.mini-bar {
  height: 6px;
  border-radius: 999px;
  background: rgba(15, 107, 92, 0.1);
  overflow: hidden;
  margin-top: 4px;
}

.mini-bar i {
  display: block;
  height: 100%;
  background: var(--brand);
}

@media (max-width: 900px) {
  .today-body {
    grid-template-columns: 1fr;
  }
}

.panel,
.hotlinks {
  background: #fff;
  border: 1px solid rgba(20, 33, 43, 0.08);
  overflow: hidden;
}

.panel-head {
  margin: 0;
  padding: 10px 16px;
  background: var(--brand);
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

.panel-body,
.hot-body {
  padding: 14px 16px 16px;
}

.notice-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.notice-list li {
  padding: 12px 0;
  border-bottom: 1px solid rgba(20, 33, 43, 0.08);
}

.notice-list li:last-of-type {
  border-bottom: none;
}

.notice-title {
  display: block;
  color: var(--brand-deep);
  font-weight: 700;
  font-size: 0.98rem;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.notice-list time {
  display: block;
  margin-top: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
}

.notice-snip {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.45;
}

.empty {
  color: var(--muted);
  margin: 8px 0;
}

.more,
.text-link {
  display: inline-block;
  margin-top: 10px;
  color: var(--brand);
  font-weight: 600;
  font-size: 0.9rem;
}

.intro-body {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 18px;
  align-items: center;
}

.welcome {
  margin: 0 0 6px;
  color: var(--brand);
  font-weight: 600;
  font-size: 0.9rem;
}

.intro-copy h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.35rem, 2.2vw, 1.75rem);
  color: var(--brand-deep);
  line-height: 1.25;
}

.lead,
.sec-desc {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.55;
  font-size: 0.92rem;
}

.compose {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.compose input {
  border: 1px solid rgba(15, 107, 92, 0.22);
  border-radius: 999px;
  padding: 11px 16px;
  background: #f7faf8;
  font: inherit;
}

.compose input:focus {
  outline: 2px solid var(--brand-soft);
  border-color: rgba(15, 107, 92, 0.45);
}

.stage-window {
  border-radius: 14px;
  border: 1px solid rgba(20, 33, 43, 0.08);
  background: #f7faf8;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 220px;
}

.stage-window.tall {
  min-height: 420px;
  grid-template-rows: auto 1fr auto;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 24px 60px rgba(20, 33, 43, 0.1);
  backdrop-filter: blur(8px);
  animation: floatSoft 6s ease-in-out infinite;
}

.stage-top {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  background: rgba(243, 246, 244, 0.9);
}

.stage-top span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d7dee3;
}

.stage-top span:first-child {
  background: #e8a317;
}

.stage-top em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.75rem;
  color: var(--muted);
  font-weight: 600;
}

.stage-body {
  padding: 14px;
  display: grid;
  gap: 10px;
  background: linear-gradient(160deg, rgba(15, 107, 92, 0.08), rgba(232, 163, 23, 0.06));
}

.agent {
  max-width: 90%;
  padding: 8px 10px;
  border-radius: 12px;
  background: white;
  border: 1px solid var(--line);
}

.agent.peer {
  margin-left: auto;
}

.agent b {
  display: block;
  font-size: 0.75rem;
  color: var(--brand);
  margin-bottom: 2px;
}

.agent p {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.4;
}

.board {
  margin: 2px 6%;
  padding: 14px 12px;
  border-radius: 12px;
  background: linear-gradient(145deg, #0f6b5c, #1a8f7a 55%, #0a4f44);
  color: white;
  min-height: 88px;
}

.slide-line {
  height: 7px;
  width: 72%;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.35);
  margin-bottom: 8px;
}

.slide-line.short {
  width: 48%;
}

.formula {
  margin-top: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
}

.pillar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 12px;
}

.pillar {
  padding: 14px 12px;
  border: 1px solid rgba(20, 33, 43, 0.07);
  background: #f8faf9;
}

.idx {
  display: block;
  color: var(--accent);
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 8px;
}

.pillar h3,
.cap h3 {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 1.05rem;
}

.pillar p,
.cap p {
  margin: 0;
  color: var(--muted);
  line-height: 1.45;
  font-size: 0.86rem;
}

.cap-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 4px;
}

.cap {
  padding: 14px;
  border: 1px solid rgba(15, 107, 92, 0.12);
  background: linear-gradient(160deg, rgba(15, 107, 92, 0.05), #fff);
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.hotlinks {
  position: sticky;
  top: calc(var(--nav-h) + 16px);
}

.hot-group {
  margin-bottom: 16px;
}

.hot-group:last-child {
  margin-bottom: 0;
}

.hot-group h3 {
  margin: 0 0 8px;
  color: var(--brand-deep);
  font-size: 0.92rem;
  font-weight: 700;
}

.hot-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.hot-group li {
  margin: 0;
  padding: 5px 0 5px 14px;
  position: relative;
  font-size: 0.9rem;
}

.hot-group li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.7em;
  width: 6px;
  height: 6px;
  background: var(--ink);
}

.hot-group a:hover {
  color: var(--brand);
  text-decoration: underline;
}

/* —— 未登录落地页 —— */
.landing {
  color: var(--ink);
}

.wrap {
  width: min(1120px, calc(100% - 48px));
  margin: 0 auto;
}

.hero {
  position: relative;
  min-height: calc(100vh - var(--nav-h));
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 48px 0 64px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(900px 520px at 12% 20%, rgba(15, 107, 92, 0.18), transparent 60%),
    radial-gradient(700px 420px at 88% 10%, rgba(232, 163, 23, 0.16), transparent 55%),
    linear-gradient(165deg, #f3f6f4 0%, #e7eef5 48%, #eef6f3 100%);
}

.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(15, 107, 92, 0.09) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(to bottom, black 30%, transparent 92%);
  opacity: 0.7;
}

.hero-inner {
  position: relative;
  z-index: 1;
  width: min(1120px, calc(100% - 48px));
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 48px;
  align-items: center;
}

.kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  color: var(--brand);
  font-weight: 600;
  font-size: 0.9rem;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulseDot 1.8s ease-in-out infinite;
}

.brand {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(3.4rem, 8vw, 5.4rem);
  line-height: 0.95;
  color: var(--brand);
}

.promise {
  margin: 16px 0 0;
  font-size: clamp(1.25rem, 2.4vw, 1.65rem);
  font-weight: 500;
  line-height: 1.4;
  max-width: 16em;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  margin-top: 16px;
}

.hero-stage {
  min-height: 420px;
}

.scene-tabs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--line);
  background: white;
}

.scene-tabs span {
  text-align: center;
  padding: 10px 4px;
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 600;
}

.scene-tabs .on {
  color: var(--brand);
  box-shadow: inset 0 -2px 0 var(--brand);
}

@keyframes floatSoft {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.band {
  padding: 72px 0;
}

.scenes {
  background: rgba(255, 255, 255, 0.45);
  border-block: 1px solid rgba(20, 33, 43, 0.06);
}

.sec-head {
  max-width: 36em;
  margin-bottom: 32px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--brand);
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: 0.06em;
}

.sec-head h2 {
  margin: 0 0 10px;
  font-family: var(--font-display);
  font-size: clamp(1.7rem, 3vw, 2.2rem);
}

.sec-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.courses-band {
  background: rgba(255, 255, 255, 0.35);
}

.cta-band {
  padding: 72px 0 96px;
}

.cta-inner {
  text-align: center;
  padding: 48px 24px;
  border-radius: 28px;
  background:
    radial-gradient(600px 200px at 50% 0%, rgba(232, 163, 23, 0.22), transparent 60%),
    linear-gradient(145deg, #0f6b5c, #0a4f44);
  color: white;
  box-shadow: 0 24px 50px rgba(15, 107, 92, 0.28);
}

.cta-inner h2 {
  margin: 0 0 10px;
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3vw, 2.1rem);
}

.cta-inner p {
  margin: 0 0 22px;
  opacity: 0.9;
}

@media (max-width: 1100px) {
  .portal-grid {
    grid-template-columns: 1fr;
  }

  .hotlinks {
    position: static;
  }

  .intro-body,
  .pillar-grid,
  .cap-grid,
  .course-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .hero-inner {
    grid-template-columns: 1fr;
  }

  .hero {
    min-height: auto;
    padding-top: 28px;
  }

  .compose {
    grid-template-columns: 1fr;
  }

  .landing .pillar-grid,
  .landing .cap-grid,
  .landing .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>
