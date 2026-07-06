#!/bin/bash
# SNMP MIB → Zabbix Template Tool 一键启动脚本
# 同时启动后端(FastAPI)和前端(Vite Dev Server)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo " SNMP MIB → Zabbix 6.4 模板生成工具"
echo "=========================================="

# 1. 启动后端
echo ""
echo "[1/2] 启动后端 (FastAPI)..."
cd "$SCRIPT_DIR/backend"

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python 3.9+"
    exit 1
fi

# 安装依赖(如需要)
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -r requirements.txt -q

# 启动后端服务 (后台运行)
echo "启动 FastAPI 服务 (端口 8000)..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 2. 启动前端
echo ""
echo "[2/2] 启动前端 (Vite)..."
cd "$SCRIPT_DIR/frontend"

# 安装依赖(如需要)
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

echo "启动 Vite Dev Server (端口 5173)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo " 启动完成!"
echo " 前端地址: http://localhost:5173"
echo " 后端API:  http://localhost:8000"
echo " API文档:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待子进程
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
