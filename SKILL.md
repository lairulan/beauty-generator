---
name: beauty-generator
version: 12.27.0
description: 独立文生图写真仓库。Google Imagen 4 Ultra 主力，Doubao Seedream 4.5 回退，支持 22-24 岁年轻成人女性写真 prompt、基于参考图式东方审美脸部档案、三分之二侧脸但眼神回看镜头、侧分长黑发修饰脸侧并排除短发波波头、鹅蛋瓜子脸/窄颌柔下巴、内双杏眼/卧蚕高光、柔弧柳叶眉、挺秀高直鼻梁、小巧鼻翼和鼻孔、花瓣微笑唇、无明显口红的淡裸粉润唇、含蓄性感艺术写真语气、日常丰满但非露骨的女性轮廓、无遮挡生活半身构图、场景/情绪控制、手动 prompt、公众号草稿箱发布与 7 天风格轮换。Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真", "文生图美女").
author: rulanlai
tags: [image-generation, beauty, wechat, google, doubao, seedream]
---

# Beauty Generator - 文生图写真 V12.27

纯文生图模式：Google Imagen 4 Ultra（主力）+ 豆包 Seedream 4.5（兜底）。从元素库随机组合人物、场景、穿搭、光线和艺术风格，生成高质量年轻成熟女性艺术写真，并可直接发布到微信公众号草稿箱。

## 与 beauty-img2img（图生图）的区别

- **本 skill**：纯文生图，prompt_library 完整随机（含 face/hair/skin/body）
- **beauty-img2img**：基于参考图图生图，跳过外貌描述，由参考图决定人物

## 触发词

- "生成美女"、"画一个美女"、"美女图片"
- "每日美女"、"今日美女"、"文生图美女"
- "发布美女"、"艺术写真"、"公众号美女图"

## 快速使用

```bash
# 在仓库根目录执行

# 自动模式：生成并发布 1 张
python3 scripts/publish_wechat.py --count 1

# 手动 prompt
python3 scripts/publish_wechat.py \
  --prompt "your prompt" --count 1

# 测试模式：只生成不发布
python3 scripts/publish_wechat.py \
  --test --count 1 --scene "城市" --emotion "自信"

# 预览自动策略 prompt，可用日志里的随机种子复现
python3 scripts/generate_beauty.py \
  --preview --style "职场系" --emotion "自信" --seed 533224
```

## API 配置

```bash
export GOOGLE_API_KEY="..."    # Google Imagen 4 Ultra（主力）
export DOUBAO_API_KEY="..."    # 豆包 Seedream 4.5（回退）
export IMGBB_API_KEY="..."     # Google 生成图片上传所需
export WECHAT_API_KEY="..."    # 微信公众号 API
export WECHAT_API_ALLOW_INSECURE_SSL="1"  # 可选：证书异常时允许临时回退
```

## 定时发布

- Cloudflare Worker 触发 `daily-beauty` → GitHub Actions `daily-publish.yml`
- GitHub Actions 原生 `schedule` 兜底：UTC 12:00 / 北京 20:00
- `workflow_dispatch` 可手动补跑
- 自动触发会先检查 GitHub Actions 当日成功记录，再回查远端月度日志，避免重复发布
- 7 风格按星期轮换
