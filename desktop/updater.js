const { ipcMain, dialog, app, shell } = require('electron')
const { spawn } = require('child_process')
const https = require('https')
const http = require('http')
const fs = require('fs')
const os = require('os')
const path = require('path')

const GH_OWNER = 'caoling7878-arch'
const GH_REPO = 'eduAI'
const UA = 'eduAI-desktop'
const CACHE_MS = 8 * 60 * 1000

let getWindow = () => null
let stopServer = () => {}
let setQuitting = () => {}
let cache = { at: 0, info: null }
let busy = false

function emit(payload) {
  const win = getWindow()
  if (win && !win.isDestroyed()) {
    win.webContents.send('update-status', payload)
  }
}

function parseVer(raw) {
  return String(raw || '')
    .replace(/^v/i, '')
    .split(/[^\d]+/)
    .filter(Boolean)
    .map((n) => parseInt(n, 10) || 0)
}

function isNewer(remote, local) {
  const a = parseVer(remote)
  const b = parseVer(local)
  const n = Math.max(a.length, b.length, 3)
  for (let i = 0; i < n; i++) {
    const x = a[i] || 0
    const y = b[i] || 0
    if (x > y) return true
    if (x < y) return false
  }
  return false
}

function requestText(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https:') ? https : http
    const req = mod.get(
      url,
      {
        headers: { 'User-Agent': UA, ...headers },
      },
      (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume()
          requestText(res.headers.location, headers).then(resolve, reject)
          return
        }
        let body = ''
        res.setEncoding('utf8')
        res.on('data', (c) => {
          body += c
        })
        res.on('end', () => {
          if (!res.statusCode || res.statusCode >= 400) {
            reject(new Error(`GitHub ${res.statusCode || '?'}：${body.slice(0, 160) || '无法获取版本信息'}`))
            return
          }
          resolve(body)
        })
      },
    )
    req.on('error', reject)
    req.setTimeout(20000, () => {
      req.destroy()
      reject(new Error('连接 GitHub 超时，请检查网络后重试'))
    })
  })
}

function downloadFile(url, dest, onProgress, redirects = 0) {
  return new Promise((resolve, reject) => {
    if (redirects > 10) {
      reject(new Error('下载重定向过多'))
      return
    }
    const mod = url.startsWith('https:') ? https : http
    const req = mod.get(
      url,
      {
        headers: { 'User-Agent': UA, Accept: 'application/octet-stream' },
      },
      (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume()
          downloadFile(res.headers.location, dest, onProgress, redirects + 1).then(resolve, reject)
          return
        }
        if (res.statusCode !== 200) {
          res.resume()
          reject(new Error(`下载失败 HTTP ${res.statusCode}`))
          return
        }
        const total = Number(res.headers['content-length'] || 0)
        let received = 0
        const out = fs.createWriteStream(dest)
        res.on('data', (chunk) => {
          received += chunk.length
          if (total > 0) onProgress(Math.min(99, Math.round((received / total) * 100)), received, total)
        })
        res.pipe(out)
        out.on('finish', () => {
          out.close(() => {
            onProgress(100, received, total)
            resolve()
          })
        })
        out.on('error', reject)
        res.on('error', reject)
      },
    )
    req.on('error', reject)
    req.setTimeout(15 * 60 * 1000, () => {
      req.destroy()
      reject(new Error('下载超时，请检查网络后重试'))
    })
  })
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { ...opts, windowsHide: true })
    let out = ''
    child.stdout?.on('data', (d) => {
      out += d.toString()
    })
    child.stderr?.on('data', (d) => {
      out += d.toString()
    })
    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) resolve(out)
      else reject(new Error(out.trim() || `${cmd} 退出码 ${code}`))
    })
  })
}

function pickAsset(assets) {
  const list = Array.isArray(assets) ? assets : []
  if (process.platform === 'win32') {
    return (
      list.find((a) => String(a.name).toLowerCase() === 'install.exe') ||
      list.find((a) => /\.exe$/i.test(a.name || ''))
    )
  }
  if (process.platform === 'darwin') {
    const tag = process.arch === 'arm64' ? 'arm64' : 'x64'
    // 未公证时 DMG 替换 .app 常被 Gatekeeper 拦截，优先用 PKG
    return (
      list.find((a) => new RegExp(`eduAI-.*-${tag}\\.pkg$`, 'i').test(a.name || '')) ||
      list.find((a) => /\.pkg$/i.test(a.name || '')) ||
      list.find((a) => new RegExp(`eduAI-.*-${tag}\\.dmg$`, 'i').test(a.name || '')) ||
      list.find((a) => /\.dmg$/i.test(a.name || ''))
    )
  }
  return null
}

function parseMountPoint(text) {
  const m = String(text || '').match(/\/Volumes\/[^\n\r]+/)
  return m ? m[0].trim() : ''
}

async function fetchLatest() {
  const body = await requestText(
    `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/releases/latest`,
    {
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
  )
  const data = JSON.parse(body)
  const currentVersion = app.getVersion()
  const latestVersion = String(data.tag_name || data.name || '').replace(/^v/i, '')
  const asset = pickAsset(data.assets || [])
  const available = isNewer(latestVersion, currentVersion)
  return {
    currentVersion,
    latestVersion,
    available,
    notes: String(data.body || '').slice(0, 800),
    htmlUrl: data.html_url || `https://github.com/${GH_OWNER}/${GH_REPO}/releases/latest`,
    assetName: asset?.name || '',
    downloadUrl: asset?.browser_download_url || '',
    size: Number(asset?.size || 0),
  }
}

async function checkForUpdate(force = false) {
  emit({ state: 'checking', currentVersion: app.getVersion() })
  try {
    if (!force && cache.info && Date.now() - cache.at < CACHE_MS) {
      const info = cache.info
      emit({
        state: info.available ? 'available' : 'uptodate',
        ...info,
      })
      return info
    }
    const info = await fetchLatest()
    cache = { at: Date.now(), info }
    if (info.available && !info.downloadUrl) {
      const err = {
        ...info,
        available: false,
        state: 'error',
        message: '已发布新版本，但没有找到当前系统对应的安装包',
      }
      emit(err)
      return err
    }
    emit({
      state: info.available ? 'available' : 'uptodate',
      ...info,
    })
    return info
  } catch (err) {
    const payload = {
      state: 'error',
      currentVersion: app.getVersion(),
      message: err instanceof Error ? err.message : String(err),
    }
    emit(payload)
    return payload
  }
}

function applyWindows(installerPath) {
  const ps = [
    `$pidToWait = ${process.pid}`,
    'while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 1 }',
    `Start-Process -FilePath ${JSON.stringify(installerPath)} -Wait`,
  ].join('; ')
  const child = spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], {
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  })
  child.unref()
}

function applyMac(stagedApp) {
  const sh = path.join(os.tmpdir(), 'eduai-apply-update.sh')
  const pid = process.pid
  fs.writeFileSync(
    sh,
    `#!/bin/bash
set -euo pipefail
PID="${pid}"
SRC=${JSON.stringify(stagedApp)}
DEST="/Applications/eduAI.app"
while /bin/kill -0 "$PID" 2>/dev/null; do sleep 0.4; done
sleep 0.8
rm -rf "$DEST"
/bin/cp -R "$SRC" "$DEST"
xattr -cr "$DEST" >/dev/null 2>&1 || true
codesign --force --deep --sign - "$DEST" >/dev/null 2>&1 || true
open "$DEST"
rm -rf "$SRC"
rm -f "$0"
`,
    'utf8',
  )
  fs.chmodSync(sh, 0o755)
  const child = spawn('/bin/bash', [sh], { detached: true, stdio: 'ignore' })
  child.unref()
}

function relaunchMacAfterQuit() {
  const sh = path.join(os.tmpdir(), 'eduai-relaunch.sh')
  const pid = process.pid
  fs.writeFileSync(
    sh,
    `#!/bin/bash
PID="${pid}"
while /bin/kill -0 "$PID" 2>/dev/null; do sleep 0.3; done
sleep 0.6
xattr -cr /Applications/eduAI.app >/dev/null 2>&1 || true
open /Applications/eduAI.app
rm -f "$0"
`,
    'utf8',
  )
  fs.chmodSync(sh, 0o755)
  const child = spawn('/bin/bash', [sh], { detached: true, stdio: 'ignore' })
  child.unref()
}

async function installMacPkg(pkgPath) {
  emit({ state: 'installing', message: '请在系统弹窗中输入 Mac 登录密码以完成安装…' })
  const script =
    'do shell script "/usr/sbin/installer -pkg " & quoted form of ' +
    JSON.stringify(pkgPath) +
    ' & " -target /" with administrator privileges'
  try {
    await run('osascript', ['-e', script])
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    if (/User canceled|-128|用户已取消|未输入/i.test(msg)) {
      throw new Error('已取消安装：未输入 Mac 密码')
    }
    throw new Error(msg.trim() || 'PKG 安装失败')
  }
}

async function installMacDmg(dmgPath) {
  emit({ state: 'installing', message: '正在安装…' })
  const out = await run('hdiutil', ['attach', '-nobrowse', dmgPath])
  const volume = parseMountPoint(out) || '/Volumes/eduAI 安装'
  const appSrc = path.join(volume, 'eduAI.app')
  if (!fs.existsSync(appSrc)) {
    try {
      await run('hdiutil', ['detach', volume, '-quiet'])
    } catch {
      /* ignore */
    }
    throw new Error('安装盘中未找到 eduAI.app')
  }
  const staged = path.join(os.tmpdir(), 'eduAI-update.app')
  fs.rmSync(staged, { recursive: true, force: true })
  await run('/bin/cp', ['-R', appSrc, staged])
  try {
    await run('hdiutil', ['detach', volume, '-quiet'])
  } catch {
    /* ignore */
  }
  applyMac(staged)
}

async function startUpdate() {
  if (busy) {
    return { ok: false, message: '正在更新中' }
  }
  if (!app.isPackaged) {
    const message = '开发模式下请重新打包桌面安装包后再更新'
    emit({ state: 'error', message, currentVersion: app.getVersion() })
    return { ok: false, message }
  }
  busy = true
  try {
    let info = cache.info
    if (!info?.available) info = await checkForUpdate(true)
    if (!info?.available || !info.downloadUrl) {
      busy = false
      return info
    }

    const usePkg = process.platform === 'darwin' && /\.pkg$/i.test(info.assetName || info.downloadUrl || '')
    const win = getWindow()
    if (win && !win.isDestroyed()) {
      const sizeMb = info.size ? `约 ${Math.max(1, Math.round(info.size / 1024 / 1024))} MB，` : ''
      const { response } = await dialog.showMessageBox(win, {
        type: 'info',
        buttons: ['立即更新', '稍后'],
        defaultId: 0,
        cancelId: 1,
        title: '发现新版本',
        message: `eduAI ${info.latestVersion} 已发布`,
        detail: usePkg
          ? `${sizeMb}将下载 PKG 安装包。安装时请在系统弹窗中输入一次 Mac 登录密码，然后应用会自动重启。`
          : `${sizeMb}下载完成后将自动安装并重启应用。请保持网络畅通。`,
      })
      if (response !== 0) {
        busy = false
        emit({ state: 'available', ...info })
        return { ...info, cancelled: true }
      }
    }

    const ext = process.platform === 'win32' ? '.exe' : usePkg ? '.pkg' : '.dmg'
    const dest = path.join(os.tmpdir(), `eduAI-update-${info.latestVersion}${ext}`)
    emit({ state: 'downloading', percent: 0, ...info })
    await downloadFile(info.downloadUrl, dest, (percent) => {
      emit({ state: 'downloading', percent, ...info })
    })

    if (process.platform === 'darwin' && usePkg) {
      await installMacPkg(dest)
      emit({ state: 'installing', percent: 100, message: '安装完成，应用即将重启…', ...info })
      setQuitting(true)
      stopServer()
      relaunchMacAfterQuit()
    } else {
      emit({ state: 'installing', percent: 100, message: '正在安装，应用即将重启…', ...info })
      setQuitting(true)
      stopServer()
      if (process.platform === 'win32') {
        applyWindows(dest)
      } else if (process.platform === 'darwin') {
        await installMacDmg(dest)
      } else {
        throw new Error('当前系统暂不支持自动更新')
      }
    }

    setTimeout(() => app.quit(), 400)
    return { ok: true, installing: true, ...info }
  } catch (err) {
    busy = false
    const message = err instanceof Error ? err.message : String(err)
    emit({ state: 'error', message, currentVersion: app.getVersion() })
    return { ok: false, message }
  }
}

async function promptCheckOrUpdate() {
  const info = await checkForUpdate(true)
  const win = getWindow()
  if (info?.available) return startUpdate()
  const boxOpts = {
    title: '检查更新',
    message:
      info?.state === 'error'
        ? '暂时无法检查更新'
        : `当前已是最新版本 ${info?.currentVersion || app.getVersion()}`,
    detail: info?.state === 'error' ? info.message || '' : '',
    type: info?.state === 'error' ? 'error' : 'info',
  }
  if (win && !win.isDestroyed()) await dialog.showMessageBox(win, boxOpts)
  else await dialog.showMessageBox(boxOpts)
  return info
}

function setupUpdater(opts) {
  getWindow = opts.getWindow
  stopServer = opts.stopServer
  setQuitting = opts.setQuitting

  ipcMain.handle('get-version', () => app.getVersion())
  ipcMain.handle('check-for-update', () => checkForUpdate(false))
  ipcMain.handle('start-update', () => startUpdate())
  ipcMain.handle('open-release-page', () => {
    const url = cache.info?.htmlUrl || `https://github.com/${GH_OWNER}/${GH_REPO}/releases/latest`
    return shell.openExternal(url)
  })
}

module.exports = {
  setupUpdater,
  checkForUpdate,
  startUpdate,
  promptCheckOrUpdate,
  GH_OWNER,
  GH_REPO,
}
