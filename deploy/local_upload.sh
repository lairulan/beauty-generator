#!/bin/bash
# 本地上传脚本
# 在本地电脑运行此脚本，将代码上传到服务器

set -e

if [ -z "$1" ]; then
    echo "❌ 请提供服务器 IP 地址"
    echo "   用法: bash local_upload.sh <服务器IP> [用户名]"
    echo "   示例: bash local_upload.sh 123.45.67.89 root"
    exit 1
fi

SERVER_IP=$1
SERVER_USER=${2:-root}

echo "=========================================="
echo "📤 美女生成器 - 代码上传脚本"
echo "=========================================="
echo "服务器: $SERVER_USER@$SERVER_IP"
echo ""

# 检查服务器连接
echo "🔍 检查服务器连接..."
if ! ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_IP "echo '连接成功'" > /dev/null 2>&1; then
    echo "❌ 无法连接到服务器 $SERVER_USER@$SERVER_IP"
    echo "   请检查："
    echo "   1. 服务器 IP 是否正确"
    echo "   2. SSH 服务是否运行"
    echo "   3. 是否已配置 SSH 密钥或密码"
    exit 1
fi
echo "✅ 连接成功"

# 源目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 本地目录: $SCRIPT_DIR"

# 上传文件
echo ""
echo "📤 开始上传文件..."

# 创建远程目录结构
ssh $SERVER_USER@$SERVER_IP "mkdir -p ~/beauty-generator/{scripts,logs,config}"

# 上传核心脚本
echo "  📄 上传脚本文件..."
scp $SCRIPT_DIR/scripts/publish_wechat.py $SERVER_USER@$SERVER_IP:~/beauty-generator/scripts/
scp $SCRIPT_DIR/scripts/generate_beauty.py $SERVER_USER@$SERVER_IP:~/beauty-generator/scripts/

# 上传配置文件
echo "  📄 上传配置文件..."
if [ -f "$SCRIPT_DIR/config/daily_styles.json" ]; then
    scp $SCRIPT_DIR/config/daily_styles.json $SERVER_USER@$SERVER_IP:~/beauty-generator/config/
fi

# 上传并设置环境变量
echo "  🔑 配置环境变量..."
echo "  ⚠️  请手动在服务器上设置环境变量："
echo "     export DOUBAO_API_KEY=\"your-doubao-api-key\""
echo "     export WECHAT_API_KEY=\"your-wechat-api-key\""
echo ""
echo "  或者取消注释下面的代码并填入实际的 API keys"
# ssh $SERVER_USER@$SERVER_IP "cat >> ~/.bashrc << 'EOF'
#
# # 美女生成器环境变量
# export DOUBAO_API_KEY=\"your-doubao-api-key\"
# export WECHAT_API_KEY=\"your-wechat-api-key\"
# EOF"

# 设置脚本权限
ssh $SERVER_USER@$SERVER_IP "chmod +x ~/beauty-generator/scripts/*.py"

echo ""
echo "=========================================="
echo "✅ 上传完成！"
echo "=========================================="
echo ""
echo "📝 下一步：在服务器上运行以下命令完成配置"
echo ""
echo "   ssh $SERVER_USER@$SERVER_IP"
echo "   cd ~/beauty-generator"
echo "   bash scripts/config_cron.sh"
echo ""
echo "=========================================="
