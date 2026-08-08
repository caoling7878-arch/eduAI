import { getToken } from './api'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1'

export type GeometryLabSuggestion = {
  page_key: string
  title: string
  category: string
  preview_path: string
  knowledge_points: string
}

export type GeometryChatTurn = {
  role: 'user' | 'assistant'
  content: string
  steps?: string[]
  knowledge_points?: string[]
  suggested_labs?: GeometryLabSuggestion[]
  source?: string
}

export type GeometryStreamHandlers = {
  onDelta?: (text: string) => void
  onMeta?: (meta: {
    source: string
    steps: string[]
    knowledge_points: string[]
    suggested_labs: GeometryLabSuggestion[]
  }) => void
  onDone?: (full: string) => void
  onError?: (message: string, code?: string) => void
}

export function streamGeometryTutor(
  message: string,
  history: Array<{ role: 'user' | 'assistant'; content: string }>,
  handlers: GeometryStreamHandlers,
  opts?: { imageBase64?: string; mime?: string; signal?: AbortSignal },
) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  return fetch(`${API_BASE}/labs/geometry-tutor/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      history,
      image_base64: opts?.imageBase64 || '',
      mime: opts?.mime || 'image/jpeg',
    }),
    signal: opts?.signal,
  }).then(async (res) => {
    if (!res.ok || !res.body) {
      let detail = res.statusText
      try {
        const data = await res.json()
        if (typeof data.detail === 'string') detail = data.detail
      } catch {
        /* ignore */
      }
      handlers.onError?.(detail || '讲解请求失败')
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
            source?: string
            steps?: string[]
            knowledge_points?: string[]
            suggested_labs?: GeometryLabSuggestion[]
          }
          if (evt.type === 'delta' && evt.content) handlers.onDelta?.(evt.content)
          else if (evt.type === 'meta') {
            handlers.onMeta?.({
              source: evt.source || 'heuristic',
              steps: evt.steps || [],
              knowledge_points: evt.knowledge_points || [],
              suggested_labs: evt.suggested_labs || [],
            })
          } else if (evt.type === 'done' && evt.content != null) handlers.onDone?.(evt.content)
          else if (evt.type === 'error') handlers.onError?.(evt.message || '生成失败', evt.code)
        } catch {
          /* ignore partial json */
        }
      }
    }
  })
}
