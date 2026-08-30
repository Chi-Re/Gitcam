#!/usr/bin/env bash
# 一键生产部署：构建镜像并启动完整栈（web/backend/mysql/minio）
# 注意：prod 编排位于 deploy/ 独立目录，避免与根目录开发 compose 合并导致误删
set -e
cd "$(dirname "$0")/.."

COMPOSE_DIR=deploy
COMPOSE_FILE=docker-compose.prod.yml
PORT=${PORT:-8080}

echo "==> 构建并启动容器栈（对外端口 ${PORT}）"
docker-compose -f "$COMPOSE_DIR/$COMPOSE_FILE" up -d --build

echo "==> 等待服务就绪"
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "   后端健康检查通过 ✓"
    break
  fi
  if [ "$i" = 60 ]; then
    echo "   等待超时，请查看日志：docker-compose -f $COMPOSE_DIR/$COMPOSE_FILE logs backend"
    exit 1
  fi
  sleep 2
done

echo ""
echo "部署完成："
echo "  访问地址:  http://127.0.0.1:${PORT}"
echo "  后端直连:  http://127.0.0.1:18000"
echo "  MinIO 控制台: http://127.0.0.1:9003"
echo ""
echo "查看状态: docker-compose -f $COMPOSE_DIR/$COMPOSE_FILE ps"
echo "查看日志: docker-compose -f $COMPOSE_DIR/$COMPOSE_FILE logs -f"
echo "停止服务: docker-compose -f $COMPOSE_DIR/$COMPOSE_FILE down"
echo "数据持久化于 Docker volumes（mysql_prod_data/minio_prod_data/repos_prod_data/uploads_prod_data）"
