# 云服务器部署指南

## 快速部署（3 步完成）

### 步骤 1: 服务器初始化

购买服务器后，SSH 连接到服务器：

```bash
ssh root@你的服务器IP
```

然后下载并运行安装脚本：

```bash
# 创建部署目录
mkdir -p ~/beauty-generator/deploy

# 下载安装脚本（在本地执行后上传到服务器）
# 或者直接在服务器上创建 server_setup.sh 文件
```

运行安装脚本：

```bash
bash ~/beauty-generator/deploy/server_setup.sh
```

---

### 步骤 2: 上传代码

在**本地电脑**上运行：

```bash
cd ~/.claude/skills/beauty-generator
bash deploy/local_upload.sh 你的服务器IP
```

示例：
```bash
bash deploy/local_upload.sh 123.45.67.89
# 如果不是 root 用户
bash deploy/local_upload.sh 123.45.67.89 ubuntu
```

---

### 步骤 3: 配置定时任务

在**服务器**上运行：

```bash
ssh root@你的服务器IP
cd ~/beauty-generator
bash scripts/config_cron.sh
```

---

## 验证部署

在服务器上检查定时任务：

```bash
# 查看定时任务
crontab -l

# 应该看到：
# 0 20 * * * ~/beauty-generator/run_daily.sh
```

查看日志：

```bash
tail -f ~/beauty-generator/logs/cron_$(date +%Y%m%d).log
```

---

## 常用命令

| 操作 | 命令 |
|------|------|
| 查看定时任务 | `crontab -l` |
| 编辑定时任务 | `crontab -e` |
| 删除定时任务 | `crontab -r` |
| 手动运行 | `~/beauty-generator/run_daily.sh` |
| 查看日志 | `tail -f ~/beauty-generator/logs/cron_*.log` |
| 测试发布 | `cd ~/beauty-generator && python3 scripts/publish_wechat.py --count 1 --test` |

---

## 推荐云服务器

| 服务商 | 配置 | 价格 | 链接 |
|--------|------|------|------|
| 阿里云 | 2核2G | ¥60/月 | https://www.aliyun.com/product/swas |
| 腾讯云 | 2核2G | ¥50/月 | https://cloud.tencent.com/product/lighthouse |
| Vultr | 1核1G | $5/月 | https://www.vultr.com |

---

## 故障排查

### 定时任务没执行

1. 检查 cron 服务状态：
```bash
service cron status
```

2. 查看 cron 日志：
```bash
tail -f ~/beauty-generator/logs/cron_*.log
```

### 环境变量问题

确保 `~/.bashrc` 中有：
```bash
export DOUBAO_API_KEY="a26f05b1-4025-4d66-a43d-ea3a64b267cf"
export WECHAT_API_KEY="xhs_4abcfb085d38aeb676ba5eb1ebc205c0"
```

重新加载：
```bash
source ~/.bashrc
```

---

## 文件结构

```
服务器上的文件结构：
~/beauty-generator/
├── scripts/
│   ├── publish_wechat.py      # 发布脚本
│   ├── generate_beauty.py     # 生成脚本
│   └── config_cron.sh         # 定时任务配置
├── logs/                       # 日志目录
├── config/                     # 配置目录
└── run_daily.sh               # 每日运行脚本
```
