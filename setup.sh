#!/bin/bash
# Rethinking Park Backend API 自动化设置脚本
# 适用于 Arch Linux 系统

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "${BLUE}🚀 $1${NC}"
    echo "=================================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查是否在正确的目录
check_directory() {
    if [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
        print_error "请在 rethinkingpark-backend-v2 目录中运行此脚本"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    if [ ! -f "/etc/arch-release" ]; then
        print_warning "此脚本专为 Arch Linux 设计，其他系统可能需要手动安装"
        read -p "是否继续？ (y/N): " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 安装系统依赖
install_system_deps() {
    print_header "安装系统依赖"
    
    # 检查 yay 是否安装
    if ! command -v yay &> /dev/null; then
        print_error "yay 包管理器未安装"
        print_info "请先安装 yay: https://github.com/Jguer/yay#installation"
        exit 1
    fi
    
    # 更新系统
    print_info "更新系统包..."
    yay -Syu --noconfirm
    
    # 安装必要的包
    print_info "安装 Python 和相关工具..."
    yay -S --needed --noconfirm python python-pip python-venv git curl wget
    
    # 安装 Google Cloud CLI (可选)
    read -p "是否安装 Google Cloud CLI？ (y/N): " install_gcloud
    if [[ $install_gcloud =~ ^[Yy]$ ]]; then
        print_info "安装 Google Cloud CLI..."
        yay -S --needed --noconfirm google-cloud-cli
        print_success "Google Cloud CLI 安装完成"
        print_info "稍后可以运行 'gcloud auth login' 进行认证"
    fi
    
    print_success "系统依赖安装完成"
}

# 设置 Python 虚拟环境
setup_python_env() {
    print_header "设置 Python 虚拟环境"
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python -m venv venv
        print_success "虚拟环境创建完成"
    else
        print_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    print_info "激活虚拟环境..."
    source venv/bin/activate
    
    # 升级 pip
    print_info "升级 pip..."
    pip install --upgrade pip
    
    # 安装 Python 依赖
    print_info "安装 Python 依赖..."
    pip install -r requirements.txt
    
    print_success "Python 环境设置完成"
}

# 配置环境变量
setup_environment() {
    print_header "配置环境变量"
    
    if [ ! -f ".env" ]; then
        print_info "创建 .env 文件..."
        cp env.example .env
        print_success ".env 文件创建完成"
        
        print_warning "请编辑 .env 文件并填入你的 Google Cloud 配置:"
        print_info "- GOOGLE_CLOUD_PROJECT_ID: 你的 GCP 项目 ID"
        print_info "- GOOGLE_CLOUD_STORAGE_BUCKET: 存储桶名称"
        print_info "- GOOGLE_APPLICATION_CREDENTIALS: 密钥文件路径"
        
        read -p "现在打开编辑器配置 .env 文件？ (y/N): " edit_env
        if [[ $edit_env =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        print_info ".env 文件已存在"
    fi
}

# 测试 Google Cloud 配置
test_gcp_config() {
    print_header "测试 Google Cloud 配置"
    
    if [ ! -f "service-account-key.json" ]; then
        print_warning "未找到 service-account-key.json 文件"
        print_info "请将从 Google Cloud Console 下载的密钥文件重命名并放置在此目录"
        
        read -p "是否跳过配置测试？ (y/N): " skip_test
        if [[ $skip_test =~ ^[Yy]$ ]]; then
            return
        else
            print_error "请先配置 Google Cloud 密钥文件"
            exit 1
        fi
    fi
    
    print_info "运行配置测试..."
    if python test_gcp.py; then
        print_success "Google Cloud 配置测试通过"
    else
        print_error "Google Cloud 配置测试失败"
        print_info "请检查配置并参考 docs/google-cloud-setup.md"
        read -p "是否继续？ (y/N): " continue_setup
        if [[ ! $continue_setup =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 创建启动脚本
create_scripts() {
    print_header "创建便利脚本"
    
    # 创建启动脚本
    cat > start.sh << 'EOF'
#!/bin/bash
# 启动 Rethinking Park API 服务

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# 启动服务
echo "🚀 启动 Rethinking Park API..."
echo "📖 API 文档: http://localhost:8000/docs"
echo "🔍 健康检查: http://localhost:8000/health"
echo ""

python main.py
EOF
    
    chmod +x start.sh
    print_success "启动脚本创建完成: ./start.sh"
    
    # 创建测试脚本
    cat > test.sh << 'EOF'
#!/bin/bash
# 测试 API 功能

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if [ "$1" ]; then
    echo "🧪 测试图像上传和分析: $1"
    python utils/test_client.py "$1"
else
    echo "🏥 API 健康检查..."
    python utils/test_client.py
fi
EOF
    
    chmod +x test.sh
    print_success "测试脚本创建完成: ./test.sh [image_path]"
}

# 创建 systemd 服务文件（可选）
create_systemd_service() {
    read -p "是否创建 systemd 服务以便系统启动时自动运行？ (y/N): " create_service
    if [[ $create_service =~ ^[Yy]$ ]]; then
        print_header "创建 systemd 服务"
        
        SERVICE_FILE="/etc/systemd/system/rethinking-park-api.service"
        CURRENT_DIR=$(pwd)
        CURRENT_USER=$(whoami)
        
        sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Rethinking Park Backend API
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable rethinking-park-api.service
        
        print_success "systemd 服务创建完成"
        print_info "启动服务: sudo systemctl start rethinking-park-api"
        print_info "查看状态: sudo systemctl status rethinking-park-api"
        print_info "查看日志: sudo journalctl -u rethinking-park-api -f"
    fi
}

# 显示完成信息
show_completion_info() {
    print_header "安装完成"
    
    print_success "Rethinking Park Backend API 设置完成！"
    echo ""
    print_info "📁 项目目录: $(pwd)"
    print_info "🐍 Python 环境: venv/"
    print_info "⚙️  配置文件: .env"
    print_info "🔑 密钥文件: service-account-key.json"
    echo ""
    print_info "🚀 启动命令:"
    echo "   ./start.sh                    # 启动 API 服务"
    echo "   ./test.sh                     # 测试 API"
    echo "   ./test.sh image.jpg           # 测试图像上传"
    echo ""
    print_info "📖 更多信息:"
    echo "   API 文档: http://localhost:8000/docs"
    echo "   配置教程: docs/google-cloud-setup.md"
    echo "   项目文档: README.md"
    echo ""
    
    if [ ! -f "service-account-key.json" ]; then
        print_warning "下一步: 配置 Google Cloud"
        echo "1. 从 Google Cloud Console 下载服务账号密钥"
        echo "2. 重命名为 service-account-key.json 并放在此目录"
        echo "3. 编辑 .env 文件填入正确的配置"
        echo "4. 运行 python test_gcp.py 测试配置"
        echo ""
    fi
    
    read -p "现在启动 API 服务？ (y/N): " start_now
    if [[ $start_now =~ ^[Yy]$ ]]; then
        print_info "启动服务..."
        ./start.sh
    fi
}

# 主函数
main() {
    print_header "Rethinking Park Backend API 自动化设置"
    print_info "适用于 Arch Linux 系统"
    echo ""
    
    # 检查环境
    check_directory
    check_system
    
    # 执行安装步骤
    install_system_deps
    setup_python_env
    setup_environment
    test_gcp_config
    create_scripts
    create_systemd_service
    
    # 显示完成信息
    show_completion_info
}

# 错误处理
trap 'print_error "安装过程中发生错误，请检查上述输出"; exit 1' ERR

# 运行主函数
main "$@" 