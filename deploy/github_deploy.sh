#!/bin/bash
# GitHub Actions 一键部署脚本

set -e

echo "=========================================="
echo "🚀 美女生成器 - GitHub Actions 部署"
echo "=========================================="

# 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "❌ 未安装 git，请先安装:"
    echo "   brew install git  # macOS"
    echo "   apt install git   # Ubuntu/Debian"
    exit 1
fi

# 获取 GitHub 用户名
read -p "请输入你的 GitHub 用户名: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ 用户名不能为空"
    exit 1
fi

REPO_NAME="beauty-generator"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "📋 配置信息:"
echo "  用户名: $GITHUB_USERNAME"
echo "  仓库名: $REPO_NAME"
echo "  本地路径: $SCRIPT_DIR"
echo ""

# 确认
read -p "确认创建并推送到 GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
fi

cd "$SCRIPT_DIR"

# 初始化 git
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
    git branch -M main
else
    echo "✅ Git 仓库已存在"
fi

# 创建 .gitignore
echo "📄 创建 .gitignore..."
cat > .gitignore << 'EOF'
# 日志
logs/
*.log

# 临时文件
output/
.DS_Store
*.pyc
__pycache__/

# 环境变量
.env
EOF

# 添加所有文件
echo "📦 添加文件到 Git..."
git add .

# 提交
echo "💾 提交更改..."
git commit -m "feat: 初始化美女生成器 - GitHub Actions 自动部署" || echo "✅ 无新更改需要提交"

# 添加远程仓库
REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
if git remote get-url origin &> /dev/null; then
    echo "✅ 远程仓库已存在，更新 URL..."
    git remote set-url origin "$REMOTE_URL"
else
    echo "🔗 添加远程仓库..."
    git remote add origin "$REMOTE_URL"
fi

# 推送
echo "📤 推送到 GitHub..."
echo ""
echo "=========================================="
echo "⚠️  推送前请确保："
echo "=========================================="
echo "1. 已在 GitHub 创建仓库: $REPO_NAME"
echo "   访问: https://github.com/new"
echo ""
echo "2. 仓库设置为 Public（免费无限额度）"
echo ""
echo "3. 推送后需要配置 Secrets:"
echo "   DOUBAO_API_KEY = a26f05b1-4025-4d66-a43d-ea3a64b267cf"
echo "   WECHAT_API_KEY = xhs_4abcfb085d38aeb676ba5eb1ebc205c0"
echo ""
echo "=========================================="

read -p "按回车继续推送..."

git push -u origin main

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📝 下一步："
echo ""
echo "1. 访问你的仓库:"
echo "   https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""
echo "2. 配置 Secrets:"
echo "   Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "3. 添加两个 Secrets:"
echo "   Name: DOUBAO_API_KEY"
echo "   Value: a26f05b1-4025-4d66-a43d-ea3a64b267cf"
echo ""
echo "   Name: WECHAT_API_KEY"
echo "   Value: xhs_4abcfb085d38aeb676ba5eb1ebc205c0"
echo ""
echo "4. 启用 Actions:"
echo "   Actions → I understand my workflows → Run workflow"
echo ""
echo "=========================================="
