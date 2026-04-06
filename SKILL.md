---
name: beauty-generator
version: 13.1.0
description: Generate realistic beauty photography with Doubao Seedream 5.0 Lite. 7-day style rotation (性感/甜美/国风/职场/生活场景/清纯/邻家), scene/emotion control, manual prompt mode, and WeChat auto-publishing. Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真", "文生图美女").
author: rulanlai
tags: [image-generation, beauty, wechat, doubao, seedream]
---

# Beauty Generator - 文生图写真 V13.1

纯文生图模式：从 284 元素 × 9 维度的元素库随机组合提示词，生成高质量艺术写真。

## 与 beauty-img2img（图生图）的区别

- **本 skill**：纯文生图，prompt_library 完整随机（含 face/hair/skin/body）
- **beauty-img2img**：基于参考图图生图，跳过外貌描述，由参考图决定人物

## 触发词

- "生成美女"、"画一个美女"、"美女图片"
- "每日美女"、"今日美女"、"文生图美女"
- "发布美女"、"艺术写真"

## 快速使用

```bash
# 自动模式
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 手动模式
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --prompt "your prompt" --count 1
```

## API 配置

```bash
export DOUBAO_API_KEY="..."   # 豆包 Seedream 5.0 Lite
export IMGBB_API_KEY="..."    # imgbb 图片托管
export WECHAT_API_KEY="..."   # 微信公众号 API
```

## 定时发布

CF Worker 触发 `daily-beauty` → GitHub Actions `daily-publish.yml`。7 风格按星期轮换。
