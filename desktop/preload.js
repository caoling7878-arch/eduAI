const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('eduaiDesktop', {
  getPort: () => ipcRenderer.invoke('get-port'),
  getVersion: () => ipcRenderer.invoke('get-version'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  checkForUpdate: () => ipcRenderer.invoke('check-for-update'),
  startUpdate: () => ipcRenderer.invoke('start-update'),
  openReleasePage: () => ipcRenderer.invoke('open-release-page'),
  onUpdateStatus: (cb) => {
    const listener = (_event, data) => cb(data)
    ipcRenderer.on('update-status', listener)
    return () => ipcRenderer.removeListener('update-status', listener)
  },
})
