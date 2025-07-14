# Google Cloud 配置教程

本教程将详细指导你如何配置Google Cloud Platform (GCP)环境，以便在Rethinking Park Backend API中使用Cloud Storage和Vision API服务。

## 📋 目录
1. [创建Google Cloud项目](#1-创建google-cloud项目)
2. [启用必要的API](#2-启用必要的api)
3. [创建服务账号](#3-创建服务账号)
4. [创建存储桶](#4-创建存储桶)
5. [配置环境变量](#5-配置环境变量)
6. [验证配置](#6-验证配置)
7. [常见问题](#7-常见问题)

---

## 1. 创建Google Cloud项目

### 步骤1.1: 访问Google Cloud Console
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 使用你的Google账号登录
3. 如果是首次使用，需要接受服务条款

### 步骤1.2: 创建新项目
1. 点击页面顶部的项目选择器（项目名称旁的下拉箭头）
2. 在弹出的对话框中点击 "新建项目"
3. 填写项目信息：
   - **项目名称**: `rethinking-park-api` (或你喜欢的名称)
   - **项目ID**: 系统会自动生成，你也可以自定义（注意：项目ID全球唯一且创建后无法修改）
   - **位置**: 选择组织（如果有）或"无组织"
4. 点击"创建"

### 步骤1.3: 记录项目信息
创建完成后，记录以下信息：
- **项目ID**: 例如 `rethinking-park-api-123456`
- **项目编号**: 例如 `123456789012`

> ⚠️ **重要**: 项目ID将用于环境变量配置

---

## 2. 启用必要的API

### 步骤2.1: 启用Cloud Storage API
1. 在Cloud Console中，确保选择了正确的项目
2. 进入 "API和服务" > "库"
3. 搜索 "Cloud Storage API"
4. 点击搜索结果中的 "Cloud Storage API"
5. 点击"启用"按钮

### 步骤2.2: 启用Cloud Vision API
1. 继续在"API和服务" > "库"页面
2. 搜索 "Cloud Vision API"
3. 点击搜索结果中的 "Vision API"
4. 点击"启用"按钮

### 步骤2.3: 验证API启用状态
1. 进入 "API和服务" > "已启用的API和服务"
2. 确认看到以下API：
   - Cloud Storage API
   - Cloud Vision API

---

## 3. 创建服务账号

### 步骤3.1: 创建服务账号
1. 进入 "IAM和管理" > "服务账号"
2. 点击 "创建服务账号"
3. 填写服务账号详情：
   - **服务账号名称**: `rethinking-park-service`
   - **服务账号ID**: 系统自动生成 `rethinking-park-service@your-project-id.iam.gserviceaccount.com`
   - **描述**: `Rethinking Park API服务账号`
4. 点击"创建并继续"

### 步骤3.2: 分配角色权限
为服务账号分配必要的角色：

1. **Storage Admin角色**：
   - 在"向此服务账号授予对项目的访问权限"部分
   - 点击"选择角色"下拉菜单
   - 搜索并选择 "Storage Admin"
   - 点击"添加其他角色"

2. **Cloud Vision API User角色**：
   - 继续在角色选择中
   - 搜索并选择 "ML Engine Developer" 或 "AI Platform Developer"
   - 如果找不到，可以选择 "Editor"（权限较大）

3. 点击"继续"，然后点击"完成"

### 步骤3.3: 创建密钥文件
1. 在服务账号列表中，找到刚创建的服务账号
2. 点击服务账号的邮箱地址
3. 切换到"密钥"标签页
4. 点击"添加密钥" > "创建新密钥"
5. 选择密钥类型为"JSON"
6. 点击"创建"
7. JSON密钥文件会自动下载到你的电脑

### 步骤3.4: 保存密钥文件
1. 将下载的JSON文件重命名为 `service-account-key.json`
2. 将文件移动到项目根目录：
   ```
   rethinkingpark-backend-v2/
   ├── service-account-key.json  ← 放在这里
   ├── main.py
   └── ...
   ```

> ⚠️ **安全提示**: 
> - 不要将密钥文件提交到版本控制系统
> - 确保密钥文件权限设置正确（仅当前用户可读）

---

## 4. 创建存储桶

### 步骤4.1: 通过Cloud Console创建
1. 进入 "Cloud Storage" > "存储桶"
2. 点击"创建存储桶"
3. 配置存储桶：
   - **名称**: `rethinking-park-images-唯一标识` (例如: `rethinking-park-images-20241201`)
   - **位置类型**: 选择"Region"
   - **位置**: 选择离你最近的地区（例如：`asia-east1`）
   - **存储类别**: "Standard"
   - **访问控制**: "统一"
   - **保护工具**: 可选择启用版本控制
4. 点击"创建"

### 步骤4.2: 通过命令行创建（可选）
如果你已安装Google Cloud CLI：
```bash
# 安装gcloud CLI（如果尚未安装）
# 在Arch Linux上：
yay -S google-cloud-cli

# 登录
gcloud auth login

# 设置项目
gcloud config set project YOUR_PROJECT_ID

# 创建存储桶
gsutil mb -l asia-east1 gs://rethinking-park-images-your-unique-id
```

### 步骤4.3: 设置存储桶权限（可选）
如果需要公开访问：
```bash
# 设置存储桶为公开可读
gsutil iam ch allUsers:objectViewer gs://your-bucket-name
```

---

## 5. 配置环境变量

### 步骤5.1: 复制环境变量模板
```bash
cd rethinkingpark-backend-v2
cp env.example .env
```

### 步骤5.2: 编辑.env文件
使用你喜欢的编辑器打开`.env`文件：
```bash
nano .env
# 或
vim .env
# 或
code .env
```

### 步骤5.3: 填写配置信息
根据前面步骤获得的信息，修改`.env`文件：

```env
# Google Cloud 配置
GOOGLE_CLOUD_PROJECT_ID=rethinking-park-api-123456
GOOGLE_CLOUD_STORAGE_BUCKET=rethinking-park-images-20241201
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# 应用配置
DEBUG=True
APP_NAME=Rethinking Park Backend API
APP_VERSION=1.0.0

# API配置 
API_V1_STR=/api/v1

# CORS配置（多个域名用逗号分隔）
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend-domain.com
```

### 步骤5.4: 配置说明

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `GOOGLE_CLOUD_PROJECT_ID` | 你的GCP项目ID | `rethinking-park-api-123456` |
| `GOOGLE_CLOUD_STORAGE_BUCKET` | 存储桶名称 | `rethinking-park-images-20241201` |
| `GOOGLE_APPLICATION_CREDENTIALS` | 服务账号密钥文件路径 | `./service-account-key.json` |
| `DEBUG` | 是否启用调试模式 | `True` 或 `False` |
| `ALLOWED_ORIGINS` | 允许的跨域来源 | 前端应用的URL |

---

## 6. 验证配置

### 步骤6.1: 安装项目依赖
```bash
cd rethinkingpark-backend-v2
pip install -r requirements.txt
```

### 步骤6.2: 测试Google Cloud连接
创建一个简单的测试脚本：

```bash
# 创建测试文件
cat > test_gcp.py << 'EOF'
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import vision

# 加载环境变量
load_dotenv()

def test_storage():
    """测试Cloud Storage连接"""
    try:
        client = storage.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT_ID'))
        bucket_name = os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET')
        bucket = client.bucket(bucket_name)
        
        if bucket.exists():
            print("✅ Cloud Storage 连接成功")
            print(f"   存储桶: {bucket_name}")
            return True
        else:
            print("❌ 存储桶不存在")
            return False
    except Exception as e:
        print(f"❌ Cloud Storage 连接失败: {e}")
        return False

def test_vision():
    """测试Vision API连接"""
    try:
        client = vision.ImageAnnotatorClient()
        print("✅ Vision API 连接成功")
        return True
    except Exception as e:
        print(f"❌ Vision API 连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 测试Google Cloud配置...")
    print("-" * 40)
    
    storage_ok = test_storage()
    vision_ok = test_vision()
    
    print("-" * 40)
    if storage_ok and vision_ok:
        print("🎉 所有服务配置正确！")
    else:
        print("⚠️  部分服务配置有问题，请检查配置")
EOF

# 运行测试
python test_gcp.py
```

### 步骤6.3: 启动API服务
```bash
# 启动开发服务器
python main.py

# 或使用uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤6.4: 测试API端点
```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试API文档
# 浏览器访问: http://localhost:8000/docs
```

### 步骤6.5: 使用测试客户端
```bash
# 找一张测试图片
wget https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Victoria_Park_Bedford.jpg/1280px-Victoria_Park_Bedford.jpg -O test_park.jpg

# 运行测试客户端
python utils/test_client.py test_park.jpg
```

---

## 7. 常见问题

### Q1: "Application Default Credentials"错误
**错误信息**: `Could not automatically determine credentials`

**解决方案**:
1. 确保`service-account-key.json`文件在正确位置
2. 检查`.env`文件中的`GOOGLE_APPLICATION_CREDENTIALS`路径
3. 或设置环境变量：
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
   ```

### Q2: 存储桶权限错误
**错误信息**: `403 Forbidden` 或 `Permission denied`

**解决方案**:
1. 检查服务账号是否有`Storage Admin`角色
2. 确认存储桶名称正确
3. 验证项目ID是否匹配

### Q3: Vision API配额限制
**错误信息**: `Quota exceeded` 或 `Rate limit`

**解决方案**:
1. 检查API配额使用情况：进入GCP Console > IAM和管理 > 配额
2. 如果是免费层，注意每月限制
3. 考虑启用计费账号以获得更高配额

### Q4: 网络连接问题
**错误信息**: `Connection timeout` 或 `DNS resolution failed`

**解决方案**:
1. 检查网络连接
2. 确认防火墙设置
3. 如果在中国大陆，可能需要配置代理

### Q5: 密钥文件格式错误
**错误信息**: `Invalid JSON` 或 `Malformed credentials`

**解决方案**:
1. 重新下载服务账号密钥文件
2. 确保文件完整且未被修改
3. 检查文件编码（应为UTF-8）

---

## 🔐 安全最佳实践

1. **密钥管理**:
   - 不要将密钥文件提交到Git
   - 定期轮换服务账号密钥
   - 使用最小权限原则

2. **网络安全**:
   - 在生产环境中使用HTTPS
   - 配置适当的CORS策略
   - 启用API密钥限制

3. **监控和日志**:
   - 启用Cloud Audit Logs
   - 监控API使用情况
   - 设置告警通知

---

## 📞 获取帮助

如果遇到问题：

1. **查看日志**: 检查应用程序日志输出
2. **Google Cloud文档**: [https://cloud.google.com/docs](https://cloud.google.com/docs)
3. **社区支持**: Stack Overflow, Reddit等
4. **官方支持**: Google Cloud支持（付费用户）

---

## ✅ 配置完成检查清单

- [ ] 创建了GCP项目
- [ ] 启用了Cloud Storage API
- [ ] 启用了Cloud Vision API  
- [ ] 创建了服务账号
- [ ] 分配了正确的角色权限
- [ ] 下载了密钥文件
- [ ] 创建了存储桶
- [ ] 配置了环境变量
- [ ] 测试了连接
- [ ] API服务正常启动
- [ ] 成功上传和分析了测试图像

完成所有检查项后，你的Google Cloud环境就配置完成了！🎉 