#!/usr/bin/env bash
# eduAI 一键启动：API(:8000) + 学员端(:5173) + 管理端(:5174)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT/.run"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

API_PORT=8000
WEB_PORT=5173
ADMIN_PORT=5174

usage() {
  cat <<'EOF'
用法:
  ./start.sh              启动 API + 学员端 + 管理端
  ./start.sh --install    启动前安装依赖（pip / npm）
  ./start.sh stop         停止全部服务
  ./start.sh status       查看运行状态
  ./start.sh restart      重启全部服务

服务地址:
  学员端   http://127.0.0.1:5173/
  管理端   http://127.0.0.1:5174/
  API文档  http://127.0.0.1:8000/docs
EOF
}

is_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

pid_of_port() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -n1 || true
}

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 0.4
    pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
  fi
}

install_deps() {
  echo "→ 安装 API 依赖…"
  python3 -m pip install -q -r "$ROOT/apps/api/requirements.txt"
  echo "→ 安装学员端依赖…"
  npm install --prefix "$ROOT/apps/web"
  echo "→ 安装管理端依赖…"
  npm install --prefix "$ROOT/apps/admin"
}

start_one() {
  local name="$1"
  local port="$2"
  local pidfile="$RUN_DIR/$name.pid"
  local logfile="$LOG_DIR/$name.log"
  shift 2

  if is_listening "$port"; then
    echo "· $name 已在 :$port 运行 (pid $(pid_of_port "$port"))"
    return 0
  fi

  echo "→ 启动 $name (:$port)…"
  (
    cd "$ROOT"
    nohup "$@" >"$logfile" 2>&1 &
    echo $! >"$pidfile"
  )
}

wait_ready() {
  local name="$1"
  local port="$2"
  local url="$3"
  local i
  for i in $(seq 1 40); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "✓ $name 就绪  $url"
      return 0
    fi
    sleep 0.35
  done
  echo "✗ $name 启动超时（:$port），日志: $LOG_DIR/$name.log"
  return 1
}

do_start() {
  local do_install="${1:-0}"
  if [[ "$do_install" == "1" ]]; then
    install_deps
  fi

  if [[ ! -d "$ROOT/apps/web/node_modules" || ! -d "$ROOT/apps/admin/node_modules" ]]; then
    echo "提示: 未检测到 node_modules，自动执行依赖安装…"
    install_deps
  fi

  start_one api "$API_PORT" \
    python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT" --app-dir apps/api

  start_one web "$WEB_PORT" \
    npm run dev --prefix apps/web -- --host 127.0.0.1 --port "$WEB_PORT"

  start_one admin "$ADMIN_PORT" \
    npm run dev --prefix apps/admin -- --host 127.0.0.1 --port "$ADMIN_PORT"

  echo
  wait_ready api "$API_PORT" "http://127.0.0.1:$API_PORT/api/v1/health" || true
  wait_ready web "$WEB_PORT" "http://127.0.0.1:$WEB_PORT/" || true
  wait_ready admin "$ADMIN_PORT" "http://127.0.0.1:$ADMIN_PORT/" || true

  cat <<EOF

eduAI 已启动
  学员端   http://127.0.0.1:$WEB_PORT/
  管理端   http://127.0.0.1:$ADMIN_PORT/
  API文档  http://127.0.0.1:$API_PORT/docs

账号: admin@edu.ai / admin123 · teacher@edu.ai / teacher123 · student@edu.ai / student123
日志: $LOG_DIR/
停止: ./start.sh stop
EOF
}

do_stop() {
  echo "→ 停止服务…"
  kill_port "$ADMIN_PORT"
  kill_port "$WEB_PORT"
  kill_port "$API_PORT"
  rm -f "$RUN_DIR"/*.pid 2>/dev/null || true
  echo "✓ 已停止"
}

do_status() {
  for item in "api:$API_PORT" "web:$WEB_PORT" "admin:$ADMIN_PORT"; do
    local name="${item%%:*}"
    local port="${item##*:}"
    if is_listening "$port"; then
      echo "✓ $name  :$port  pid=$(pid_of_port "$port")"
    else
      echo "· $name  :$port  未运行"
    fi
  done
}

cmd="${1:-start}"
case "$cmd" in
  -h|--help|help) usage ;;
  --install) do_start 1 ;;
  start) do_start 0 ;;
  stop) do_stop ;;
  status) do_status ;;
  restart) do_stop; sleep 0.5; do_start 0 ;;
  *)
    echo "未知命令: $cmd"
    usage
    exit 1
    ;;
esac
