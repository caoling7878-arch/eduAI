export type DesktopUpdateStatus = {
  state?: 'idle' | 'checking' | 'available' | 'downloading' | 'installing' | 'uptodate' | 'error'
  currentVersion?: string
  latestVersion?: string
  percent?: number
  message?: string
  available?: boolean
}

export type EduaiDesktopApi = {
  getPort: () => Promise<number>
  getVersion: () => Promise<string>
  openExternal: (url: string) => Promise<void>
  checkForUpdate: () => Promise<DesktopUpdateStatus>
  startUpdate: () => Promise<DesktopUpdateStatus>
  openReleasePage: () => Promise<void>
  onUpdateStatus: (cb: (data: DesktopUpdateStatus) => void) => () => void
}

declare global {
  interface Window {
    eduaiDesktop?: EduaiDesktopApi
  }
}

export {}
