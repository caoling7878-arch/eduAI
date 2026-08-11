#!/usr/bin/env bash
# 将已打包的 eduAI.app 做成安装盘：
# 1) DMG：内含「① 双击安装.command」（推荐）+ 应用本体
# 2) PKG：双击用系统安装器安装，postinstall 自动清除隔离属性
# 不提供 Applications 拖拽快捷方式，避免用户拖装后出现「已损坏」
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
  if [[ -d "$DESKTOP/dist/mac/eduAI.app" ]]; then
    APP_DIR="$DESKTOP/dist/mac"
  else
    echo "未找到 eduAI.app，请先执行 electron-builder --mac dir/zip"
    exit 1
  fi
fi

APP_SRC="$APP_DIR/eduAI.app"

echo "==> ad-hoc 签名 eduAI.app（无开发者证书时的本地签名）"
codesign --force --deep --sign - "$APP_SRC"
xattr -cr "$APP_SRC" 2>/dev/null || true

STAGE="$(mktemp -d)/eduai-dmg"
mkdir -p "$STAGE"
ditto "$APP_SRC" "$STAGE/eduAI.app"
codesign --force --deep --sign - "$STAGE/eduAI.app"
xattr -cr "$STAGE/eduAI.app" 2>/dev/null || true

# 文件名靠前，引导用户先点安装脚本（不要拖拽 .app）
INSTALL_CMD="$STAGE/① 双击安装 eduAI.command"
cp "$DESKTOP/scripts/Install eduAI.command" "$INSTALL_CMD"
chmod +x "$INSTALL_CMD"

cat > "$STAGE/请先读我-安装说明.txt" <<'EOF'
════════════════════════════════════
  macOS 安装 eduAI（必读）
════════════════════════════════════

【推荐】双击「① 双击安装 eduAI.command」
  · 会自动装到「应用程序」并清除下载隔离标记
  · 若系统拦截脚本：按住 Control 点击该文件 →「打开」→ 再点「打开」

【不要】把 eduAI.app 直接拖进「应用程序」
  · 从 GitHub / 浏览器下载的未公证应用，拖装后常会提示
    「eduAI」已损坏，无法打开 —— 这是 Gatekeeper 隔离，不是真损坏

【若已拖装并提示已损坏】打开「终端」执行：

  xattr -cr /Applications/eduAI.app

然后从启动台重新打开 eduAI。

也可使用同目录旁发布的 .pkg 安装包（系统安装器 + 自动放行）。
EOF

OUT_DMG="$DESKTOP/dist/eduAI-${VERSION}-${ARCH_TAG}.dmg"
rm -f "$OUT_DMG"
hdiutil create -volname "eduAI 安装" -srcfolder "$STAGE" -ov -format UDZO "$OUT_DMG"
echo "✓ DMG: $OUT_DMG"
ls -lh "$OUT_DMG"

# ---- 额外生成 PKG（双击安装，postinstall 清隔离）----
echo "==> 生成 PKG 安装包"
PKG_ROOT="$(mktemp -d)/pkgroot"
PKG_SCRIPTS="$(mktemp -d)/pkgscripts"
mkdir -p "$PKG_ROOT" "$PKG_SCRIPTS"
ditto "$APP_SRC" "$PKG_ROOT/eduAI.app"
cp "$DESKTOP/scripts/pkg-scripts/postinstall" "$PKG_SCRIPTS/postinstall"
chmod 755 "$PKG_SCRIPTS/postinstall"

OUT_PKG="$DESKTOP/dist/eduAI-${VERSION}-${ARCH_TAG}.pkg"
rm -f "$OUT_PKG"
pkgbuild \
  --root "$PKG_ROOT" \
  --install-location /Applications \
  --scripts "$PKG_SCRIPTS" \
  --identifier ai.edu.desktop \
  --version "$VERSION" \
  --ownership recommended \
  "$OUT_PKG"
echo "✓ PKG: $OUT_PKG"
ls -lh "$OUT_PKG"

rm -rf "$STAGE" "$PKG_ROOT" "$PKG_SCRIPTS" 2>/dev/null || true
