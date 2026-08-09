const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('eduaiDesktop', {
  getPort: () => ipcRenderer.invoke('get-port'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
})
