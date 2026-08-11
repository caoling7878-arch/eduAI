#!/bin/bash
# 从 DMG 安装 eduAI：复制到「应用程序」并清除隔离属性，避免「已损坏，无法打开」
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/eduAI.app"
DEST="/Applications/eduAI.app"

if [[ ! -d "$SRC" ]]; then
  osascript -e 'display dialog "未找到 eduAI.app，请从安装盘根目录运行本脚本。\n\n若双击本文件被拦截：按住 Control 点击本文件 → 选择「打开」。" buttons {"好"} default button 1 with icon stop' >/dev/null
  exit 1
fi

osascript -e 'display notification "正在安装 eduAI…" with title "eduAI"' >/dev/null 2>&1 || true

# 若正在运行则先退出
osascript -e 'tell application "System Events" to if exists process "eduAI" then tell application "eduAI" to quit' >/dev/null 2>&1 || true
sleep 1

# 先清源包隔离标记，再 ditto 复制（比 cp -R 更适合 .app）
xattr -cr "$SRC" 2>/dev/null || true
rm -rf "$DEST"
ditto "$SRC" "$DEST"

# 清除从浏览器/网盘下载带来的隔离标记（否则会提示「已损坏」）
xattr -cr "$DEST" 2>/dev/null || true
# 去掉可能残留的 Gatekeeper 评估缓存痕迹
xattr -d com.apple.quarantine "$DEST" 2>/dev/null || true

# 无 Apple 开发者证书时做 ad-hoc 签名，避免签名损坏误判
codesign --force --deep --sign - "$DEST" 2>/dev/null || true

open "$DEST"
osascript -e 'display dialog "eduAI 已安装到「应用程序」并完成安全放行，正在启动。\n\n以后可直接从启动台打开。" buttons {"好"} default button 1' >/dev/null
