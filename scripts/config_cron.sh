#!/bin/bash
# 服务器端配置定时任务脚本
# 上传代码后，在服务器上运行此脚本

set -e

echo "=========================================="
echo "⏰ 美女生成器 - 定时任务配置"
echo "=========================================="

# 加载环境变量
source ~/.bashrc

# 检查环境变量
if [ -z "$DOUBAO_API_KEY" ] || [ -z "$WECHAT_API_KEY" ]; then
    echo "❌ 环境变量未设置，请先运行上传脚本"
    exit 1
fi

echo "✅ 环境变量检查通过"

# 切换到项目目录
cd ~/beauty-generator

# 测试运行
echo ""
echo "🧪 测试运行（生成 1 张图片）..."
/usr/bin/python3 scripts/publish_wechat.py --count 1 --test

if [ $? -eq 0 ]; then
    echo "✅ 测试成功"
else
    echo "❌ 测试失败，请检查配置"
    exit 1
fi

# 配置 cron 定时任务
echo ""
echo "⏰ 配置定时任务（每天 20:00）..."

# 创建 cron 脚本
cat > ~/beauty-generator/run_daily.sh << 'CRON_EOF'
#!/bin/bash
source ~/.bashrc
cd ~/beauty-generator
/usr/bin/python3 scripts/publish_wechat.py --count 3 >> logs/cron_$(date +\%Y\%m\%d).log 2>&1
CRON_EOF

chmod +x ~/beauty-generator/run_daily.sh

# 添加到 crontab
CRON_JOB="0 20 * * * ~/beauty-generator/run_daily.sh"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "beauty-generator"; then
    echo "⚠️  定时任务已存在，先删除旧任务..."
    crontab -l | grep -v "beauty-generator" | crontab -
fi

# 添加新的定时任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📋 定时任务信息："
echo "  - 运行时间: 每天 20:00"
echo "  - 生成数量: 3 张图片"
echo "  - 日志位置: ~/beauty-generator/logs/"
echo ""
echo "📝 常用命令："
echo "  查看定时任务: crontab -l"
echo "  查看日志: tail -f ~/beauty-generator/logs/cron_\$(date +%Y%m%d).log"
echo "  手动运行: ~/beauty-generator/run_daily.sh"
echo ""
echo "=========================================="
