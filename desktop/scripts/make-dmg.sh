#!/usr/bin/env bash
# 将已打包的 eduAI.app 做成「拖到 Applications」的 DMG
# 并附带一键安装脚本，清除下载隔离属性，避免「已损坏，无法打开」
set -euo pipefail

DESKTOP="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(node -p "require('$DESKTOP/package.json').version")"
ARCH="$(uname -m)"
case "$ARCH" in
  arm64) ARCH_TAG=arm64 ;;
  x86_64) ARCH_TAG=x64 ;;
  *) ARCH_TAG="$ARCH" ;;
esac

APP_DIR="$DESKTOP/dist/mac-${ARCH_TAG}"
if [[ ! -d "$APP_DIR/eduAI.app" ]]; then
  # electron-builder 偶尔输出到 dist/mac
  if [[ -d "$DESKTOP/dist/mac/eduAI.app" ]]; then
    APP_DIR="$DESKTOP/dist/mac"
  else
    echo "未找到 eduAI.app，请先执行 electron-builder --mac dir/zip"
    exit 1
  fi
fi

APP_SRC="$APP_DIR/eduAI.app"

echo "==> ad-hoc 签名 eduAI.app（无开发者证书时减少 Gatekeeper「已损坏」误判）"
codesign --force --deep --sign - "$APP_SRC"

STAGE="$(mktemp -d)/eduai-dmg"
mkdir -p "$STAGE"
cp -R "$APP_SRC" "$STAGE/eduAI.app"
# 复制后再次签名，避免 cp 破坏签名
codesign --force --deep --sign - "$STAGE/eduAI.app"
# 确保暂存包本身无隔离标记
xattr -cr "$STAGE/eduAI.app" 2>/dev/null || true

ln -s /Applications "$STAGE/Applications"

INSTALL_CMD="$STAGE/安装 eduAI.command"
cp "$DESKTOP/scripts/Install eduAI.command" "$INSTALL_CMD"
chmod +x "$INSTALL_CMD"

cat > "$STAGE/安装说明.txt" <<'EOF'
【推荐】双击「安装 eduAI.command」完成安装
会自动复制到「应用程序」并清除 macOS 下载隔离标记，避免提示「已损坏，无法打开」。
首次运行若弹出安全提示，在对话框中点「打开」即可。

【也可】将 eduAI 拖入「应用程序」(Applications)
若随后提示「已损坏，无法打开」，请打开「终端」执行：

  xattr -cr /Applications/eduAI.app

然后再从启动台打开 eduAI。
EOF

OUT="$DESKTOP/dist/eduAI-${VERSION}-${ARCH_TAG}.dmg"
rm -f "$OUT"
hdiutil create -volname "eduAI 安装" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "✓ DMG: $OUT"
ls -lh "$OUT"
