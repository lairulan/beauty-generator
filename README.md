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

**每天 19:30 自动发布到「三更熟」公众号草稿箱**

- Cloudflare Worker 触发（UTC 11:30 / 北京 19:30）
- GitHub Actions schedule 备用（UTC 12:00 / 北京 20:00）
- 去重机制确保每天只执行一次

## 双引擎架构

| 引擎 | 用途 | 说明 |
|------|------|------|
| Google Imagen 4 Ultra | 主力生成 | 高质量，生成后上传 imgbb 获取 URL |
| 豆包 Seedream 4.5 | 自动回退 | Google 失败时自动切换，自带图片 URL |

## 风格轮换（V8.0 新增）

按星期自动切换风格，避免审美疲劳：

| 星期 | 风格 | 情绪 |
|------|------|------|
| 周一 | 性感系 | 挑逗 |
| 周二 | 甜美系 | 俏皮 |
| 周三 | 知性系 | 自信 |
| 周四 | 冷艳系 | 神秘 |
| 周五 | 御姐系 | 高冷 |
| 周六 | 性感系 | 挑逗 |
| 周日 | 清纯系 | 温柔 |

## 精准控制

### 场景 (15+ 种)

自然场景：樱花雨、雨夜、黄昏海滩、雪山、秋日森林
城市场景：rooftop夜景、地铁、咖啡厅、豪华酒店
艺术场景：艺术画廊、废弃工厂、玻璃花房、复古房间
特殊氛围：梦境、赛博朋克、古风、末日废土

### 情绪 (8 种)

挑逗、忧郁、神秘、开心、高冷、温柔、自信、俏皮

### 妆容 (8 种)

裸妆、韩妆、欧美妆、日妆、烟熏妆、红唇妆、玻璃妆、创意妆

### 艺术风格 (8 种)

电影感、复古胶片、王家卫、韩剧、时尚杂志、ins风、暗调、清新日系

### 光影 (8 种)

黄金时刻、蓝调时刻、窗边自然光、影棚柔光、侧光戏剧、轮廓光、顶光神圣、霓虹灯光

## 命令行使用

```bash
# 生成图片
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3

# 精准控制
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py \
  --scene "雨夜" --emotion "挑逗" --makeup "韩妆" --art-style "王家卫" --lighting "蓝调时刻"

# 发布到公众号
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --count 1

# 测试模式（只生成不发布）
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test --count 1

# 查看所有选项
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --list-options
```

## 配置

### 环境变量

```bash
export GOOGLE_API_KEY="..."    # Google Imagen 4 Ultra（主力）
export DOUBAO_API_KEY="..."    # 豆包 Seedream 4.5（回退）
export IMGBB_API_KEY="..."     # imgbb 图片托管（Google 生成的图片需上传）
export WECHAT_API_KEY="..."    # 微信公众号 API
```

## 文件结构

```
beauty-generator/
├── SKILL.md                    # 技能说明（Claude 触发用）
├── README.md                   # 本文件
├── WORKFLOW.md                 # 工作流程文档
├── CHANGELOG.md                # 版本历史
├── .github/workflows/
│   └── daily-publish.yml       # GitHub Actions 定时发布
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
