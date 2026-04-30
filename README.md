# Beauty Generator V12.44

> 双引擎艺术写真生成 + 性感/吸引力写真固定风格 + 公众号自动发布

## 快速开始

### 自然语言使用（推荐）

```
每日美女              → 生成1张今日主题
每日美女 2张          → 生成2张
发布美女              → 生成并发布到公众号（小绿书）
发布今日美女，5张      → 生成5张并发布
```

### 定时发布

**每天 20:00（北京时间）自动发布到「三更熟」公众号草稿箱**

- Cloudflare Worker 触发 `daily-beauty` → GitHub Actions `repository_dispatch`
- GitHub Actions 原生 `schedule` 作为同时间兜底：UTC 12:00 / 北京 20:00
- GitHub Actions `workflow_dispatch` 可手动补跑
- Workflow `concurrency` 防止同一分支并发重入
- 自动触发会先检查 GitHub Actions 当日成功记录，再回查远端月度日志，避免重复发布

## 双引擎架构

| 引擎 | 用途 | 说明 |
|------|------|------|
| Google Imagen 4 Ultra | 主力生成 | 高质量，生成后上传 imgbb 获取 URL；429 限流时会退避重试，并在当前运行内短暂跳过后续 Google 尝试 |
| 豆包 Seedream 4.5 | 自动回退 | Google 失败时自动切换，自带图片 URL |

## 自动风格（V12.44 固定）

自动文生图不再按星期轮换其他风格，统一走性感系/相近吸引力写真方向：

| 模式 | 风格 | 情绪/表情 | 说明 |
|------|------|-----------|------|
| 自动发布/自动生成 | 性感系 | 性感 | fully dressed 性感写真、都市/室内/特殊场景、吸引力但不露骨 |

## 精准控制

### 自动场景

自动模式只保留性感系适配场景：室内、城市、特殊。传入其他场景会被忽略并重新从这三类里选择。

### 情绪关键词

挑逗、性感、温柔、俏皮、自信、高冷、忧郁、纯欲、微笑、开心、神秘

### 文案增强关键词

`publish_wechat.py` 额外支持 `--makeup`、`--art-style`，用于生成更贴合的小绿书开场文案。

## 命令行使用

以下命令默认在仓库根目录执行：

```bash
# 生成图片
python3 scripts/generate_beauty.py --count 3

# 精准控制（style/emotion 会被自动规范到性感系）
python3 scripts/generate_beauty.py \
  --style "性感系" --scene "城市" --emotion "性感"

# 发布到公众号
python3 scripts/publish_wechat.py --count 1

# 测试模式（只生成不发布）
python3 scripts/publish_wechat.py \
  --test --count 1 --scene "城市" --emotion "性感" --caption "今晚这组偏都市感。"

# 查看所有选项
python3 scripts/generate_beauty.py --list-options
```

## 配置

### 环境变量

```bash
export GOOGLE_API_KEY="..."    # Google Imagen 4 Ultra（主力）
export DOUBAO_API_KEY="..."    # 豆包 Seedream 4.5（回退）
export IMGBB_API_KEY="..."     # imgbb 图片托管（Google 生成的图片需上传）
export WECHAT_API_KEY="..."    # 微信公众号 API
export WECHAT_API_ALLOW_INSECURE_SSL="1"  # 可选：证书异常时允许临时回退
```

`publish_wechat.py --test` 不需要 `WECHAT_API_KEY`，但仍需要生图相关环境变量。

## 文件结构

```
beauty-generator/
├── SKILL.md                    # 技能说明（Claude 触发用）
├── README.md                   # 本文件
├── WORKFLOW.md                 # 工作流程文档
├── CHANGELOG.md                # 版本历史
├── .github/workflows/
│   └── daily-publish.yml       # GitHub Actions 自动/手动发布
├── scripts/
│   ├── generate_beauty.py      # 双引擎图片生成（Google + 豆包）
│   └── publish_wechat.py       # 公众号发布脚本
├── config/
│   └── prompt_library.json     # Prompt 元素库
└── workflow_logs/              # 按月分文件的运行日志
    └── actions_runs_YYYY-MM.md
```

## 版本

**V12.44.0** - 2026-05-01

自动文生图和自动发布固定为性感系/相近吸引力写真风格，去掉按星期轮换到甜美、国风、职场、生活场景、清纯等其他风格的路径。

详见 [CHANGELOG.md](CHANGELOG.md)
