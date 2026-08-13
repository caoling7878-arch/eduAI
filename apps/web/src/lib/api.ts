const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function tokenKey() {
  return 'eduai_token'
}

export function getToken(): string | null {
  return localStorage.getItem(tokenKey())
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(tokenKey(), token)
  else localStorage.removeItem(tokenKey())
}

export async function api<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (options.auth !== false) {
    const token = getToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    let message = res.statusText
    try {
      const data = (await res.json()) as { detail?: string | Array<{ msg?: string }> }
      if (typeof data.detail === 'string') message = data.detail
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export interface User {
  id: number
  email: string
  display_name: string
  role?: string
  status?: string
  tags?: string
  created_at?: string
}

export interface CourseSummary {
  course_id: string
  total_items: number
  started: number
  completed: number
  percent: number
}

export interface ProgressItem {
  course_id: string
  item_id: string
  status: 'started' | 'completed' | string
  score: number
  meta: Record<string, unknown>
  updated_at?: string
}

export interface ProgressSummary {
  user: User
  courses: CourseSummary[]
  items: ProgressItem[]
  vocab_streak_days?: number
  vocab_streak_badge?: boolean
}

export function register(body: {
  email: string
  password: string
  display_name: string
}) {
  return api<{ access_token: string }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(body),
    auth: false,
  })
}

export function login(body: { email: string; password: string }) {
  return api<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
    auth: false,
  })
}

export function fetchMe() {
  return api<User>('/auth/me')
}

export function fetchProgress() {
  return api<ProgressSummary>('/progress/me')
}

export function upsertProgress(body: {
  course_id: string
  item_id: string
  status: 'started' | 'completed'
  score?: number
  meta?: Record<string, unknown>
}) {
  return api<ProgressItem>('/progress/upsert', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export type CheckinInfo = {
  day: string
  streak: number
  total: number
  checked_today: boolean
}

export type StudyPlan = {
  id: number
  title: string
  done: boolean
  created_at?: string
}

export type Announcement = {
  id: number
  title: string
  body: string
  published: boolean
  views: number
  created_at?: string
}

export type Paper = {
  id: number
  title: string
  status: string
  question_ids: number[]
}

export type Question = {
  id: number
  type: string
  stem: string
  options: string[]
  answer: string
  analysis: string
  knowledge_points: string
  difficulty: number
}

export type MembershipPlan = {
  id: number
  name: string
  price: number
  days: number
  benefits: string
}

export const fetchCheckin = () => api<CheckinInfo>('/checkins/me')
export const doCheckin = () => api<CheckinInfo>('/checkins/me', { method: 'POST' })
export const fetchStudyPlans = () => api<StudyPlan[]>('/study-plans')
export const addStudyPlan = (title: string) =>
  api<StudyPlan>('/study-plans', { method: 'POST', body: JSON.stringify({ title }) })
export const toggleStudyPlan = (id: number) =>
  api<StudyPlan>(`/study-plans/${id}/toggle`, { method: 'PATCH' })
export const deleteStudyPlan = (id: number) =>
  api(`/study-plans/${id}`, { method: 'DELETE' })
export const fetchAnnouncements = () =>
  api<Announcement[]>('/announcements?published_only=true')
export const fetchAnnouncement = (id: number) => api<Announcement>(`/announcements/${id}`)
export const fetchPapers = () => api<Paper[]>('/papers')
export const fetchQuiz = (paperId: number) =>
  api<{ paper: Paper; questions: Array<Omit<Question, 'answer' | 'analysis' | 'version'>> }>(
    `/papers/${paperId}/quiz`,
  )
export const submitPaper = (paper_id: number, answers: Record<string, string>) =>
  api<{ id: number; score: number; total: number }>('/papers/submit', {
    method: 'POST',
    body: JSON.stringify({ paper_id, answers }),
  })
export const fetchMembershipPlans = () => api<MembershipPlan[]>('/membership-plans')
export const createOrder = (body: { plan_id?: number; course_id?: number }) =>
  api('/orders', { method: 'POST', body: JSON.stringify(body) })
export const fetchMyOrders = () => api<any[]>('/orders/me')
export const fetchCatalogCourses = () => api<any[]>('/courses?published_only=true')

export const fetchWrongbook = (mastered?: boolean) => {
  const q = mastered === undefined ? '' : `?mastered=${mastered}`
  return api<any[]>(`/wrongbook${q}`)
}
export const masterWrong = (id: number) => api(`/wrongbook/${id}/master`, { method: 'POST' })
export const deleteWrong = (id: number) => api(`/wrongbook/${id}`, { method: 'DELETE' })

export const fetchNotifications = () => api<any[]>('/notifications/me')
export const fetchUnreadCount = () => api<{ count: number }>('/notifications/me/unread-count')
export const markNotificationRead = (id: number) =>
  api(`/notifications/me/${id}/read`, { method: 'POST' })
export const markAllNotificationsRead = () =>
  api('/notifications/me/read-all', { method: 'POST' })

export const fetchMyReport = () => api<any>('/reports/me')
export const fetchMyGrades = () => api<any[]>('/grading/me')

export const fetchEbooks = () => api<any[]>('/ebooks?published_only=true')
export const fetchEbook = (id: number) => api<any>(`/ebooks/${id}`)

export const scoreSpeech = (expected: string, transcript: string) =>
  api<{
    score: number
    level: string
    matched: string[]
    missing: string[]
    feedback: string
  }>('/speech/score', {
    method: 'POST',
    body: JSON.stringify({ expected, transcript }),
    auth: false,
  })

export async function exportMyData() {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE}/privacy/export`, { headers })
  if (!res.ok) {
    let message = res.statusText
    try {
      const data = (await res.json()) as { detail?: string }
      if (data.detail) message = data.detail
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'eduai-my-data.json'
  a.click()
  URL.revokeObjectURL(url)
}

export const deleteMyAccount = (password: string, confirm = 'DELETE') =>
  api<{ status: string; message: string }>('/privacy/delete-account', {
    method: 'POST',
    body: JSON.stringify({ password, confirm }),
  })

export const fetchMyBilling = () =>
  api<{
    tenant: { id: number; name: string; slug: string; status: string } | null
    subscription: {
      pack_name: string
      tokens_used: number
      token_quota: number
      requests_used: number
      request_quota: number
      ends_at: string
      token_pct: number
      request_pct: number
    } | null
  }>('/billing/me')
