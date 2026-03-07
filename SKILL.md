---
name: beauty-generator
version: 3.0.0
description: Generate realistic beauty photography using Doubao Seedream model. Supports artistic portrait style, scene/atmosphere control, emotion/makeup/art style customization, and WeChat publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真").
author: rulanlai
tags: [image-generation, beauty, wechat, doubao]
---

# Beauty Generator - 艺术写真生成 V3.0

高质量真人艺术写真生成助手，使用豆包 Seedream 模型。

## 功能特点

- **高质量写真**: 使用豆包 Seedream 生成真实的艺术写真
- **每日一张精品**: 默认每天生成一张写真，更吸引眼球
- **公众号发布**: 一键发布到公众号草稿箱（小绿书格式）
- **定时发布**: 每天 20:00 自动发布到公众号草稿箱

## 🆕 V3.0 更新

- 改用豆包 API,移除 OpenRouter 依赖
- 简化 API 配置,只需一个 DOUBAO_API_KEY
- 更稳定的图片生成体验

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
# 生成图片
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3
```

### 公众号发布
```bash
# 发布到公众号
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 测试模式（只生成不发布）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test --count 1
```

## API 配置

环境变量：
```bash
# 豆包 API (图片生成)
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
│   ├── generate_beauty.py      # 豆包图片生成
│   ├── publish_wechat.py       # 公众号发布脚本
│   ├── auto_publish.py         # 本地定时发布
│   └── config_cron.sh          # cron 配置
├── config/
│   ├── api.json                # API配置
│   └── prompt_library.json     # Prompt 元素库
└── logs/                       # 运行日志
```

## 定时发布

**每天 20:00 自动发布到「三更熟」公众号草稿箱**

使用 Cloudflare Workers + GitHub Actions 实现精确定时触发。

## 版本信息

当前版本：**v3.0** (2026-02-16)

- V3.0: 移除 OpenRouter 依赖,专用豆包 API
- V2.x: 支持 OpenRouter fallback
- V1.x: 使用豆包模型生成美女图片
