#!/usr/bin/env bash
# 将已打包的 eduAI.app 做成「拖到 Applications」的 DMG
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

STAGE="$(mktemp -d)/eduai-dmg"
mkdir -p "$STAGE"
cp -R "$APP_DIR/eduAI.app" "$STAGE/eduAI.app"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/安装说明.txt" <<'EOF'
将 eduAI 拖入「应用程序」(Applications) 即可完成安装。
安装后可在启动台点击 eduAI 图标启动本地系统。
若提示无法打开，请到「系统设置 → 隐私与安全性」允许运行。
EOF

OUT="$DESKTOP/dist/eduAI-${VERSION}-${ARCH_TAG}.dmg"
rm -f "$OUT"
hdiutil create -volname "eduAI 安装" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
echo "✓ DMG: $OUT"
ls -lh "$OUT"
