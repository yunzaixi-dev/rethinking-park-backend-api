#!/bin/bash

# Docker Compose 本地测试脚本

set -e

echo "🚀 开始Docker本地测试..."

# 检查必要文件
if [ ! -f "service-account-key.json" ]; then
    echo "❌ 缺少 service-account-key.json 文件"
    echo "请将Google Cloud服务账号密钥文件复制到当前目录"
    exit 1
fi

# 停止并清理现有容器
echo "🧹 清理现有容器..."
docker-compose down -v 2>/dev/null || true

# 构建并启动服务
echo "🏗️ 构建并启动服务..."
docker-compose up --build -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 检查Redis连接
echo "📊 检查Redis连接..."
if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis连接正常"
else
    echo "❌ Redis连接失败"
fi

# 检查API健康状态
echo "🏥 检查API健康状态..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ API服务健康检查通过"
        break
    else
        echo "⏳ 尝试 $attempt/$max_attempts - 等待API服务启动..."
        sleep 2
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ API服务启动超时"
    echo "📋 查看API日志:"
    docker-compose logs api
    exit 1
fi

# 测试API端点
echo "🧪 测试API端点..."

# 测试根端点
echo "🏠 测试根端点..."
if curl -s http://localhost:8000/ | grep -q "Rethinking Park Backend API"; then
    echo "✅ 根端点正常"
else
    echo "❌ 根端点测试失败"
fi

# 测试健康检查
echo "🏥 测试健康检查端点..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ 健康检查端点正常"
else
    echo "❌ 健康检查端点测试失败"
fi

# 测试统计信息
echo "📊 测试统计信息端点..."
if curl -s http://localhost:8000/api/v1/stats | grep -q "storage"; then
    echo "✅ 统计信息端点正常"
else
    echo "❌ 统计信息端点测试失败"
fi

# 查看服务日志
echo "📋 最近的服务日志:"
echo "--- Redis 日志 ---"
docker-compose logs --tail=10 redis
echo "--- API 日志 ---"
docker-compose logs --tail=20 api

echo ""
echo "🎉 Docker测试完成！"
echo "📖 API文档: http://localhost:8000/docs"
echo "🏥 健康检查: http://localhost:8000/health"
echo "📊 统计信息: http://localhost:8000/api/v1/stats"
echo ""
echo "🛑 停止服务: docker-compose down"
echo "🧹 清理数据: docker-compose down -v"