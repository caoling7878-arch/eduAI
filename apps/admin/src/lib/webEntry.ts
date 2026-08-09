/** 学员端地址（开发双端口；桌面/生产同源根路径） */
export function webBaseUrl() {
  const env = (import.meta.env.VITE_WEB_URL as string | undefined)?.replace(/\/$/, '')
  if (env !== undefined && env !== '') return env
  if (import.meta.env.PROD) return window.location.origin
  return 'http://127.0.0.1:5173'
}
