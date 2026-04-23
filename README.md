# Beauty Generator V10.0

> 双引擎艺术写真生成 + 风格轮换 + 公众号自动发布

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
| 豆包 Seedream 5.0 Lite | 自动回退 | Google 失败时自动切换，自带图片 URL |

## 风格轮换（V8.0 新增）

按星期自动切换风格，避免审美疲劳：

| 星期 | 风格 | 情绪 |
|------|------|------|
| 周一 | 性感系 | 挑逗 |
| 周二 | 甜美系 | 俏皮 |
| 周三 | 国风系 | 温柔 |
| 周四 | 邻家女孩系 | 温柔 |
| 周五 | 职场系 | 自信 |
| 周六 | 生活场景系 | 微笑 |
| 周日 | 清纯系 | 性感 |

## 精准控制

### 场景 (15+ 种)

自然场景：樱花雨、雨夜、黄昏海滩、雪山、秋日森林
城市场景：rooftop夜景、地铁、咖啡厅、豪华酒店
艺术场景：艺术画廊、废弃工厂、玻璃花房、复古房间
特殊氛围：梦境、赛博朋克、古风、末日废土

### 情绪关键词

挑逗、性感、温柔、俏皮、自信、高冷、忧郁、纯欲、微笑、开心、神秘

### 文案增强关键词

`publish_wechat.py` 额外支持 `--makeup`、`--art-style`，用于生成更贴合的小绿书开场文案。

## 命令行使用

以下命令默认在仓库根目录执行：

```bash
# 生成图片
python3 scripts/generate_beauty.py --count 3

# 精准控制
python3 scripts/generate_beauty.py \
  --style "甜美系" --scene "自然" --emotion "俏皮"

# 发布到公众号
python3 scripts/publish_wechat.py --count 1

# 测试模式（只生成不发布）
python3 scripts/publish_wechat.py \
  --test --count 1 --scene "城市" --emotion "自信" --caption "今晚这组偏都市感。"

# 查看所有选项
python3 scripts/generate_beauty.py --list-options
```

## 配置

### 环境变量

```bash
export GOOGLE_API_KEY="..."    # Google Imagen 4 Ultra（主力）
export DOUBAO_API_KEY="..."    # 豆包 Seedream 5.0 Lite（回退）
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

**V10.0.0** - 2026-03-21

详见 [CHANGELOG.md](CHANGELOG.md)
