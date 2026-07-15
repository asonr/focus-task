#!/bin/bash

# Focus Task 启动脚本
# 用法: ./start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PID_FILE="$SCRIPT_DIR/.dev-pids"
BACKEND_PORT="${FOCUS_TASK_BACKEND_PORT:-8765}"

PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

# 绕过本地代理（系统代理会拦截 localhost 请求导致健康检查失败）
export NO_PROXY="localhost,127.0.0.1"
export no_proxy="localhost,127.0.0.1"
export FOCUS_TASK_RUN_LEGACY_MIGRATION="${FOCUS_TASK_RUN_LEGACY_MIGRATION:-0}"

# 颜色
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'

cleanup() {
  echo ""
  echo -e "${YELLOW}正在停止服务...${NC}"
  if [ -f "$PID_FILE" ]; then
    while read -r pid; do
      kill "$pid" 2>/dev/null && echo "  已停止进程 $pid"
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  echo -e "${GREEN}服务已停止${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

if [ -f "$PID_FILE" ]; then
  while read -r pid; do
    kill "$pid" 2>/dev/null && echo "  已清理上次启动残留进程 $pid"
  done < "$PID_FILE"
  rm -f "$PID_FILE"
fi

if lsof -ti:"$BACKEND_PORT" >/dev/null 2>&1; then
  echo -e "${YELLOW}端口 $BACKEND_PORT 已被占用，请先停止对应服务后再启动。${NC}"
  exit 1
fi

if lsof -ti:1420 >/dev/null 2>&1; then
  echo -e "${YELLOW}端口 1420 已被占用，请先停止对应服务后再启动。${NC}"
  exit 1
fi

sleep 1

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Focus Task 启动中...${NC}"
echo -e "${GREEN}========================================${NC}"

# ─── 后端 ───
echo -e "${BLUE}🔧 启动后端 (http://127.0.0.1:$BACKEND_PORT)...${NC}"
cd "$BACKEND_DIR"
[ -f "todo.db" ] || echo "  (首次运行，将自动创建数据库)"
if [ "$FOCUS_TASK_RUN_LEGACY_MIGRATION" = "1" ]; then
  echo "  执行一次性旧库迁移..."
  "$PYTHON_BIN" run_legacy_migration.py >> "$SCRIPT_DIR/backend.log" 2>&1 || {
    echo -e "${YELLOW}   ⚠ 旧库迁移失败，请查看 backend.log${NC}"
    exit 1
  }
fi
"$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" >> "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" >> "$PID_FILE"
echo -e "${BLUE}   后端 PID: $BACKEND_PID${NC}"

# 等后端就绪
for i in $(seq 1 15); do
  sleep 1
  if curl -s "http://127.0.0.1:$BACKEND_PORT/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 后端已就绪${NC}"
    break
  fi
  [ $i -eq 15 ] && echo -e "${YELLOW}   ⚠ 后端可能启动失败，请查看 backend.log${NC}"
done

# ─── 前端 ───
echo -e "${BLUE}🎨 启动前端 (http://localhost:1420)...${NC}"
cd "$FRONTEND_DIR"
"$FRONTEND_DIR/node_modules/.bin/vite" --host --port 1420 >> "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"
echo -e "${BLUE}   前端 PID: $FRONTEND_PID${NC}"

# 等前端就绪
for i in $(seq 1 10); do
  sleep 1
  if curl -s http://localhost:1420/ > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 前端已就绪${NC}"
    break
  fi
  [ $i -eq 10 ] && echo -e "${YELLOW}   ⚠ 前端可能启动失败，请查看 frontend.log${NC}"
done

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || echo '未检测到')"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   服务已启动！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "  后端:  ${BLUE}http://127.0.0.1:$BACKEND_PORT${NC}"
echo -e "  前端:  ${BLUE}http://localhost:1420${NC}"
echo -e "  局域网: ${BLUE}http://$LAN_IP:1420${NC}"
echo -e "  日志:  $SCRIPT_DIR/backend.log / frontend.log"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

wait
