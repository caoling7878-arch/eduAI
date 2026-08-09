/** 管理后台地址（开发双端口；桌面/生产同源 /admin） */
export function adminBaseUrl() {
  const env = (import.meta.env.VITE_ADMIN_URL as string | undefined)?.replace(/\/$/, '')
  if (env) return env
  if (import.meta.env.PROD) return `${window.location.origin}/admin`
  return 'http://127.0.0.1:5174'
}

/** 携带当前 JWT 跳转管理端，避免二次登录 */
export function openAdminConsole(token: string | null, path = '/') {
  const base = adminBaseUrl().replace(/\/$/, '')
  if (!token) {
    window.location.href = `${base}/login`
    return
  }
  const q = new URLSearchParams({ handoff: token })
  // 必须以 /admin/login 形式进入，由后端 SPA 回退到 index.html
  window.location.href = `${base}/login?${q.toString()}&redirect=${encodeURIComponent(path)}`
}
