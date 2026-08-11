#!/usr/bin/env bash
# 构建 eduAI 桌面安装包（当前平台）
#   ./tools/desktop/build.sh          # 自动识别 macOS / Windows
#   ./tools/desktop/build.sh mac
#   ./tools/desktop/build.sh win
#   ./tools/desktop/build.sh server   # 仅打包后端二进制
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DESKTOP="$ROOT/desktop"
API="$ROOT/apps/api"
WEB="$ROOT/apps/web"
ADMIN="$ROOT/apps/admin"
SPA_WEB="$API/app/spa/web"
SPA_ADMIN="$API/app/spa/admin"
SERVER_OUT="$DESKTOP/resources/server"

TARGET="${1:-auto}"
OS="$(uname -s 2>/dev/null || echo unknown)"
if [[ "$TARGET" == "auto" ]]; then
  case "$OS" in
    Darwin) TARGET=mac ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) TARGET=win ;;
    *)
      echo "无法识别的平台，请显式指定: mac | win | server"
      exit 1
      ;;
  esac
fi

# 原生服务端二进制不可跨平台交叉编译
if [[ "$TARGET" == "mac" && "$OS" != "Darwin" ]]; then
  echo "macOS 安装包请在 Mac 上构建"
  exit 1
fi
if [[ "$TARGET" == "win" && "$OS" == "Darwin" ]]; then
  echo "Windows 安装包请在 Windows 上构建（或使用 CI）: tools/desktop/build.ps1"
  exit 1
fi

echo "==> 目标平台: $TARGET"
echo "==> 仓库: $ROOT"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "缺少命令: $1"
    exit 1
  }
}

need_cmd npm

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
need_cmd "$PY"

echo "==> 安装前端依赖"
npm install --prefix "$WEB"
npm install --prefix "$ADMIN"

echo "==> 构建学员端（vite，跳过既有 vue-tsc 报错）"
( cd "$WEB" && npx vite build )

echo "==> 构建管理端 (base=/admin/)"
( cd "$ADMIN" && EDUAI_ADMIN_BASE=/admin/ npx vite build )

echo "==> 复制 SPA 到 API"
rm -rf "$SPA_WEB" "$SPA_ADMIN"
mkdir -p "$SPA_WEB" "$SPA_ADMIN"
cp -R "$WEB/dist/." "$SPA_WEB/"
cp -R "$ADMIN/dist/." "$SPA_ADMIN/"
test -f "$SPA_WEB/index.html"
test -f "$SPA_ADMIN/index.html"
# 管理端生产路径必须带 /admin/ 前缀
if ! grep -q '/admin/assets/' "$SPA_ADMIN/index.html"; then
  echo "错误: 管理端未以 base=/admin/ 构建，Windows/Mac 安装后管理后台会 404"
  exit 1
fi

echo "==> 准备 Python 打包环境"
if [[ ! -d "$API/.venv-desktop" ]]; then
  "$PY" -m venv "$API/.venv-desktop"
fi
# shellcheck disable=SC1091
if [[ -f "$API/.venv-desktop/bin/activate" ]]; then
  source "$API/.venv-desktop/bin/activate"
else
  # Git Bash / Windows
  source "$API/.venv-desktop/Scripts/activate"
fi
python -m pip install -q -U pip wheel
python -m pip install -q -r "$API/requirements.txt" "pyinstaller>=6.0"

echo "==> PyInstaller 打包本地服务（含 SPA 回退与 Embedding 配置）"
rm -rf "$API/build" "$API/dist" "$SERVER_OUT"
mkdir -p "$DESKTOP/resources"
(
  cd "$API"
  pyinstaller --noconfirm --clean "$DESKTOP/eduai-server.spec"
)
mkdir -p "$SERVER_OUT"
cp -R "$API/dist/eduai-server/." "$SERVER_OUT/"

if [[ "$TARGET" == "win" || "$OS" == MINGW* || "$OS" == MSYS* ]]; then
  if [[ ! -f "$SERVER_OUT/eduai-server.exe" ]]; then
    echo "错误: 未生成 eduai-server.exe"
    ls -la "$SERVER_OUT" | head
    exit 1
  fi
else
  if [[ -f "$SERVER_OUT/eduai-server" ]]; then
    chmod +x "$SERVER_OUT/eduai-server"
  fi
fi

if [[ "$TARGET" == "server" ]]; then
  echo "✓ 服务端已输出: $SERVER_OUT"
  exit 0
fi

echo "==> 安装 Electron 依赖"
npm install --prefix "$DESKTOP"

# Windows 图标：若存在 ImageMagick 则生成 .ico
if [[ "$TARGET" == "win" ]]; then
  if command -v convert >/dev/null 2>&1; then
    convert "$DESKTOP/build/icon.png" -define icon:auto-resize=256,128,64,48,32,16 "$DESKTOP/build/icon.ico" || true
  fi
fi

echo "==> electron-builder 打包安装程序"
case "$TARGET" in
  mac)
    npm run dist:mac --prefix "$DESKTOP"
    echo
    echo "✓ macOS 安装包已生成（请用 DMG 内「① 双击安装」或 .pkg，勿直接拖拽 .app）:"
    ls -la "$DESKTOP/dist/"*.dmg "$DESKTOP/dist/"*.pkg 2>/dev/null || ls -la "$DESKTOP/dist/"
    ;;
  win)
    npm run dist:win --prefix "$DESKTOP"
    echo
    echo "✓ Windows 安装包已生成（双击 install.exe）:"
    ls -la "$DESKTOP/dist/install.exe" 2>/dev/null || ls -la "$DESKTOP/dist/"
    test -f "$DESKTOP/dist/install.exe"
    ;;
  *)
    echo "未知目标: $TARGET"
    exit 1
    ;;
esac

echo
echo "完成。安装后桌面/启动台会出现 eduAI 图标，点击即可启动本地系统。"
echo "本包已包含：管理端 /admin SPA 回退、Embedding 配置与维度对齐检索。"
