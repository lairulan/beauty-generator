---
name: beauty-generator
version: 12.36.0
description: 独立文生图写真仓库。Google Imagen 4 Ultra 主力，Doubao Seedream 4.5 回退，支持 22-23 岁年轻成人女性写真 prompt、生活场景文生图短强正向约束、明亮清透中国东方审美脸部档案、高键清透但保留立体骨相、冷中性白里透红/奶白东亚肤色、近乎透明淡婴儿粉水润唇、凤眼感杏眼/狐狸杏眼、眼尾上扬、强 catchlight 回看镜头眼神吸引力、自然发缝/碎发/轻微毛躁/真实发丝密度、鹅蛋瓜子脸/窄颌柔下巴、小巧高鼻梁和小鼻翼小鼻孔、颧骨弧线、鼻梁高光、鼻侧微阴影、清晰但年轻的下颌转折、五官和谐漂亮、鲜亮性感但非露骨的生活写真色彩、fully dressed 性感艺术照式丰满但非露骨胸腰轮廓、无遮挡生活半身构图、场景/情绪控制、手动 prompt、手动模板提示词库、公众号草稿箱发布与 7 天风格轮换。Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真", "文生图美女").
author: rulanlai
tags: [image-generation, beauty, wechat, google, doubao, seedream]
---

# Beauty Generator - 文生图写真 V12.36

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
