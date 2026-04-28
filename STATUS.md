# beauty-generator STATUS — 2026-04-28

## 当前状态
- **版本：v12.40.0**（2026-04-28：LLM 文案永不重复 + 图文匹配）
- 主链路：Google Imagen 4 Ultra 生成；连接或生成失败时自动回退到豆包 Seedream 4.5
- 发布链路：`publish_wechat.py` 负责标题、开场文案、内容组装与公众号草稿箱发布
- **文案链路（v12.40 新增）**：Qwen-VL 看实际成图 → DeepSeek 写文（cinematic 调性，电影叙事 80-120字 3 段）→ 历史库去重（跨 skill 互查）→ 不通过重生
- 三层去重：开头 12 字精确 + 三元组 Jaccard 0.55 + VLM 关键词覆盖率 ≥2
- 自动去重：自动触发前先检查 GitHub Actions 当日成功记录，再回查远端 `workflow_logs`
- 测试模式：`--test` 只生成不发布，不要求 `WECHAT_API_KEY`

## 断点（2026-04-28）
- **本次完成**：v12.40.0 LLM 文案链路上线
  - 新增 `lib/llm_caption.py`：Qwen-VL → DeepSeek + 历史库 + 重生
  - `lib/captions.py::generate_smart_caption()` 增加 image_url 走 LLM 链路，失败回退模板
  - 新增 `generate_image_caption()` 让图片下方短文也走 LLM
  - `publish_wechat.py` 把开场文案生成移到图生成后；自动加载 `.env`
  - workflow YAML 注入 QWEN_API_KEY/DEEPSEEK_API_KEY/BEAUTY_CAPTION_TONE=cinematic
- **正式跑 2 次**（4-28）全部成功，文案完全不同且每篇都包含 ≥2 个 VLM 视觉关键词
- **下一步**：等今晚 20:00 schedule 自动跑，观察文案质量；本仓库的 Google Imagen key 仍受 "paid plan only" 限制，备用 key 工作正常

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
