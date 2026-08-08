/** 管理后台地址（与学员端不同端口，localStorage 不共享） */
export function adminBaseUrl() {
  return (import.meta.env.VITE_ADMIN_URL as string | undefined)?.replace(/\/$/, '') || 'http://127.0.0.1:5174'
}

/** 携带当前 JWT 跳转管理端，避免二次登录 */
export function openAdminConsole(token: string | null, path = '/') {
  const base = adminBaseUrl()
  if (!token) {
    window.location.href = `${base}/login`
    return
  }
  const q = new URLSearchParams({ handoff: token })
  window.location.href = `${base}/login?${q.toString()}&redirect=${encodeURIComponent(path)}`
}
