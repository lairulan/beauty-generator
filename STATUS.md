# beauty-generator STATUS — 2026-04-23

## 当前状态
- 版本：v12.1.0，独立文生图仓库
- 主链路：Google Imagen 4 Ultra 生成；连接或生成失败时自动回退到豆包 Seedream 4.5
- 发布链路：`publish_wechat.py` 负责标题、开场文案、内容组装与公众号草稿箱发布
- 内容生成：年轻成熟女性 prompt + 风格专属标题 + 2段开场文案（STYLE_OPENERS + EMOTION_CLOSERS）+ 2句图片配文
- 自动去重：自动触发前先检查 GitHub Actions 当日成功记录，再回查远端 `workflow_logs`
- 测试模式：`--test` 只生成不发布，不要求 `WECHAT_API_KEY`
- HTTPS：默认严格校验证书，证书异常时仅在 `WECHAT_API_ALLOW_INSECURE_SSL` 允许下临时回退

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker daily-beauty / GitHub Actions schedule（UTC 12:00 / 北京时间 20:00）
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (兜底) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)

## 勿碰
- config/prompt_library.json 的基础结构（v12.1 已验证稳定）
- .github/workflows/ 的 concurrency 配置
- config/manual_prompts.json 不要与 prompt_library.json 合并
