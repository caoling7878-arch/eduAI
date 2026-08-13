const { app, BrowserWindow, Tray, Menu, nativeImage, shell, ipcMain, dialog } = require('electron')
const { spawn } = require('child_process')
const fs = require('fs')
const http = require('http')
const path = require('path')
const { setupUpdater, checkForUpdate, promptCheckOrUpdate } = require('./updater')

const PORT = Number(process.env.EDUAI_PORT || 18765)
const HOST = process.env.EDUAI_HOST || '127.0.0.1'
const APP_URL = `http://${HOST}:${PORT}/`

let mainWindow = null
let tray = null
let serverProc = null
let quitting = false

function resourcesRoot() {
  if (app.isPackaged) return process.resourcesPath
  return path.join(__dirname, 'resources')
}

function serverBinary() {
  const root = path.join(resourcesRoot(), 'server')
  if (process.platform === 'win32') {
    const exe = path.join(root, 'eduai-server.exe')
    if (fs.existsSync(exe)) return exe
  } else {
    const bin = path.join(root, 'eduai-server')
    if (fs.existsSync(bin)) return bin
  }
  // Dev fallback: run Python entry from monorepo
  return null
}

function repoApiDir() {
  return path.join(__dirname, '..', 'apps', 'api')
}

function ensureDataDir() {
  const dir = path.join(app.getPath('userData'), 'data')
  fs.mkdirSync(dir, { recursive: true })
  return dir
}

function startServer() {
  if (serverProc) return

  const dataDir = ensureDataDir()
  const env = {
    ...process.env,
    EDUAI_HOST: HOST,
    EDUAI_PORT: String(PORT),
    EDUAI_DATA_DIR: dataDir,
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',
  }

  const bin = serverBinary()
  const spawnOpts = {
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    shell: false,
  }
  if (bin) {
    // onedir: exe 与 _internal 同级，cwd 必须是 server 目录
    serverProc = spawn(bin, [], { ...spawnOpts, cwd: path.dirname(bin) })
  } else {
    const apiDir = repoApiDir()
    const py = process.platform === 'win32' ? 'python' : 'python3'
    serverProc = spawn(py, ['desktop_entry.py'], { ...spawnOpts, cwd: apiDir })
  }

  const logFile = path.join(app.getPath('userData'), 'server.log')
  const logStream = fs.createWriteStream(logFile, { flags: 'a' })
  serverProc.stdout?.pipe(logStream)
  serverProc.stderr?.pipe(logStream)

  serverProc.on('exit', (code, signal) => {
    serverProc = null
    if (!quitting && mainWindow && !mainWindow.isDestroyed()) {
      dialog.showMessageBox(mainWindow, {
        type: 'error',
        title: 'eduAI',
        message: '本地服务已退出',
        detail: `code=${code ?? '-'} signal=${signal ?? '-'}\n日志: ${logFile}`,
      })
    }
  })
}

function stopServer() {
  if (!serverProc) return
  const proc = serverProc
  serverProc = null
  try {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(proc.pid), '/f', '/t'], { windowsHide: true })
    } else {
      proc.kill('SIGTERM')
      setTimeout(() => {
        try {
          proc.kill('SIGKILL')
        } catch {
          /* ignore */
        }
      }, 1500)
    }
  } catch {
    /* ignore */
  }
}

function waitForHealth(timeoutMs = 90000) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(`http://${HOST}:${PORT}/api/v1/health`, (res) => {
        res.resume()
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
          resolve()
          return
        }
        retry()
      })
      req.on('error', retry)
      req.setTimeout(1500, () => {
        req.destroy()
        retry()
      })
    }
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error('服务启动超时'))
        return
      }
      setTimeout(tick, 400)
    }
    tick()
  })
}

function appTitle() {
  return `eduAI v${app.getVersion()}`
}

function showAbout() {
  const win = mainWindow && !mainWindow.isDestroyed() ? mainWindow : undefined
  dialog.showMessageBox(win, {
    type: 'info',
    title: '关于 eduAI',
    message: appTitle(),
    detail: '智慧教育云桌面版\nWindows / macOS 通用',
  })
}

function createWindow() {
  const icon = nativeImage.createFromPath(path.join(__dirname, 'build', 'icon.png'))
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 960,
    minHeight: 640,
    title: appTitle(),
    icon,
    backgroundColor: '#0b3d36',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  })

  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.on('page-title-updated', (e) => {
    e.preventDefault()
    mainWindow?.setTitle(appTitle())
  })
  mainWindow.loadFile(path.join(__dirname, 'splash.html')).then(() => {
    const ver = JSON.stringify(`v${app.getVersion()}`)
    mainWindow?.webContents.executeJavaScript(
      `var el=document.getElementById('app-ver'); if(el) el.textContent=${ver};`,
    )
  })

  mainWindow.on('close', (e) => {
    if (!quitting && process.platform === 'darwin') {
      e.preventDefault()
      mainWindow?.hide()
    }
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

function createTray() {
  const iconPath = path.join(__dirname, 'build', 'icon.png')
  let image = nativeImage.createFromPath(iconPath)
  if (!image.isEmpty()) {
    image = image.resize({ width: 18, height: 18 })
  }
  tray = new Tray(image.isEmpty() ? nativeImage.createEmpty() : image)
  tray.setToolTip(appTitle())
  const menu = Menu.buildFromTemplate([
    {
      label: '打开 eduAI',
      click: () => {
        if (!mainWindow) createWindow()
        mainWindow?.show()
        mainWindow?.focus()
      },
    },
    {
      label: '检查更新',
      click: () => {
        promptCheckOrUpdate()
      },
    },
    {
      label: '打开学员端（浏览器）',
      click: () => shell.openExternal(APP_URL),
    },
    {
      label: '打开管理端（浏览器）',
      click: () => shell.openExternal(`${APP_URL}admin/`),
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        quitting = true
        app.quit()
      },
    },
  ])
  tray.setContextMenu(menu)
  tray.on('click', () => {
    if (!mainWindow) createWindow()
    mainWindow?.show()
    mainWindow?.focus()
  })
}

function buildAppMenu() {
  const template = [
    ...(process.platform === 'darwin'
      ? [
          {
            label: app.name,
            submenu: [
              { role: 'about' },
              {
                label: `版本 ${app.getVersion()}`,
                enabled: false,
              },
              { type: 'separator' },
              { role: 'hide' },
              { role: 'hideOthers' },
              { role: 'unhide' },
              { type: 'separator' },
              { role: 'quit' },
            ],
          },
        ]
      : []),
    // macOS 上未注册 Edit 菜单时，Cmd+C/V/X 等在输入框中会失效（含 API Key、模型名、地址等）
    {
      label: '编辑',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'pasteAndMatchStyle' },
        { role: 'delete' },
        { role: 'selectAll' },
      ],
    },
    {
      label: '窗口',
      submenu: [
        { role: 'reload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'minimize' },
        { role: 'close' },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '检查更新',
          click: () => {
            promptCheckOrUpdate()
          },
        },
        {
          label: '关于 eduAI',
          click: () => showAbout(),
        },
        { type: 'separator' },
        {
          label: '学员端',
          click: () => shell.openExternal(APP_URL),
        },
        {
          label: '管理端',
          click: () => shell.openExternal(`${APP_URL}admin/`),
        },
        {
          label: 'API 文档',
          click: () => shell.openExternal(`http://${HOST}:${PORT}/docs`),
        },
      ],
    },
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

ipcMain.handle('get-port', () => PORT)
ipcMain.handle('open-external', (_e, url) => {
  if (typeof url === 'string') shell.openExternal(url)
})

setupUpdater({
  getWindow: () => mainWindow,
  stopServer,
  setQuitting: (v) => {
    quitting = v
  },
})

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })

  app.whenReady().then(async () => {
    app.setAboutPanelOptions({
      applicationName: 'eduAI',
      applicationVersion: app.getVersion(),
      version: app.getVersion(),
      copyright: 'Copyright © eduAI',
    })
    buildAppMenu()
    createTray()
    createWindow()
    startServer()
    try {
      await waitForHealth()
      try {
        await mainWindow?.webContents.session.clearCache()
      } catch {
        /* ignore */
      }
      await mainWindow?.loadURL(APP_URL)
      setTimeout(() => {
        checkForUpdate(false).catch(() => {})
      }, 4000)
    } catch (err) {
      const logFile = path.join(app.getPath('userData'), 'server.log')
      dialog.showErrorBox(
        'eduAI 启动失败',
        `${err instanceof Error ? err.message : String(err)}\n\n请查看日志:\n${logFile}`,
      )
    }
  })

  app.on('activate', () => {
    if (!mainWindow) createWindow()
    else mainWindow.show()
  })

  app.on('before-quit', () => {
    quitting = true
    stopServer()
  })

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      quitting = true
      app.quit()
    }
  })
}
