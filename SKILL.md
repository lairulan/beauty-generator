---
name: beauty-generator
version: 11.1.0
description: Generate realistic beauty photography with dual-engine (Google Imagen 4 Ultra + Doubao Seedream 4.5). 7-day style rotation (性感/甜美/国风/职场/生活场景/清纯/邻家), scene/emotion control, manual prompt mode, and WeChat auto-publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真", "手动生成美女", "自定义提示词生成").
author: rulanlai
tags: [image-generation, beauty, wechat, google-imagen, doubao]
---

# Beauty Generator - 艺术写真生成 V11.1

高质量真人艺术写真生成助手，双引擎架构：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退)。

## 功能特点

- **双模式生成**: 自动模式（元素库随机）+ 手动模式（用户自定义提示词）
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
- "手动生成美女"、"用提示词生成"、"自定义提示词生成"

## 两种模式

### 自动模式（默认）
从元素库（284个元素、9个维度）随机组合提示词，7日风格轮换，全自动。

### 手动模式
用户提供自定义提示词，直接调用双引擎生成，走完整发布流程推送到公众号草稿箱。

当用户说"用这个提示词生成"或直接给出英文 prompt 时，使用手动模式：
```bash
# 手动模式：自定义提示词生成并发布
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --prompt "A beautiful Asian woman in a red dress, standing in a field of sunflowers" \
  --count 1

# 手动模式 + 自定义配文
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --prompt "your prompt here" \
  --caption-text "向日葵田里的红裙少女。" \
  --title "手动精选 | 向日葵" \
  --count 1

# 手动模式：只生成不发布（测试）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --prompt "your prompt here" --test --count 1
```

## 快速使用

```bash
# 自动模式：生成图片
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3

# 自动模式：发布到公众号
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 手动模式：自定义提示词生成
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --prompt "your prompt" --count 1

# 手动模式：生成并发布
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --prompt "your prompt" --count 1
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

当前版本：**v11.1.0** (2026-03-22)
