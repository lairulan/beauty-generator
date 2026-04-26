# beauty-generator STATUS — 2026-04-26

## 当前状态
- 版本：**v12.39.0**，独立文生图仓库
- 主链路：Google Imagen 4 Ultra 生成；连接或生成失败时自动回退到豆包 Seedream 4.5
- 发布链路：`publish_wechat.py` 负责标题、开场文案、内容组装与公众号草稿箱发布
- 自动去重：自动触发前先检查 GitHub Actions 当日成功记录，再回查远端 `workflow_logs`
- 测试模式：`--test` 只生成不发布，不要求 `WECHAT_API_KEY`
- HTTPS：默认严格校验证书，证书异常时仅在 `WECHAT_API_ALLOW_INSECURE_SSL` 允许下临时回退

## V12.39 关键变更（2026-04-26）
- **Prompt 工程精简**：lifestyle prompt 13+ 段 → 6 段，词数 -41.5%，Imagen 长尾约束有效保留
- **Negative prompt 分类拆分**：5 个 ≤75 token 子串，按 pose/style 动态拼接，豆包不再被截断
- **唇色 palette 多样化**：每风格 3 选 1 fallback，同风格出图妆感不再雷同
- **生活场景系净化**：移除 sensual/magnetic/alluring 措辞
- **种族 negative 改写**：去掉具体种族枚举，改为 non-East-Asian features 单条
- **代码瘦身**：删 minimax 死代码 + 内置 fallback 库，2070 → 1601 行（-23%）
- **风格常量化**：STYLE_LIFESTYLE 等顶层常量替换散字符串
- **backup JSON 归档**：移到 `config/archive/`

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker daily-beauty / GitHub Actions schedule（UTC 12:00 / 北京时间 20:00）
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (兜底) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)

## 勿碰
- `config/prompt_library.json` 的整体结构（V12.39 已验证稳定，但 negative_prompts 已重命名 keys，回滚需注意）
- `.github/workflows/` 的 concurrency 配置
- `config/manual_prompts.json` 不要与 prompt_library.json 合并
- publish_wechat.py 解析 `META:scene|outfit|expression|lighting|art_style` 行的格式 — 修改 generate_beauty.py 输出时必须保留

## 已知限制
- Google Imagen 主路径不接收 negative_prompt（已在正向 prompt 前半段硬约束肤色/唇色/比例）
- 默认图床仅 imgbb 单点（如需冗余可在 `config/constants.json:image_hosts` 加 sm.ms）
- `FORCE_GOOGLE_ONLY=1` 模式下豆包不兜底（生产 daily-publish.yml 默认开启）
