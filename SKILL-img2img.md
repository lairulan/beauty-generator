---
name: beauty-img2img
version: 13.1.0
description: 基于参考图的图生图写真生成。使用豆包 Seedream 5.0 Lite + 参考图保持人物一致性，每日自动生成1张精品写真发布到微信公众号。触发词："图生图美女"、"参考图生成"、"换装写真"、"beauty img2img"。
author: rulanlai
tags: [image-generation, img2img, beauty, seedream, wechat]
---

# Beauty Img2Img - 参考图写真生成 V13.1

基于参考图的图生图写真生成。参考图提供人物一致性（脸部/体态），提示词只控制场景/服装/光线/氛围。

## 与 beauty-generator（文生图）的区别

| | beauty-generator（文生图） | beauty-img2img（图生图） |
|---|---|---|
| 人物来源 | prompt_library 随机组合 | 参考图决定 |
| 引擎参数 | 纯 prompt | prompt + image 数组 |
| 外貌描述 | 完整 face/hair/skin/body | 跳过，由参考图决定 |
| 适用场景 | 随机多样化生成 | 固定人物换场景 |

## 触发词

- "图生图美女"、"参考图生成"、"换装写真"
- "beauty img2img"、"ref image beauty"

## 快速使用

```bash
# 自动模式（需设置 REFERENCE_IMAGE_URL 环境变量）
export REFERENCE_IMAGE_URL="https://i.ibb.co/xxx/ref.jpg"
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 手动模式
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --count 1 --prompt "your scene prompt" --title "自定义标题"
```

## API 配置

```bash
export DOUBAO_API_KEY="..."          # 豆包 Seedream 5.0 Lite
export REFERENCE_IMAGE_URL="..."     # 参考图 URL（imgbb 永久链接）
export IMGBB_API_KEY="..."           # imgbb 图片托管
export WECHAT_API_KEY="..."          # 微信公众号 API
```

## 定时发布

由 Cloudflare Worker 触发 `daily-beauty-i2i` 事件 → GitHub Actions `daily-publish-i2i.yml`。
每天按星期轮换风格，生成 1 张精品图发布到公众号草稿箱。

## 模型

- 引擎：豆包 Seedream 5.0 Lite (`doubao-seedream-5-0-260128`)
- 参考图参数：`image` 数组（传入参考图 URL）
- Anti-AI：强化 negative prompt + 真实感锚点
