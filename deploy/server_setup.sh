#!/bin/bash
# 云服务器自动安装脚本
# 在服务器上运行此脚本

set -e

echo "=========================================="
echo "🚀 美女生成器 - 云服务器部署脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 用户运行此脚本"
    echo "   sudo bash server_setup.sh"
    exit 1
fi

# 获取当前用户（非 root 时）
REAL_USER=${SUDO_USER:-root}
USER_HOME=$(eval echo ~$REAL_USER)

echo "📦 安装系统依赖..."
apt update
apt install -y python3 python3-pip curl

echo "📁 创建项目目录..."
mkdir -p /home/$REAL_USER/beauty-generator
cd /home/$REAL_USER/beauty-generator

# 创建必要的目录
mkdir -p scripts logs config

echo "✅ 安装完成！"
echo ""
echo "=========================================="
echo "📝 下一步："
echo "=========================================="
echo "1. 在本地电脑运行上传脚本："
echo "   bash deploy/local_upload.sh 你的服务器IP"
echo ""
echo "2. 上传完成后，在服务器运行："
echo "   bash deploy/config_cron.sh"
echo "=========================================="
