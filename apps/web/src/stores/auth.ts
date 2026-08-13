import { computed, reactive, readonly } from 'vue'
import {
  ApiError,
  fetchMe,
  fetchProgress,
  getToken,
  login as apiLogin,
  register as apiRegister,
  setToken,
  upsertProgress,
  type CourseSummary,
  type ProgressItem,
  type User,
} from '../lib/api'

const state = reactive({
  ready: false,
  user: null as User | null,
  courses: [] as CourseSummary[],
  items: [] as ProgressItem[],
  vocab_streak_days: 0,
  vocab_streak_badge: false,
  error: '' as string,
})

async function hydrate() {
  state.error = ''
  if (!getToken()) {
    state.user = null
    state.courses = []
    state.items = []
    state.vocab_streak_days = 0
    state.vocab_streak_badge = false
    state.ready = true
    return
  }
  try {
    const progress = await fetchProgress()
    state.user = progress.user
    state.courses = progress.courses
    state.items = progress.items
    state.vocab_streak_days = progress.vocab_streak_days || 0
    state.vocab_streak_badge = !!progress.vocab_streak_badge
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      setToken(null)
      state.user = null
      state.courses = []
      state.items = []
      state.vocab_streak_days = 0
      state.vocab_streak_badge = false
    } else {
      try {
        state.user = await fetchMe()
      } catch {
        setToken(null)
        state.user = null
      }
    }
  } finally {
    state.ready = true
  }
}

async function login(email: string, password: string) {
  const { access_token } = await apiLogin({ email, password })
  setToken(access_token)
  await hydrate()
}

async function register(email: string, password: string, displayName: string) {
  const { access_token } = await apiRegister({
    email,
    password,
    display_name: displayName,
  })
  setToken(access_token)
  await hydrate()
}

function applyVocabStreak(days: number, badge: boolean) {
  state.vocab_streak_days = days
  state.vocab_streak_badge = badge
}

function logout() {
  setToken(null)
  state.user = null
  state.courses = []
  state.items = []
  state.vocab_streak_days = 0
  state.vocab_streak_badge = false
  state.error = ''
}

async function track(
  courseId: string,
  itemId: string,
  status: 'started' | 'completed',
  meta: Record<string, unknown> = {},
  score = 0,
) {
  if (!state.user) return null
  try {
    const item = await upsertProgress({
      course_id: courseId,
      item_id: itemId,
      status,
      score,
      meta,
    })
    const idx = state.items.findIndex(
      (i) => i.course_id === courseId && i.item_id === itemId,
    )
    if (idx >= 0) state.items[idx] = item
    else state.items.push(item)

    // 乐观更新汇总
    const summary = state.courses.find((c) => c.course_id === courseId)
    if (summary) {
      const courseItems = state.items.filter((i) => i.course_id === courseId)
      const completed = courseItems.filter((i) => i.status === 'completed').length
      const started = courseItems.length
      summary.started = Math.min(started, summary.total_items)
      summary.completed = Math.min(completed, summary.total_items)
      summary.percent = summary.total_items
        ? Math.round((summary.completed * 100) / summary.total_items)
        : 0
    } else {
      await hydrate()
    }
    return item
  } catch (err) {
    state.error = err instanceof Error ? err.message : '进度同步失败'
    return null
  }
}

function coursePercent(courseId: string) {
  return state.courses.find((c) => c.course_id === courseId)?.percent ?? 0
}

function isCompleted(courseId: string, itemId: string) {
  return state.items.some(
    (i) => i.course_id === courseId && i.item_id === itemId && i.status === 'completed',
  )
}

function isStarted(courseId: string, itemId: string) {
  return state.items.some((i) => i.course_id === courseId && i.item_id === itemId)
}

export function useAuth() {
  return {
    state: readonly(state),
    isLoggedIn: computed(() => !!state.user),
    isStaff: computed(() => state.user?.role === 'admin' || state.user?.role === 'teacher'),
    isAdmin: computed(() => state.user?.role === 'admin'),
    hydrate,
    login,
    register,
    logout,
    applyVocabStreak,
    track,
    coursePercent,
    isCompleted,
    isStarted,
  }
}
