#!/usr/bin/env bash
# 启动后端服务（后台运行，日志写入 server.log）
set -e
cd "$(dirname "$0")/../backend"
pkill -f "port=5000" 2>/dev/null || true
sleep 1
setsid nohup venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from app import create_app
app = create_app()
app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
" > server.log 2>&1 < /dev/null &
sleep 4
curl -s --max-time 5 http://127.0.0.1:5000/api/health && echo " backend ok" || { echo "backend failed"; tail -20 server.log; exit 1; }
