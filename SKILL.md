---
name: beauty-generator
description: Generate realistic beauty photography using OpenRouter (Gemini) or Doubao Seedream model. Supports artistic portrait style, scene/atmosphere control, emotion/makeup/art style customization, and WeChat publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真").
---

# Beauty Generator - 艺术写真生成 V2.0

高质量真人艺术写真生成助手，支持 OpenRouter (Gemini) 和豆包模型。

## 功能特点

- **高质量写真**: 使用 OpenRouter (Gemini) 生成更真实、更性感的艺术写真
- **每日一张精品**: 默认每天生成一张高质量写真，更吸引眼球
- **双模型支持**: 可选择使用 OpenRouter 或豆包模型
- **公众号发布**: 一键发布到公众号草稿箱（小绿书格式）
- **定时发布**: 每天 20:00 自动发布到公众号草稿箱

## 🆕 V2.0 更新

- 默认使用 OpenRouter (Gemini) 生成图片
- 更高质量的真人摄影风格
- 更性感、更吸引眼球的艺术写真
- 每日生成一张精品（可调整数量）

## 触发词

用户说以下内容时触发此技能：
- "生成美女"、"画一个美女"、"美女图片"
- "每日美女"、"今日美女"
- "发布美女"、"发布今日美女"
- "艺术写真"、"生成写真"
- 或类似表达

## 快速使用

### 基础使用
```bash
# 生成艺术写真（使用 OpenRouter/Gemini）
python3 ~/.claude/skills/beauty-generator/scripts/generate_artistic.py

# 生成多张
python3 ~/.claude/skills/beauty-generator/scripts/generate_artistic.py --count 3

# 预览 Prompt
python3 ~/.claude/skills/beauty-generator/scripts/generate_artistic.py --preview
```

### 使用豆包模型（备用）
```bash
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3
```

### 公众号发布
```bash
# 发布到公众号（默认使用 OpenRouter）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 使用豆包模型发布
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --use-doubao --count 3

# 测试模式（只生成不发布）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test --count 1
```

## API 配置

环境变量：
```bash
# OpenRouter (主要)
export OPENROUTER_API_KEY="your-openrouter-api-key"
export IMGBB_API_KEY="your-imgbb-api-key"

# 豆包 (备用)
export DOUBAO_API_KEY="your-doubao-api-key"

# 公众号发布
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
│   ├── generate_artistic.py    # 🆕 V2.0 艺术写真生成
│   ├── generate_beauty.py      # 豆包模式生成
│   ├── publish_wechat.py       # 公众号发布脚本
│   ├── auto_publish.py         # 本地定时发布
│   └── config_cron.sh          # cron 配置
├── config/
│   ├── api.json                # API配置
│   └── prompt_library.json     # Prompt 元素库
└── logs/                       # 运行日志
```

## 定时发布

**每天 20:00 自动发布到「三更愿」公众号草稿箱**

使用 Cloudflare Workers + GitHub Actions 实现精确定时触发。

## 版本信息

当前版本：**v2.0** (2026-01-19)

- V2.0: 改用 OpenRouter (Gemini) 生成高质量艺术写真
- V1.x: 使用豆包模型生成美女图片
