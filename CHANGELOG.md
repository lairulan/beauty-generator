# 版本历史

## v12.39.0 (2026-04-26) - Prompt 工程精简 + 代码瘦身 + 描述净化

### Prompt 优化（影响出图质量）
- **lifestyle prompt 从 13+ 段精简到 6 段**：合并 face / eyes / skin / lip 为单段 face-anchor；合并 body / outfit / fully-dressed 三处描述为一段。Imagen 长尾约束的衰减被有效抑制。
- **唇色 palette 多样化**：新增 `config/prompt_library.json:lip_color_palette`，每风格 3 选 1 fallback（natural lip-tone balm / pale baby-pink jelly balm / barely-tinted petal-pink gloss 等），同风格不再妆感雷同。
- **negative_prompts 拆分**：原 250+ token `anti_ai` 单串拆为 `anti_face / anti_body / anti_hair_makeup / anti_age_mood / anti_scene` 五个 ≤75 token 子串，`get_negative_prompt(pose_type, style)` 按场景动态拼接，避免被豆包静默截断。
- **生活场景系措辞净化**：移除 `sensual / magnetic / alluring`，统一为 `fresh / candid / lively`，调性更纯净。
- **`asian_focused` negative 改写**：去掉具体种族枚举（Indian / Latin / Southeast Asian / Eurasian），改为 `non-East-Asian features` 单条。
- **`_build_realism_clauses` 精简**：默认从 6 条缩到 3+1 条；生活场景系完全交给专用 prompt 不再叠加。

### 代码瘦身
- **删除 `generate_image_minimax` 死代码**（100+ 行，已不在 dispatch 链中）。
- **删除 `get_default_library` 内置硬编码 fallback**（392 行，与 `prompt_library.json` 易 drift）→ 改为 fail-fast。
- **风格枚举常量化**：`STYLE_LIFESTYLE / STYLE_SEXY / STYLE_OFFICE` 等顶层常量替换全文散字符串。
- **归档 backup JSON**：`prompt_library.v10.backup.json` 与 `v11.0.backup.json` 移到 `config/archive/`。
- **单文件总行数**：2070 → 1601（-23%）。

### 工程改进
- `--preview` 模式新增 token 估计输出（`[token≈xxx]`），便于发现长度逼近模型上限的 prompt。
- SKILL.md 补充：① Imagen 主路径不吃 negative 的事实；② FORCE_GOOGLE_ONLY 模式说明；③ 默认图床 imgbb 单点的提示。

### 验证
- 7 风格 preview 全部 exit=0
- 词数：34768 → 20321（-41.5%），lifestyle 单条 prompt 4731 → 2702 词
- 唇色 palette 多样化生效（同风格 3 张图已观察到 fallback 交替）
- API 调用链回归正常（Google primary → backup → 豆包，错误捕获明确）

---

## v12.1.0 (2026-04-23) - 年轻成熟女性 Prompt 与发布前整理

### Prompt 优化
- 年龄锚点统一为 24-27 岁 / mid-twenties / youthful softness，减少模型把“成熟”理解成偏年长的概率。
- 强化成熟女性感但保持写实：自然胸部轮廓、腰臀比例、锁骨/肩颈线、合身衣料和自信姿态，不走夸张或裸露方向。
- negative prompt 增加并保留 anti-flat-chest、anti-aging、anti-underage 与真实身体比例约束。
- 清理容易显老的备用词：将 `mature elegant face`、`crinkled laugh lines`、偏年长的 manager 表述改成年轻成人的精致/笑眼/职业感。

### 文档与元数据
- SKILL/README/STATUS/WORKFLOW 统一到 v12.1.0，并同步 Google Imagen 4 Ultra + 豆包 Seedream 4.5 架构。
- 定时发布说明保持为 Cloudflare Worker + GitHub Actions UTC 12:00 / 北京 20:00 兜底。
- 配置版本同步到 12.1.0，prompt library 标记为 12.1。

### 验证
- 已通过 JSON 配置解析、Python 编译检查和 prompt preview 检查。

---

## v10.1.0 (2026-04-08) - 内容质量升级

### 功能改进
- **差异化标题**：新增 `STYLE_TITLES` 映射，7种风格各有独立标题（如"今日写真 · 国风"），不再每篇都是"每日美女 | 周三"
- **风格专属开场文案**：新增 `_STYLE_OPENERS`，每种风格3条开场句按日期轮换，配合 `_EMOTION_CLOSERS` 组成2段开场内容
- **修复 emotion 映射缺失**：新增 `_EMOTION_ALIAS`，将 workflow 传入的 emotion 值（"挑逗"/"俏皮"/"温柔"等）正确映射到 `expr_phrases` key，解决开场白长期落入 fallback 的问题
- **图片配文升级**：`generate_caption_from_meta` 自动补第2句（从光影/穿搭维度），避免单句配文

### Bug 修复
- **dedupe exit 126 修复**：将 `RUNS_JSON` 改为写入临时文件再传给 python，规避 Argument list too long 问题（随运行记录积累 JSON 超出内核参数上限）



### 架构优化
- **配置驱动风格策略**: 风格策略从 if-elif 硬编码迁移到 `style_strategies.json`，支持无代码修改风格组合
- **集中常量管理**: API 端点、超时时间、模型名、图片参数统一由 `constants.json` 管理，一处修改全局生效
- **多图床容错机制**: imgbb + sm.ms 两级图床 + 指数退避重试，提升图片上传成功率

### Bug 修复
- **修复表情缺失**: 内置备用库补全"挑逗"/"纯欲"表情定义，避免 KeyError
- **修复姿势缺失**: 默认姿势池补全"写真"类型，确保所有姿势类型都有备用
- **移除冗余逻辑**: 移除 negative_prompt 的重复生成代码，避免冗余计算

### 代码质量
- **统一日志输出**: `generate_series()` 全部输出改用 `log()` 函数，避免 print/log 混用
- **版本号统一**: 所有文件版本号同步为 10.0.0
- **日志文件名更新**: v7-日期.log 更新为 v10-日期.log
- **imports 整理**: urllib.parse/base64 移到文件顶部，符合 PEP8 规范

---

## v8.0 (2026-03-11) - 全面优化

### 触发机制优化
- **解决双重触发浪费**: schedule 延后到 UTC 12:00 (北京 20:00)，给 CF Worker 30 分钟缓冲
- **风格轮换机制**: 按星期自动切换 6 种风格，告别每天「性感系+挑逗」的单调

### 代码质量
- **移除 curl 依赖**: `publish_wechat.py` 的 `make_request()` 改用原生 `urllib.request`
- **SSL 安全修复**: `generate_beauty.py` 优先使用系统 SSL 证书，仅在不可用时回退到不验证

### 日志优化
- **按月分文件**: `actions_runs.md` 改为 `actions_runs_YYYY-MM.md`，防止无限膨胀
- **风格记录**: 日志中记录每次使用的风格/情绪参数

### 文档同步
- **版本号统一**: SKILL.md / WORKFLOW.md / CHANGELOG.md 全部升级到 v8.0
- **架构更新**: WORKFLOW.md 反映真实的双引擎 (Google Imagen 4 Ultra + 豆包) 架构

---

## v5.1 (2026-01-24) 🔧

### Bug 修复
- **修复豆包回退模式**: URL 提取逻辑现在同时支持 imgbb 和 volces.com 两种图床
- **修复重复触发**: 禁用 GitHub Actions 原生 schedule，统一由 Cloudflare Workers 触发
- **增强去重检查**: 去重逻辑现在也检查 `workflow_dispatch` 事件，彻底避免重复发布

### 代码清理
- 修复 `generate_artistic.py` 中的乱码注释

---

## v5.0 (2026-01-16) 🎨

### 智能随机 Prompt 系统
- **丰富元素库**: 基于 Civitai/Stable Diffusion 社区最佳实践
- **随机组合**: 每次生成都从元素库随机选择，确保多样性
- **外部配置**: `config/prompt_library.json` 可自行扩展

### 严格东方美女
- **身份标识**: 添加 `East Asian Chinese young woman` 等关键词
- **负面提示词**: 排除 `Western face, Caucasian, European, blonde hair, blue eyes` 等

### 新增控制选项
- **6种人物风格**: 甜美系、清纯系、御姐系、知性系、冷艳系、性感系
- **4种场景类型**: 自然、城市、室内、特殊
- **6种穿搭风格**: 优雅、性感、清新、时尚、古典、运动
- **5种表情类型**: 微笑、性感、冷艳、忧郁、自信
- **3种光影类型**: 自然光、影棚、氛围

### 代码清理
- 删除旧版本备份文件
- 删除测试脚本
- 清理历史记录
- 修复 publish_wechat.py 兼容性（--theme → --style）

---

## v4.1.1 (2026-01-15) ✅

### 验证确认
- **定时任务验证**: 确认 GitHub Actions 定时任务正常运行

---

## v4.1.0 (2026-01-14) 🔒

### 安全性修复
- **移除硬编码 API key**: 所有文件中的 API key 已移除
- **环境变量验证**: 添加启动时的环境变量检查
- **文档安全**: 所有示例使用占位符而非真实 key

### 文档优化
- **CHANGELOG 独立**: 版本历史从 SKILL.md 分离
- **描述精简**: 优化 SKILL.md，移除冗余内容
- **部署文档**: 更新部署指南中的安全配置

### 部署优化
- **GitHub Actions**: 确认定时任务正常运行（每天 20:00）
- **本地任务清理**: 删除本地 launchd 任务，避免重复执行

---

## v4.0.1 ULTIMATE (2026-01-13) 🆕
- **移除本地存储**: 不再下载保存图片到本地
- **简化输出**: 只返回在线图片URL，直接供使用
- **GitHub Actions**: 支持完全免费的云端定时任务

## v4.0 ULTIMATE (2026-01-12)
- **场景氛围系统**: 15+ 种高级场景选择
- **情绪精准控制**: 8 种情绪表达
- **妆容风格系统**: 8 种专业妆容
- **艺术风格选择**: 8 种艺术风格
- **光影大师级控制**: 8 种专业光影方案
- **图生图技术**: 使用参考图确保人物一致性

## v3.0 ULTRA (2026-01-12)
- **Midjourney 风格 prompt**: 专业级 prompt 结构
- **顶级人物描述**: 更精准的特征刻画
- **增强质感描述**: 毛孔级细节

## v2.0 (2026-01-12)
- **图生图功能**: 使用参考图提升一致性
- **增强 prompt**: 更性感、更具吸引力

## v1.0 (2026-01-12)
- 初始版本
- 每日智能生成
- 人物一致性系统
- 每周主题轮换
