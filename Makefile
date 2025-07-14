.PHONY: help install dev test clean docker-build docker-run lint format

help:		## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:	## 安装依赖
	pip install -r requirements.txt

dev:		## 启动开发服务器
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:		## 运行测试
	python -m pytest tests/ -v

clean:		## 清理临时文件
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f image_metadata.json

docker-build:	## 构建Docker镜像
	docker build -t rethinking-park-api .

docker-run:	## 运行Docker容器
	docker run -p 8000:8000 -v $(PWD)/.env:/app/.env -v $(PWD)/service-account-key.json:/app/service-account-key.json rethinking-park-api

lint:		## 代码风格检查
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

format:		## 格式化代码
	black . --line-length 88

setup-gcp:	## 设置Google Cloud项目的帮助信息
	@echo "请按照以下步骤设置Google Cloud:"
	@echo "1. 访问 https://console.cloud.google.com"
	@echo "2. 创建新项目或选择现有项目"
	@echo "3. 启用 Cloud Storage API 和 Cloud Vision API"
	@echo "4. 创建服务账号并下载密钥文件"
	@echo "5. 创建存储桶: gsutil mb gs://your-bucket-name"
	@echo "6. 复制 env.example 为 .env 并修改配置"

requirements:	## 生成requirements.txt
	pip freeze > requirements.txt 