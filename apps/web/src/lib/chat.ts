import { getToken } from './api'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1'

export type Companion = {
  id: number
  name: string
  avatar: string
  persona: string
  model: string
  knowledge_base_id?: number | null
  suggested_prompts?: string[]
  online?: boolean
  mode?: 'llm' | 'local' | string
}

export type ChatSession = {
  id: number
  assistant_id: number
  title: string
  created_at?: string
  updated_at?: string
}

export type ChatMsg = {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: Array<{ doc_id: number; title: string; snippet: string; score: number }>
  streaming?: boolean
}

export type ChatHealth = {
  online: boolean
  mode: string
  provider?: string | null
  model?: string
}

export async function fetchCompanions() {
  const res = await fetch(`${API_BASE}/ai/chat/assistants`)
  if (!res.ok) throw new Error('加载学伴失败')
  return (await res.json()) as Companion[]
}

export async function fetchChatHealth() {
  const res = await fetch(`${API_BASE}/ai/chat/health`)
  if (!res.ok) return { online: false, mode: 'local' } as ChatHealth
  return (await res.json()) as ChatHealth
}

export async function fetchSessions(assistantId?: number) {
  const q = assistantId ? `?assistant_id=${assistantId}` : ''
  const res = await fetch(`${API_BASE}/ai/chat/sessions${q}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!res.ok) throw new Error('加载会话失败')
  return (await res.json()) as ChatSession[]
}

export async function createSession(assistantId: number, title = '新对话') {
  const res = await fetch(`${API_BASE}/ai/chat/sessions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ assistant_id: assistantId, title }),
  })
  if (!res.ok) throw new Error('创建会话失败')
  return (await res.json()) as ChatSession
}

export async function renameSession(sessionId: number, title: string) {
  const res = await fetch(`${API_BASE}/ai/chat/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error('重命名失败')
  return (await res.json()) as ChatSession
}

export async function deleteSession(sessionId: number) {
  const res = await fetch(`${API_BASE}/ai/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!res.ok) throw new Error('删除会话失败')
  return (await res.json()) as { status: string }
}

export async function fetchMessages(sessionId: number) {
  const res = await fetch(`${API_BASE}/ai/chat/sessions/${sessionId}/messages`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!res.ok) throw new Error('加载消息失败')
  const rows = (await res.json()) as Array<{
    id: number
    role: string
    content: string
    citations: ChatMsg['citations']
  }>
  return rows.map(
    (r) =>
      ({
        id: r.id,
        role: r.role as ChatMsg['role'],
        content: r.content,
        citations: r.citations,
      }) satisfies ChatMsg,
  )
}

export type StreamHandlers = {
  onCitations?: (items: NonNullable<ChatMsg['citations']>) => void
  onDelta?: (text: string) => void
  onDone?: (full: string) => void
  onError?: (message: string, code?: string) => void
}

export function streamChat(
  sessionId: number,
  message: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
  opts?: { regenerate?: boolean },
) {
  return fetch(`${API_BASE}/ai/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      regenerate: !!opts?.regenerate,
    }),
    signal,
  }).then(async (res) => {
    if (!res.ok || !res.body) {
      let detail = res.statusText
      try {
        const data = await res.json()
        if (typeof data.detail === 'string') detail = data.detail
      } catch {
        /* ignore */
      }
      handlers.onError?.(detail || '流式请求失败')
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts.pop() || ''
      for (const line of parts) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const data = trimmed.slice(5).trim()
        if (data === '[DONE]') return
        try {
          const evt = JSON.parse(data) as {
            type: string
            content?: string
            message?: string
            code?: string
            items?: NonNullable<ChatMsg['citations']>
          }
          if (evt.type === 'citations' && evt.items) handlers.onCitations?.(evt.items)
          else if (evt.type === 'delta' && evt.content) handlers.onDelta?.(evt.content)
          else if (evt.type === 'done' && evt.content != null) handlers.onDone?.(evt.content)
          else if (evt.type === 'error') handlers.onError?.(evt.message || '生成失败', evt.code)
        } catch {
          /* ignore partial json */
        }
      }
    }
  })
}
