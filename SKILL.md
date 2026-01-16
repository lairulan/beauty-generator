---
name: beauty-generator
description: Generate realistic beauty photography using Doubao Seedream model. Supports scene/atmosphere control, emotion/makeup/art style customization, and WeChat publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女").
---

# Beauty Generator - 美女图像生成 V5.0

专业写实摄影风格东方美女图像生成助手，基于豆包 Seedream 图像生成模型。

## 功能特点

- **智能随机系统**: 从丰富元素库随机组合，确保每次生成都有新鲜感
- **严格东方美女**: 强制生成中国/东亚面孔，排除西方特征
- **在线图片**: 返回豆包云URL，可直接使用
- **人物一致性**: 每日3张图片保持同一人物特征，仅改变姿态/角度
- **图生图技术**: 使用第一张图作为参考，提升后续图片一致性
- **公众号发布**: 一键发布到公众号草稿箱（小绿书格式）
- **定时发布**: 每天 20:00 自动发布到公众号草稿箱

## 🆕 V5.0 智能随机系统

### 人物风格 (6 种)
- 甜美系、清纯系、御姐系、知性系、冷艳系、性感系

### 场景类型 (4 种)
- 自然、城市、室内、特殊

### 穿搭风格 (6 种)
- 优雅、性感、清新、时尚、古典、运动

### 表情类型 (5 种)
- 微笑、性感、冷艳、忧郁、自信

### 光影类型 (3 种)
- 自然光、影棚、氛围

## 触发词

用户说以下内容时触发此技能：
- "生成美女"、"画一个美女"、"美女图片"
- "每日美女"、"今日美女"
- "发布美女"、"发布今日美女"
- 或类似表达

## 快速使用

### 基础使用
```bash
# 完全随机生成（推荐）
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py

# 生成指定数量
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3
```

### 指定风格
```bash
# 指定人物风格
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --style "御姐系"

# 指定场景和穿搭
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --style "甜美系" --scene "自然" --outfit "清新"
```

### 查看所有选项
```bash
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --list-options
```

### 预览 Prompt
```bash
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --preview
```

### 公众号发布
```bash
# 发布到公众号
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 3

# 测试模式（只生成不发布）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test --count 3
```

## API 配置

环境变量：
```bash
export DOUBAO_API_KEY="your-doubao-api-key"
export WECHAT_API_KEY="your-wechat-api-key"
```

## 文件结构

```
beauty-generator/
├── SKILL.md                    # 本文件
├── CHANGELOG.md                # 版本历史
├── README.md                   # 使用说明
├── .github/workflows/          # GitHub Actions
├── deploy/                     # 部署脚本
├── scripts/
│   ├── generate_beauty.py      # V5.0 主生成脚本
│   ├── publish_wechat.py       # 公众号发布脚本
│   ├── auto_publish.py         # 本地定时发布
│   └── config_cron.sh          # cron 配置
├── config/
│   ├── api.json                # API配置
│   └── prompt_library.json     # 🆕 Prompt 元素库
└── logs/                       # 运行日志
```

## 定时发布

**每天 20:00 自动发布到「三更愿」公众号草稿箱**

推荐使用 GitHub Actions（免费、无需服务器）：
```bash
bash deploy/github_deploy.sh
```

## 版本信息

当前版本：**v5.0** (2026-01-16)

完整版本历史请查看 [CHANGELOG.md](CHANGELOG.md)
