# Beauty Generator V4.0 ULTIMATE - 开发归档

**开发日期**: 2026-01-12
**版本**: V4.0 ULTIMATE (Final)
**状态**: 已完成并归档

---

## 项目概述

专业写实摄影风格美女图像生成系统，支持精准的场景/情绪/妆容/光影控制，并自动发布到微信公众号。

---

## 核心功能

### 1. 图像生成系统
- **模型**: 豆包 Seedream (doubao-seedream-4-5-251128)
- **图生图技术**: 第2、3张图使用第1张作为参考，确保人物一致性
- **日期种子**: 使用 YYYYMMDD 作为随机种子，同一天人物固定，不同日期人物不同

### 2. V4.0 精准控制系统
| 控制项 | 选项数量 | 说明 |
|--------|----------|------|
| 场景 | 15+ | 雨夜、樱花雨、赛博朋克、咖啡厅等 |
| 情绪 | 8 | 挑逗、忧郁、神秘、开心、高冷、温柔、自信、俏皮 |
| 妆容 | 8 | 裸妆、韩妆、欧美妆、日妆、烟熏妆等 |
| 艺术风格 | 8 | 电影感、王家卫、韩剧、ins风等 |
| 光影 | 8 | 黄金时刻、蓝调时刻、霓虹灯光等 |

### 3. 智能配文系统
- **配文数量**: 100+ 条
- **生成方式**: 基于场景/情绪参数随机生成
- **不再受星期几限制**: 完全随机，确保多样性

### 4. 公众号发布
- **API**: 微绿流量宝 (https://wx.limyai.com/api/openapi)
- **目标**: 「三更愿」 (wx287cdb9d78a498aa)
- **格式**: 小绿书 (newspic)
- **定时**: 每天 21:00 自动发布

---

## 文件结构 (最终版)

```
beauty-generator/
├── SKILL.md                      # Claude Skill 触发配置
├── README.md                     # 用户文档
├── WORKFLOW.md                   # 工作流程详细说明
├── ARCHIVE_V4.0.md              # 本文件 - 开发归档
├── scripts/
│   ├── generate_beauty.py       # V4.0 主生成脚本
│   ├── publish_wechat.py        # 公众号发布脚本
│   ├── auto_publish.py          # 定时发布脚本
│   ├── test_image_persistence.py    # 图片持久性测试
│   └── test_caption_randomness.py   # 配文随机性测试
├── config/
│   └── api.json                 # API 配置
├── logs/                        # 运行日志
│   ├── auto_publish.log
│   ├── image_persistence_test.json
│   └── caption_test.json
└── output/
    ├── images/                  # 图片本地存储 (可选)
    └── history/                 # 历史记录
```

---

## 已删除文件 (清理后)

| 文件 | 原因 |
|------|------|
| `scripts/generate.py` | 基础版本，已被 generate_beauty.py 取代 |
| `scripts/smart_prompt.py` | 功能已集成到 generate_beauty.py |
| `templates/` | V4.0 内置所有模板，不再需要外部文件 |
| `config/daily_styles.json` | V4.0 内置主题配置 |

---

## 环境变量

```bash
# 豆包图像生成 API
export DOUBAO_API_KEY="your-doubao-api-key"

# 微绿流量宝 API（公众号发布）
export WECHAT_API_KEY="your-wechat-api-key"
```

---

## 人物一致性保证

### 同一天内
```python
daily_seed = int(date.today().strftime("%Y%m%d"))  # 如: 20260112
random.seed(daily_seed)
```
- 3张图使用相同种子 → 人物特征固定
- 配合图生图技术 → 确保同一个人

### 不同日期
- 日期不同 → 种子不同 → 人物完全不同
- 每周7天不同主题 → 风格多样性

---

## 已解决问题

### 1. API Key 格式
- **问题**: 尾部缺少字符
- **修复**: 补全为完整 UUID

### 2. Size 参数大小写
- **问题**: "2K" 不被识别
- **修复**: 改为小写 "2k"

### 3. SSL 证书
- **问题**: CERTIFICATE_VERIFY_FAILED
- **修复**: 使用 ssl._create_unverified_context()

### 4. 图片 URL 解析
- **问题**: 无法从输出中提取 URL
- **修复**: 更新正则表达式

### 5. "图片" 文字
- **问题**: 公众号文章显示多余 "图片" 文字
- **修复**: 使用空 alt text `![](url)`

### 6. 配文单调
- **问题**: 按星期几固定，每天相同
- **修复**: 100+ 条配文库，基于参数随机生成

---

## 待验证项目

### 图片持久性测试
- **发布时间**: 2026-01-12 10:56
- **检查时间**: 2026-01-13 11:56
- **目的**: 验证微信 CDN 是否在豆包 URL 过期后仍有效
- **命令**: `python3 ~/.claude/skills/beauty-generator/scripts/test_image_persistence.py --check`

---

## 使用命令

### 基础生成
```bash
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py --count 3
```

### 精准控制
```bash
python3 ~/.claude/skills/beauty-generator/scripts/generate_beauty.py \
  --scene "雨夜" --emotion "忧郁" --makeup "韩妆" --art-style "王家卫"
```

### 公众号发布
```bash
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py \
  --count 3 --scene "樱花雨" --emotion "温柔"
```

### 测试模式
```bash
python3 ~/.claude/skills/beauty-generator/scripts/publish_wechat.py --test
```

---

## 开发历程

1. **V1.0**: 基础美女生成 + 公众号发布
2. **V2.0**: 图生图技术，提升人物一致性
3. **V3.0**: 姿态多样化，极致特写/侧颜/全身
4. **V4.0 ULTIMATE**: 场景/情绪/妆容/光影精准控制系统 + 智能配文

---

## 技术栈

- **语言**: Python 3
- **图像生成**: 豆包 Seedream API
- **HTTP请求**: urllib.request + subprocess (curl)
- **定时任务**: macOS launchd
- **数据格式**: JSON

---

*归档完成 - 2026-01-12*
