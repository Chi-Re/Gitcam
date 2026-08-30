#!/usr/bin/env bash
# 一键启动：基础设施(Docker) + 后端 + 前端
set -e
cd "$(dirname "$0")/.."

echo "==> 1/3 启动基础设施（MySQL + MinIO）"
docker-compose up -d
sleep 5

echo "==> 2/3 启动后端 Flask API (:5000)"
bash scripts/start_backend.sh

echo "==> 3/3 启动前端 Vite Dev Server (:5173)"
cd frontend
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
setsid nohup npm run dev > dev.log 2>&1 < /dev/null &
sleep 6
curl -s --max-time 5 http://127.0.0.1:5173/ -o /dev/null && echo "前端就绪: http://127.0.0.1:5173" || { echo "前端启动失败"; tail -20 dev.log; exit 1; }

echo ""
echo "全部就绪："
echo "  前端: http://127.0.0.1:5173"
echo "  后端: http://127.0.0.1:5000"
echo "  MinIO 控制台: http://127.0.0.1:9001 (gitcam_minio / gitcam_minio_dev)"
echo "  默认管理员: admin / admin123（生产环境请修改）"
