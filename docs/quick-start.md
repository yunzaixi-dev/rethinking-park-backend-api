# 快速开始指南

本指南将帮助你在 **5 分钟内** 运行 Rethinking Park Backend API。

## 🚀 自动化安装（推荐）

### 适用于 Arch Linux 系统

```bash
cd rethinkingpark-backend-v2
./setup.sh
```

这个脚本会自动：
- 安装系统依赖
- 设置 Python 虚拟环境
- 安装项目依赖
- 配置环境变量模板
- 创建便利脚本
- 测试 Google Cloud 配置

---

## 🛠️ 手动安装

### 步骤 1: 安装依赖

#### Arch Linux:
```bash
# 使用 yay 安装
yay -S python python-pip python-venv

# 可选：安装 Google Cloud CLI
yay -S google-cloud-cli
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 可选：安装 Google Cloud CLI
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh
```

#### macOS:
```bash
# 使用 Homebrew
brew install python

# 可选：安装 Google Cloud CLI
brew install google-cloud-sdk
```

### 步骤 2: 设置 Python 环境

```bash
cd rethinkingpark-backend-v2

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 步骤 3: 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑配置文件
nano .env  # 或使用你喜欢的编辑器
```

填入以下信息：
```env
GOOGLE_CLOUD_PROJECT_ID=你的项目ID
GOOGLE_CLOUD_STORAGE_BUCKET=你的存储桶名称
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

### 步骤 4: 配置 Google Cloud

> 📖 **详细教程**: 参考 [Google Cloud 配置教程](google-cloud-setup.md)

**简化步骤**：
1. 访问 [Google Cloud Console](https://console.cloud.google.com)
2. 创建项目并启用 Cloud Storage + Vision API
3. 创建服务账号并下载密钥文件
4. 将密钥文件重命名为 `service-account-key.json` 并放在项目根目录

### 步骤 5: 测试配置

```bash
# 测试 Google Cloud 连接
python test_gcp.py

# 如果测试通过，启动服务
python main.py
```

---

## ✅ 验证安装

### 1. 健康检查
```bash
curl http://localhost:8000/health
```

### 2. 查看 API 文档
浏览器访问: http://localhost:8000/docs

### 3. 测试图像上传
```bash
# 下载测试图片
wget https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Victoria_Park_Bedford.jpg/640px-Victoria_Park_Bedford.jpg -O test_park.jpg

# 使用测试客户端
python utils/test_client.py test_park.jpg
```

---

## 🎯 常用命令

### 启动服务
```bash
# 开发模式（自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
python main.py

# 使用便利脚本（如果运行了 setup.sh）
./start.sh
```

### 测试 API
```bash
# 基本健康检查
./test.sh

# 测试图像上传和分析
./test.sh path/to/your/image.jpg

# 使用 curl
curl -X POST "http://localhost:8000/api/v1/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_park.jpg"
```

### Docker 运行
```bash
# 构建镜像
docker build -t rethinking-park-api .

# 运行容器
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/service-account-key.json:/app/service-account-key.json:ro \
  rethinking-park-api

# 或使用 docker-compose
docker-compose up
```

---

## 🐛 常见问题

### Q: "Could not automatically determine credentials" 错误
**解决**: 确保 `service-account-key.json` 文件在正确位置，并且 `.env` 中的路径正确。

### Q: "存储桶不存在" 错误
**解决**: 检查存储桶名称是否正确，或者在 Google Cloud Console 中创建存储桶。

### Q: Vision API 配额错误
**解决**: 检查 Google Cloud 项目是否启用了计费，或者等待配额重置。

### Q: 端口被占用
**解决**: 
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
uvicorn main:app --port 8001
```

---

## 🔧 开发工具

### 代码格式化
```bash
# 安装开发依赖
pip install black flake8

# 格式化代码
black .

# 检查代码风格
flake8 .
```

### 使用 Makefile
```bash
# 查看所有可用命令
make help

# 安装依赖
make install

# 启动开发服务器
make dev

# 构建 Docker 镜像
make docker-build
```

---

## 📚 下一步

1. **阅读完整文档**: [README.md](../README.md)
2. **配置 Google Cloud**: [google-cloud-setup.md](google-cloud-setup.md)
3. **查看 API 文档**: http://localhost:8000/docs
4. **集成到前端**: 参考 API 端点文档

---

## 🆘 获取帮助

- **项目文档**: [README.md](../README.md)
- **配置教程**: [google-cloud-setup.md](google-cloud-setup.md)
- **测试脚本**: `python test_gcp.py`
- **社区支持**: GitHub Issues, Stack Overflow

---

🎉 **恭喜！** 你的 Rethinking Park Backend API 现在已经运行起来了！ 