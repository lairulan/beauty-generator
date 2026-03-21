---
name: beauty-generator
version: 11.0.0
description: Generate realistic beauty photography with dual-engine (Google Imagen 4 Ultra + Doubao Seedream 4.5). 7-day style rotation (性感/甜美/国风/职场/生活场景/清纯/邻家), scene/emotion control, and WeChat auto-publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真").
author: rulanlai
tags: [image-generation, beauty, wechat, google-imagen, doubao]
---

# Beauty Generator - 艺术写真生成 V11.0

高质量真人艺术写真生成助手，双引擎架构：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退)。

## 功能特点

- **双引擎生成**: Google Imagen 4 Ultra 优先，豆包 Seedream 4.5 自动回退
- **7日风格轮换**: 性感/甜美/国风/职场/生活场景/清纯/邻家，全面偏暖性感
- **智能 Prompt**: 从丰富元素库随机组合，严格东方美女
- **动态配文**: 基于 META 元数据自动生成与图片贴合的配文和标签
- **公众号发布**: 一键发布到「三更熟」公众号草稿箱（小绿书格式）
- **定时发布**: 每天 19:30 自动触发（CF Worker → GitHub Actions）

## 触发词

- "生成美女"、"画一个美女"、"美女图片"
- "每日美女"、"今日美女"
- "发布美女"、"发布今日美女"
- "艺术写真"、"生成写真"

## 快速使用

```bash
# 生成图片
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3

# 发布到公众号
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 测试模式
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test --count 1
```

## API 配置

```bash
export GOOGLE_API_KEY="..."   # Google Imagen 4 Ultra (优先)
export DOUBAO_API_KEY="..."   # 豆包 Seedream (回退)
export IMGBB_API_KEY="..."    # imgbb 图片托管 (Google 生成的图片需上传)
export WECHAT_API_KEY="..."   # 微信公众号 API
```

## 定时发布

每天 19:30 由 Cloudflare Worker 触发 GitHub Actions（仅 repository_dispatch，无 schedule 备用）。
7日风格轮换：周一性感→周二甜美→周三国风→周四职场→周五居家→周六纯欲→周日邻家。

## 版本信息

当前版本：**v11.0.0** (2026-03-21)
