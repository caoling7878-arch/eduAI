const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const TOKEN_KEY = 'eduai_admin_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
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

export type User = {
  id: number
  email: string
  display_name: string
  role: string
  status: string
  tags: string
  created_at?: string
}

export type Dashboard = {
  users: number
  teachers: number
  students: number
  courses: number
  classes: number
  questions: number
  orders: number
  checkins_today: number
  active_members?: number
  revenue_total?: number
  revenue_today?: number
  orders_today?: number
  feedback_open?: number
  grade_pending?: number
  learning_minutes_30d?: number
  checkin_trend?: Array<{ day: string; count: number }>
  user_growth?: Array<{ day: string; count: number }>
  order_trend?: Array<{ day: string; count: number; amount?: number }>
  activity_dist?: {
    course_watch?: number
    checkin?: number
    submission?: number
    vocab?: number
  }
  top_students?: Array<{ user_id: number; display_name: string; value: number; label?: string }>
  top_classes?: Array<{ user_id: number; display_name: string; value: number; label?: string }>
  recent_audits: Array<{
    id: number
    user_id?: number
    action: string
    resource: string
    detail: string
    created_at?: string
  }>
  tenant_count?: number
  quota_alert_count?: number
  token_used_total?: number
  token_quota_total?: number
  request_used_total?: number
  request_quota_total?: number
  token_pct_max?: number
  quota_tenants?: Array<{
    id: number
    name: string
    token_pct: number
    request_pct: number
    ends_at?: string
    alert?: boolean
  }>
}

export type StudentOps = {
  id: number
  email: string
  display_name: string
  status: string
  tags: string
  created_at?: string
  checkins: number
  submissions: number
  wrong_open: number
  progress_done: number
  orders: number
  paid_amount: number
  member_plan: string
  is_member: boolean
  last_active?: string
  activity_score: number
}

export const login = (email: string, password: string) =>
  api<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    auth: false,
  })

export const fetchMe = () => api<User>('/auth/me')
export const fetchDashboard = () => api<Dashboard>('/analytics/dashboard')
export const fetchStudentOps = () => api<StudentOps[]>('/analytics/students')
export const fetchUsers = (q = '', role = '') =>
  api<User[]>(`/users?q=${encodeURIComponent(q)}&role=${encodeURIComponent(role)}`)
/** 教师可用：花名册下拉（学员/教师选项），不要求管理员权限 */
export const fetchUserOptions = (role = '') =>
  api<User[]>(`/users/options?role=${encodeURIComponent(role)}`)
export const createUser = (body: Record<string, unknown>) =>
  api<User>('/users', { method: 'POST', body: JSON.stringify(body) })
export const updateUser = (id: number, body: Record<string, unknown>) =>
  api<User>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteUser = (id: number) => api(`/users/${id}`, { method: 'DELETE' })

export const fetchTeachers = () => api<any[]>('/teachers')
export const upsertTeacher = (body: Record<string, unknown>) =>
  api('/teachers', { method: 'POST', body: JSON.stringify(body) })

export const fetchCourses = () => api<any[]>('/courses')
export const createCourse = (body: Record<string, unknown>) =>
  api('/courses', { method: 'POST', body: JSON.stringify(body) })
export const updateCourse = (id: number, body: Record<string, unknown>) =>
  api(`/courses/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteCourse = (id: number) => api(`/courses/${id}`, { method: 'DELETE' })
export const addChapter = (courseId: number, body: Record<string, unknown>) =>
  api(`/courses/${courseId}/chapters`, { method: 'POST', body: JSON.stringify(body) })

export const fetchClasses = () => api<any[]>('/classes')
export const createClass = (body: Record<string, unknown>) =>
  api('/classes', { method: 'POST', body: JSON.stringify(body) })
export const updateClass = (id: number, body: Record<string, unknown>) =>
  api(`/classes/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteClass = (id: number) => api(`/classes/${id}`, { method: 'DELETE' })

export const fetchQuestions = (q = '') =>
  api<any[]>(`/questions?q=${encodeURIComponent(q)}`)
export const createQuestion = (body: Record<string, unknown>) =>
  api('/questions', { method: 'POST', body: JSON.stringify(body) })
export const updateQuestion = (id: number, body: Record<string, unknown>) =>
  api(`/questions/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteQuestion = (id: number) => api(`/questions/${id}`, { method: 'DELETE' })

export const fetchPapers = () => api<any[]>('/papers')
export const createPaper = (body: Record<string, unknown>) =>
  api('/papers', { method: 'POST', body: JSON.stringify(body) })
export const updatePaper = (id: number, body: Record<string, unknown>) =>
  api(`/papers/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

export const fetchAnnouncements = () => api<any[]>('/announcements')
export const createAnnouncement = (body: Record<string, unknown>) =>
  api('/announcements', { method: 'POST', body: JSON.stringify(body) })
export const updateAnnouncement = (id: number, body: Record<string, unknown>) =>
  api(`/announcements/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteAnnouncement = (id: number) =>
  api(`/announcements/${id}`, { method: 'DELETE' })

export const fetchOrders = () => api<any[]>('/orders')
export const fetchPlans = () => api<any[]>('/membership-plans')
export const fetchSettings = () => api<{ items: Record<string, string> }>('/settings')
export const putSettings = (items: Record<string, string>) =>
  api('/settings', { method: 'PUT', body: JSON.stringify({ items }) })

export const fetchAssistants = () => api<any[]>('/assistants')
export const createAssistant = (body: Record<string, unknown>) =>
  api('/assistants', { method: 'POST', body: JSON.stringify(body) })
export const updateAssistant = (id: number, body: Record<string, unknown>) =>
  api(`/assistants/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteAssistant = (id: number) => api(`/assistants/${id}`, { method: 'DELETE' })

export const fetchBases = () => api<any[]>('/knowledge/bases')
export const createBase = (body: Record<string, unknown>) =>
  api('/knowledge/bases', { method: 'POST', body: JSON.stringify(body) })
export const fetchDocs = (kbId: number) => api<any[]>(`/knowledge/bases/${kbId}/docs`)
export const addDoc = (kbId: number, body: Record<string, unknown>) =>
  api(`/knowledge/bases/${kbId}/docs`, { method: 'POST', body: JSON.stringify(body) })
export const deleteDoc = (id: number) => api(`/knowledge/docs/${id}`, { method: 'DELETE' })
export const reindexKb = (kbId: number) =>
  api<{ docs: number; chunks: number; backend?: string; model?: string }>(
    `/knowledge/bases/${kbId}/reindex`,
    { method: 'POST' },
  )
export const searchKb = (body: { kb_id: number; query: string; top_k?: number }) =>
  api<{ items: any[]; embedding?: any }>('/knowledge/search', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const fetchEmbeddingStatus = (probe = false) =>
  api<any>(`/knowledge/embedding-status${probe ? '?probe=true' : ''}`)
export const fetchEmbeddingConfig = () => api<any>('/knowledge/embedding-config')
export const saveEmbeddingConfig = (body: {
  mode: string
  base_url?: string
  api_key?: string | null
  model?: string
}) =>
  api<{ config: any; status: any }>('/knowledge/embedding-config', {
    method: 'PUT',
    body: JSON.stringify(body),
  })

export async function uploadKbDoc(kbId: number, file: File, title?: string) {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const form = new FormData()
  form.append('file', file)
  if (title?.trim()) form.append('title', title.trim())
  const res = await fetch(`${API_BASE}/knowledge/bases/${kbId}/upload`, {
    method: 'POST',
    headers,
    body: form,
  })
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
  return (await res.json()) as any
}

export const generateQuestionsFromKb = (
  kbId: number,
  body: { count?: number; difficulty?: number; topic?: string; query?: string },
) =>
  api<any>(`/knowledge/bases/${kbId}/generate-questions`, {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const generateCourseFromKb = (
  kbId: number,
  body: {
    title?: string
    chapter_count?: number
    query?: string
    create_assistant?: boolean
  },
) =>
  api<any>(`/knowledge/bases/${kbId}/generate-course`, {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const fetchPaperTemplates = () => api<any[]>('/templates/papers')
export const createPaperTemplate = (body: Record<string, unknown>) =>
  api('/templates/papers', { method: 'POST', body: JSON.stringify(body) })
export const instantiatePaperTemplate = (id: number) =>
  api<{ paper_id: number; title: string }>(`/templates/papers/${id}/instantiate`, { method: 'POST' })
export const fetchPptTemplates = () => api<any[]>('/templates/ppt')
export const createPptTemplate = (body: Record<string, unknown>) =>
  api('/templates/ppt', { method: 'POST', body: JSON.stringify(body) })

export const fetchFeedbackAdmin = (status = '') =>
  api<any[]>(`/feedback${status ? `?status=${status}` : ''}`)
export const replyFeedback = (id: number, body: { reply: string; status: string }) =>
  api(`/feedback/${id}/reply`, { method: 'POST', body: JSON.stringify(body) })

export const fetchArticlesAdmin = () => api<any[]>('/articles?published_only=false')
export const createArticle = (body: Record<string, unknown>) =>
  api('/articles', { method: 'POST', body: JSON.stringify(body) })
export const updateArticle = (id: number, body: Record<string, unknown>) =>
  api(`/articles/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteArticle = (id: number) => api(`/articles/${id}`, { method: 'DELETE' })

export const fetchVocabAdmin = () => api<any[]>('/vocab/admin')
export const createVocab = (body: Record<string, unknown>) =>
  api('/vocab/admin', { method: 'POST', body: JSON.stringify(body) })

export const fetchUsageCost = (days = 0) =>
  api<any>(`/ai/usage/cost${days ? `?days=${days}` : ''}`)
export const saveUsagePrices = (prices: Record<string, unknown>) =>
  api('/ai/usage/cost/prices', { method: 'PUT', body: JSON.stringify({ prices }) })
export const exportUsageCostCsv = (days = 0) =>
  downloadAuthed(`/ai/usage/cost/export${days ? `?days=${days}` : ''}`, 'llm-cost.csv')

export const syncDataset = () => api<{ added: number }>('/datasets/sync', { method: 'POST' })
export const fetchDatasetSamples = (query = '') =>
  api<any[]>(`/datasets/samples${query.startsWith('?') || !query ? query || '' : `?${query}`}`)
export const exportDataset = (query = '?format=json&mark_exported=true') =>
  api<any[]>(`/datasets/export${query.startsWith('?') ? query : `?${query}`}`)

export const fetchApiTokens = () => api<any[]>('/api-tokens')
export const createApiToken = (body: Record<string, unknown>) =>
  api<any>('/api-tokens', { method: 'POST', body: JSON.stringify(body) })
export const revokeApiToken = (id: number) =>
  api(`/api-tokens/${id}/revoke`, { method: 'POST' })

export const fetchWorkflowOverview = () => api<any>('/workflows/overview')

export const pushPractice = (body: Record<string, unknown>) =>
  api('/practice/push', { method: 'POST', body: JSON.stringify(body) })

export const generatePpt = (body: Record<string, unknown>) =>
  api<any>('/ppt/generate', { method: 'POST', body: JSON.stringify(body) })
export const fetchPpts = () => api<any[]>('/ppt')

export async function downloadPpt(id: number, title = 'slides') {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE}/ppt/${id}/export`, { headers })
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
  a.download = `${title || 'slides'}.pptx`
  a.click()
  URL.revokeObjectURL(url)
}
export const fetchAudits = () => api<any[]>('/analytics/audits')

export const fetchProviders = () => api<any[]>('/ai/providers')
export const createProvider = (body: Record<string, unknown>) =>
  api('/ai/providers', { method: 'POST', body: JSON.stringify(body) })
export const updateProvider = (id: number, body: Record<string, unknown>) =>
  api(`/ai/providers/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const deleteProvider = (id: number) => api(`/ai/providers/${id}`, { method: 'DELETE' })
export const testProvider = (id: number) =>
  api<{ ok: boolean; latency_ms: number; detail: string }>(`/ai/providers/${id}/test`, {
    method: 'POST',
  })
export const importProviderEnv = () =>
  api('/ai/providers/import-env', { method: 'POST' })

export const fetchPrompts = () => api<any[]>('/ai/prompts')
export const createPrompt = (body: Record<string, unknown>) =>
  api('/ai/prompts', { method: 'POST', body: JSON.stringify(body) })
export const updatePrompt = (id: number, body: Record<string, unknown>) =>
  api(`/ai/prompts/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

export const fetchUsage = () => api<any[]>('/ai/usage')
export const fetchUsageSummary = () => api<any>('/ai/usage/summary')

export const fetchGradeQueue = (status = '', qc = '') => {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  if (qc) q.set('qc', qc)
  const qs = q.toString()
  return api<any[]>(`/grading/queue${qs ? `?${qs}` : ''}`)
}
export const aiScoreGrade = (id: number) =>
  api(`/grading/${id}/ai-score`, { method: 'POST' })
export const reviewGrade = (id: number, body: { teacher_score: number; teacher_feedback: string }) =>
  api(`/grading/${id}/review`, { method: 'POST', body: JSON.stringify(body) })
export const sampleGradeQc = (body: { n?: number; max_confidence?: number; only_reviewed?: boolean } = {}) =>
  api<any[]>('/grading/qc/sample', { method: 'POST', body: JSON.stringify(body) })
export const markGradeQc = (id: number, body: { result: 'passed' | 'failed'; note?: string }) =>
  api(`/grading/${id}/qc`, { method: 'POST', body: JSON.stringify(body) })

export const fetchReportOverview = () => api<any>('/reports/overview')
export const fetchClassReport = (id: number) => api<any>(`/reports/classes/${id}`)

async function downloadAuthed(path: string, filename: string) {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE}${path}`, { headers })
  if (!res.ok) throw new ApiError(res.status, '导出失败')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const exportOverviewCsv = () => downloadAuthed('/reports/overview/export', 'learning_overview.csv')
export const exportClassReportCsv = (id: number) =>
  downloadAuthed(`/reports/classes/${id}/export`, `class_${id}_report.csv`)

export const fetchEbooks = () => api<any[]>('/ebooks')
export const createEbook = (body: Record<string, unknown>) =>
  api('/ebooks', { method: 'POST', body: JSON.stringify(body) })
export const updateEbook = (id: number, body: Record<string, unknown>) =>
  api(`/ebooks/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
export const addEbookChapter = (id: number, body: Record<string, unknown>) =>
  api(`/ebooks/${id}/chapters`, { method: 'POST', body: JSON.stringify(body) })
export const deleteEbook = (id: number) => api(`/ebooks/${id}`, { method: 'DELETE' })

export const fetchLabPages = () => api<any[]>('/labs/pages')
export const patchLabPage = (pageKey: string, body: Record<string, unknown>) =>
  api(`/labs/pages/${pageKey}`, { method: 'PATCH', body: JSON.stringify(body) })
export const attachLab = (body: { lesson_id: number; page_key: string; title?: string }) =>
  api('/labs/attach', { method: 'POST', body: JSON.stringify(body) })
