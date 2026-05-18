---
name: beauty-generator
version: 12.45.1
description: 独立文生图写真仓库。Google Imagen 4 Ultra (`imagen-4.0-ultra-generate-001`) 主力，统一使用 GEMINI_API_KEY（本地兼容旧 GOOGLE_API_KEY），Doubao Seedream 4.5 回退，自动文生图和自动发布固定为性感系/相近吸引力写真风格，支持 22-23 岁年轻成人女性写真 prompt、东方审美原则、明亮清透中国东方审美脸部档案、高键清透但避免平面证件照、冷中性白里透红/奶白东亚肤色、近乎透明淡婴儿粉水润唇、凤眼感杏眼/狐狸杏眼、眼尾上扬、强 catchlight 回看镜头眼神吸引力、自然发缝/碎发/轻微毛躁/真实发丝密度、鹅蛋瓜子脸/窄颌柔下巴、小巧高鼻梁和小鼻翼小鼻孔、颧骨弧线、鼻梁高光、鼻侧微阴影、清晰但年轻的下颌转折、五官和谐漂亮、有生活背景和活力姿态、轻薄或结构化 fully dressed 性感艺术照式丰满但非露骨胸腰轮廓、无遮挡构图、场景/情绪控制、手动 prompt、手动模板提示词库、公众号草稿箱发布。Use when user asks to generate beauty images ("生成美女", "每日美女", "发布美女", "艺术写真", "文生图美女").
author: rulanlai
tags: [image-generation, beauty, wechat, google, doubao, seedream]
---

# Beauty Generator - 文生图写真 V12.45.1

纯文生图模式：Google Imagen 4 Ultra（主力）+ 豆包 Seedream 4.5（兜底）。自动模式固定为性感系/相近吸引力写真，从元素库随机组合人物、场景、穿搭、光线和艺术风格，生成高质量年轻成熟女性艺术写真，并可直接发布到微信公众号草稿箱。

## V12.45 重要更新

- **统一 Key**：Google 文生图运行时优先读取 `GEMINI_API_KEY`，本地仅兼容旧 `GOOGLE_API_KEY`，不再使用 `GOOGLE_API_KEY_BACKUP`。
- **模型确认**：文生图继续使用 `imagen-4.0-ultra-generate-001`。这是 Imagen 4 Ultra 高质量纯文生图路径，不切到更适合参考图编辑的 Gemini 图像模型。
- **Actions 兼容**：GitHub Actions 仍复用现有 secret `GOOGLE_API_KEY`，但注入到运行环境时命名为 `GEMINI_API_KEY`。

## V12.44 重要更新

- **自动风格固定**：自动文生图和自动发布统一为 `性感系 / 性感`，不再按星期轮换到其他风格。
- **兼容旧参数**：传入其他 `--style` 或 `--emotion` 时会记录告警并规范到性感系，避免旧 workflow 继续跑偏。
- **发布文案同步**：标题、开场和图片说明只保留性感/吸引力写真调性。

## V12.39 仍保留的 Prompt 优化

- **Prompt 大幅瘦身**：单条 prompt 词数 -41%（lifestyle 风格 4731 → 2702 词），Imagen 长尾约束被有效保留。
- **Negative prompt 拆分**：原 250+ token 单串 `anti_ai` 拆为 `anti_face / anti_body / anti_hair_makeup / anti_age_mood / anti_scene` 五个 ≤75 token 子串，按 pose/style 选择拼接，避免被豆包静默截断。
- **唇色多样化**：保留 `lip_color_palette`（性感系 3 选 1 fallback），同风格多张图妆感不再雷同。
- **种族 negative 改写**：去掉具体种族枚举（Indian / Latin / Southeast Asian / Eurasian），改为 "non-East-Asian features" 单条。
- **代码瘦身**：删除 minimax 死代码 + 内置 fallback 库（fail-fast 改造），单文件 2070 → 1601 行（-23%）；备份 JSON 归档到 `config/archive/`。
- **风格枚举常量化**：`STYLE_LIFESTYLE / STYLE_SEXY` 等顶层常量替换散字符串。

## 引擎与 negative_prompt 行为

- **Google Imagen 4 Ultra（主路径）不接收 negative_prompt** — 所有肤色/唇色/比例/排他约束都必须在正向 prompt 前半段硬约束。
- **豆包 Seedream 4.5（fallback）使用 negative_prompt** — V12.39 起按 pose/style 分类拼接，避免单串被截断。
- **`FORCE_GOOGLE_ONLY=1`** 模式下豆包不兜底，Google 失败即返回错误，适合需要严格保证主路径成功率的场景。
- 生产 workflow 默认 `FORCE_GOOGLE_ONLY=0`，Google 限流或失败时会启用豆包兜底；手动运行仍可勾选 `force_google_only=true` 临时禁用兜底。
- **图床默认仅 imgbb 单点**（`config/constants.json` 中 `image_hosts` 默认配置）。需要双图床冗余时可在配置里加 `sm.ms`，代码已支持。

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
  --test --count 1 --scene "城市" --emotion "性感"

# 预览自动策略 prompt，可用日志里的随机种子复现
python3 scripts/generate_beauty.py \
  --preview --style "性感系" --emotion "性感" --seed 533224
```

## API 配置

```bash
export GEMINI_API_KEY="..."    # Google Imagen 4 Ultra 统一 Key（主力，兼容旧 GOOGLE_API_KEY）
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
- 自动风格固定为性感系/性感，旧 style/emotion 入参会被规范化
