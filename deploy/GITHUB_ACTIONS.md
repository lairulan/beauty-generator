# GitHub Actions 部署指南

## 为什么选择 GitHub Actions？

| 特性 | GitHub Actions | 云服务器 |
|------|----------------|----------|
| 费用 | **完全免费** | ¥30-100/月 |
| 维护 | **无需维护** | 需要维护系统 |
| 配置 | **简单** | 复杂 |
| 可靠性 | **99.9%** | 取决于服务器 |
| 日志 | **自动保存** | 需要手动查看 |
| 手动触发 | **支持** | 需要登录服务器 |

---

## 快速开始（5 分钟完成）

### 步骤 1: 创建 GitHub 仓库

1. 访问 https://github.com/new
2. 创建新仓库，命名为 `beauty-generator`
3. 选择 Public（公开仓库免费额度更高）
4. 不要初始化 README

---

### 步骤 2: 上传代码到 GitHub

在本地执行：

```bash
cd ~/.claude/skills/beauty-generator

# 初始化 git（如果还没有）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 添加远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/beauty-generator.git

# 推送
git push -u origin main
```

---

### 步骤 3: 配置 Secrets

1. 访问你的 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 添加以下 secrets：

| Name | Secret |
|------|--------|
| `OPENROUTER_API_KEY` | `your-openrouter-api-key` |
| `IMGBB_API_KEY` | `your-imgbb-api-key` |
| `DOUBAO_API_KEY` | `your-doubao-api-key` |
| `WECHAT_API_KEY` | `your-wechat-api-key` |

---

### 步骤 4: 启用 Actions

1. 点击 **Actions** 标签
2. 点击 **I understand my workflows, go ahead and enable them**
3. 选择 **每日美女生成发布** workflow
4. 点击 **Run workflow** 按钮测试

---

## 使用说明

### 自动运行

默认通过 Cloudflare Workers 触发 `repository_dispatch`，同时启用 GitHub Actions `schedule` 作为备份。
为避免重复执行，工作流内已加入当日成功运行去重逻辑，并把执行记录写入 `workflow_logs/actions_runs.md`。

### 手动触发

1. 访问仓库的 **Actions** 页面
2. 选择 **每日美男生成发布**
3. 点击 **Run workflow** → **Run workflow**

### 修改运行时间

编辑 `.github/workflows/daily-publish.yml`：

```yaml
schedule:
  - cron: '0 12 * * *'  # UTC 时间，北京时间 = UTC + 8
```

| 北京时间 | UTC 时间 | cron 表达式 |
|----------|----------|-------------|
| 20:00 | 12:00 | `0 12 * * *` |
| 8:00 | 0:00 | `0 0 * * *` |
| 12:00 | 4:00 | `0 4 * * *` |

---

## 查看日志

1. 访问 **Actions** 页面
2. 点击具体的运行记录
3. 点击任务查看详细日志
4. 日志自动保存 90 天

---

## 修改图片参数

编辑 `scripts/publish_wechat.py` 或直接在 workflow 中传递参数：

```yaml
- name: 生成并发布美女图片
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    IMGBB_API_KEY: ${{ secrets.IMGBB_API_KEY }}
    DOUBAO_API_KEY: ${{ secrets.DOUBAO_API_KEY }}
    WECHAT_API_KEY: ${{ secrets.WECHAT_API_KEY }}
  run: |
    cd scripts
    python3 publish_wechat.py --count 3 --emotion 挑逗 --scene 雨夜
```

---

## 故障排查

### 任务没有运行

1. 检查 cron 表达式是否正确
2. Actions 默认使用 UTC 时间，注意时区转换
3. 确认仓库是 Public（Private 仓库有额度限制）

### 环境变量错误

1. 检查 Secrets 是否正确配置
2. 确保 Name 完全匹配（大小写敏感）
3. 重新添加 Secrets 并重试

### 查看失败原因

1. 点击 Actions → 失败的运行
2. 展开失败的步骤
3. 查看详细日志

---

## 限制说明

| 仓库类型 | 免费额度 | 超限后 |
|----------|----------|--------|
| Public | **无限** | - |
| Private | 2000 分钟/月 | $0.008/分钟 |

**建议：使用公开仓库享受无限免费额度**

---

## 文件结构

```
beauty-generator/
├── .github/
│   └── workflows/
│       └── daily-publish.yml      # GitHub Actions 配置
├── scripts/
│   ├── publish_wechat.py          # 发布脚本
│   ├── generate_beauty.py         # 生成脚本
│   └── config_cron.sh             # 本地 cron 配置（备用）
├── deploy/
│   ├── README.md                  # 服务器部署文档（备用）
│   └── GITHUB_ACTIONS.md          # 本文档
├── SKILL.md
└── README.md
```

---

## 推荐方式对比

| 方式 | 推荐指数 | 适用场景 |
|------|----------|----------|
| **GitHub Actions** | ⭐⭐⭐⭐⭐ | **首选！免费、简单、稳定** |
| 云服务器 | ⭐⭐⭐ | 需要更多控制权时 |
| 本地 launchd | ⭐⭐ | 电脑保持开机时 |
