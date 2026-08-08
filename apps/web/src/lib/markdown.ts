/** 轻量 Markdown → 安全 HTML（学习场景常用子集，无外部依赖） */
export function renderMarkdown(src: string): string {
  if (!src) return ''
  const escaped = escapeHtml(src)
  const blocks: string[] = []
  let text = escaped.replace(/```([\s\S]*?)```/g, (_m, code: string) => {
    const i = blocks.length
    blocks.push(`<pre class="md-code"><code>${code.trim()}</code></pre>`)
    return `\u0000BLOCK${i}\u0000`
  })

  const lines = text.split('\n')
  const out: string[] = []
  let listBuf: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const flushList = () => {
    if (!listBuf.length || !listType) return
    out.push(`<${listType}>${listBuf.join('')}</${listType}>`)
    listBuf = []
    listType = null
  }

  for (const raw of lines) {
    const line = raw
    const ol = line.match(/^\s*\d+\.\s+(.+)$/)
    const ul = line.match(/^\s*[-*]\s+(.+)$/)
    if (ol) {
      if (listType && listType !== 'ol') flushList()
      listType = 'ol'
      listBuf.push(`<li>${inlineMd(ol[1])}</li>`)
      continue
    }
    if (ul) {
      if (listType && listType !== 'ul') flushList()
      listType = 'ul'
      listBuf.push(`<li>${inlineMd(ul[1])}</li>`)
      continue
    }
    flushList()
    const h = line.match(/^(#{1,3})\s+(.+)$/)
    if (h) {
      const level = h[1].length
      out.push(`<h${level + 2} class="md-h">${inlineMd(h[2])}</h${level + 2}>`)
      continue
    }
    if (!line.trim()) {
      out.push('')
      continue
    }
    if (line.includes('\u0000BLOCK')) {
      out.push(line)
    } else {
      out.push(`<p>${inlineMd(line)}</p>`)
    }
  }
  flushList()

  let html = out.join('\n')
  html = html.replace(/\u0000BLOCK(\d+)\u0000/g, (_m, i: string) => blocks[Number(i)] || '')
  return html
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function inlineMd(s: string): string {
  return s
    .replace(/`([^`]+)`/g, '<code class="md-inline">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    )
}
