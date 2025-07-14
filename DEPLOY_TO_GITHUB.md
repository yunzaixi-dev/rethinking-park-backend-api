# 部署到GitHub指南

本文档提供了将 Rethinking Park Backend API 项目部署到GitHub的详细步骤。

## 📋 准备工作

✅ Git仓库已初始化  
✅ 代码已提交  
✅ Git用户信息已配置：`yunzaixi-dev <x@zaixi.dev>`  
✅ 项目目录：`rethinking-park-backend-api`  

## 🚀 方法一：使用GitHub CLI（推荐）

### 安装GitHub CLI
```bash
# Arch Linux
yay -S github-cli

# 或者使用官方二进制
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### 创建并推送仓库
```bash
# 1. 登录GitHub
gh auth login

# 2. 创建仓库并推送
gh repo create rethinking-park-backend-api --public --source=. --remote=origin --push

# 3. 设置仓库描述和话题
gh repo edit --description "🌳 智能公园图像分析API - 基于FastAPI和Google Cloud构建的现代化后端服务" \
             --add-topic fastapi \
             --add-topic google-cloud \
             --add-topic vision-api \
             --add-topic image-analysis \
             --add-topic python \
             --add-topic backend-api \
             --add-topic park-analysis
```

## 🌐 方法二：使用GitHub网页界面

### 1. 创建GitHub仓库
1. 访问 [GitHub](https://github.com)
2. 点击右上角的 "+" → "New repository"
3. 填写仓库信息：
   - **Repository name**: `rethinking-park-backend-api`
   - **Description**: `🌳 智能公园图像分析API - 基于FastAPI和Google Cloud构建的现代化后端服务`
   - **Visibility**: Public（推荐）
   - **不要**勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

### 2. 推送现有代码
```bash
# 添加远程仓库
git remote add origin https://github.com/yunzaixi-dev/rethinking-park-backend-api.git

# 推送代码
git branch -M main
git push -u origin main
```

## 🏷️ 方法三：完整的手动配置

```bash
# 1. 添加远程仓库（替换为你的用户名）
git remote add origin https://github.com/yunzaixi-dev/rethinking-park-backend-api.git

# 2. 验证远程仓库
git remote -v

# 3. 推送到GitHub
git push -u origin main

# 4. 验证推送成功
git log --oneline
```

## 📝 推荐的仓库设置

### 仓库信息
- **名称**: `rethinking-park-backend-api`
- **描述**: `🌳 智能公园图像分析API - 基于FastAPI和Google Cloud构建的现代化后端服务`
- **网站**: `https://your-api-domain.com`（如果有的话）

### 标签/话题 (Topics)
```
fastapi
google-cloud
vision-api
image-analysis
python
backend-api
park-analysis
machine-learning
cloud-storage
docker
rest-api
```

### 分支保护规则（可选）
如果你计划协作开发，建议设置：
- 要求Pull Request审查
- 要求状态检查通过
- 要求分支最新

## 🔗 仓库URLs

创建成功后，你的仓库将位于：

- **HTTPS**: `https://github.com/yunzaixi-dev/rethinking-park-backend-api`
- **SSH**: `git@github.com:yunzaixi-dev/rethinking-park-backend-api.git`
- **GitHub CLI**: `gh repo view yunzaixi-dev/rethinking-park-backend-api`

## 📚 下一步

仓库创建成功后：

1. **添加README徽章**：
   ```markdown
   ![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
   ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
   ![License](https://img.shields.io/badge/license-MIT-blue.svg)
   ```

2. **设置GitHub Actions** (CI/CD):
   - 代码质量检查
   - 自动测试
   - Docker镜像构建

3. **添加安全配置**:
   - Dependabot
   - Security policy
   - Secret scanning

4. **文档完善**:
   - Wiki页面
   - API文档托管
   - 贡献指南

## 🔧 故障排除

### 认证问题
```bash
# 如果推送时要求认证，设置个人访问令牌
git config --global credential.helper store
```

### 远程仓库已存在
```bash
# 如果仓库已存在但为空
git push -f origin main

# 如果仓库有内容但你想强制推送
git push --force-with-lease origin main
```

### SSH密钥设置
```bash
# 生成SSH密钥（如果没有）
ssh-keygen -t ed25519 -C "x@zaixi.dev"

# 添加到ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 复制公钥到GitHub
cat ~/.ssh/id_ed25519.pub
```

---

**选择你偏好的方法执行即可！推荐使用GitHub CLI，它最简单快捷。** 