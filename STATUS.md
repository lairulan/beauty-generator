# beauty-generator STATUS — 2026-05-01

## 当前状态
- **版本：v12.44.0**（2026-05-01：自动文生图固定为性感系/相近吸引力写真风格）
- 主链路：Google Imagen 4 Ultra 生成；连接或生成失败时自动回退到豆包 Seedream 4.5
- 发布链路：`publish_wechat.py` 负责标题、开场文案、内容组装与公众号草稿箱发布
- 自动风格：`性感系 / 性感`，旧 `style / emotion` 入参会被规范化，不再轮换其他风格
- 自动场景：只保留 `室内 / 城市 / 特殊`，避免国风/职场/居家等旧场景把画面带回其他风格
- **文案链路（v12.40 新增）**：Qwen-VL 看实际成图 → DeepSeek 写文（cinematic 调性，电影叙事 80-120字 3 段）→ 历史库去重（跨 skill 互查）→ 不通过重生
- 三层去重：开头 12 字精确 + 三元组 Jaccard 0.55 + VLM 关键词覆盖率 ≥2
- 自动去重：自动触发前先检查 GitHub Actions 当日成功记录，再回查远端 `workflow_logs`
- 测试模式：`--test` 只生成不发布，不要求 `WECHAT_API_KEY`

## 断点（2026-05-01）
- **本次完成**：v12.44.0 自动文生图固定性感系/相近吸引力写真
  - workflow 固定 `STYLE=性感系`、`EMOTION=性感`
  - `generate_beauty.py` 自动模式规范 style/emotion，`ALL_STYLES` 与策略只开放性感系
  - 自动模式限制场景为室内/城市/特殊，旧场景入参会被忽略
  - `publish_wechat.py` 与 `lib/captions.py` 标题/开场只保留性感写真调性
  - `style_strategies.json` 只保留性感系策略，文档与配置版本同步
- **v12.43.0**（2026-04-28）：codex 审查后工程稳定性强化
  - Python 3.9 兼容（lib/captions.py 加 `from __future__ import annotations`，并补 json/datetime/CONFIG_DIR/clean_manual_prompt 缺失依赖）
  - SSL fail-closed：`_get_ssl_context()` 默认严格校验，仅 `BEAUTY_ALLOW_INSECURE_SSL=1` 显式开启时回退
  - 豆包 URLError 重试（与 5xx 一致的指数退避）
  - 历史库路径基于 `__file__` 推算 skill 根目录，不再硬编码 `~/beauty-generator`；邻居路径支持 `BEAUTY_PEER_HISTORY_FILE` env 覆盖
  - CI 把 `logs/caption_history.jsonl` 加入 git add；`.gitignore` 加例外
  - prompt_library 清理 `downcast/distant gaze/distant look/looking away into distance` 等弱冲突词
- **v12.42.0**（同日）：闭眼防御 — 锁死「双眼全开」硬约束
- **v12.41.0**（同日）：图启思考哲思短文 + LLM 标题 + plan B 排版（去 `>` 引用块）
- **v12.40.0**（同日）：LLM 文案永不重复 + 图文匹配（保留作 fallback 链路）
- **下一步**：下一次自动发布使用 v12.44 固定性感系策略（每天 3 次贴图，闭眼防御 + SSL 严格 + 重试稳健）

## V12.40 关键变更（2026-04-28）
- 新链路 `lib/llm_caption.py`（500+ 行）
- `lib/captions.py::generate_smart_caption()` 重构为优先 LLM 模式
- `publish_wechat.py` 加载 `.env` + 调用 LLM 短文生成器

## V12.39 关键变更（2026-04-26）
- Prompt 工程精简、negative 拆分、唇色多样化、代码瘦身（2070→1601 行）

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 定时：UTC 12:00 = 北京时间 20:00（GitHub Actions schedule，今天保留）
- API：Google Imagen 4 Ultra（主）+ 豆包 Seedream 4.5（兜底）+ imgbb（图床）+ Qwen-VL Plus（看图）+ DeepSeek（文案）
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)
- 历史库：`logs/caption_history.jsonl`（与 i2i 互查防撞文）

## 勿碰
- `config/prompt_library.json` 整体结构（V12.39 验证稳定）
- `.github/workflows/daily-publish.yml` 的 schedule + concurrency 配置
- `config/manual_prompts.json` 不要与 prompt_library.json 合并
- publish_wechat.py 解析 `META:` 行的格式
- LLM 文案 `_BANNED_WORDS`（已规避陈词滥调）

## 已知限制
- Google Imagen 主 key 受"Imagen 3 paid plans only"限制，依赖 backup key
- `FORCE_GOOGLE_ONLY=1` 模式下豆包不兜底（生产 daily-publish.yml 默认开启）
- LLM 文案历史库永久增长（每条 < 1KB，10 年也才几 MB，无需清理）
