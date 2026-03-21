# beauty-generator STATUS v11.0.0 — 2026-03-21

## 断点
- 本次完成：v10.0 → v11.0 大版本升级
  - 调研 15+ AI 提示词平台，采集 47,010 条美女/人像提示词
  - 尝试合并外部提示词库（v11.0/v11.1/v12.0），效果不理想后回退到 v10.0 基础
  - 新增动态配文系统：基于图片 META 元数据（场景/穿搭/表情/光影/艺术风格）自动生成配文
  - 新增动态标签系统：根据图片内容自动选择话题标签（最多6个）
  - generate_beauty.py 输出 META 行协议，publish_wechat.py 解析并动态生成
  - 5次测试验证：图片生成 5/5 成功，META 解析 5/5 正确，WeChat 发布 2/5 成功（3次 API 超时为基础设施问题）
- 下一步：观察每日自动发布效果，验证动态配文与图片的贴合度

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker UTC 11:30 → repository_dispatch + schedule cron UTC 12:00 兜底
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)
- 提示词库：prompt_library.json v10.0（284 元素，9 维度，1.14 万亿组合）

## 已知问题
- WeChat API (wx.limyai.com) 间歇性超时，SSL 证书过期需跳过验证
- CF Worker 偶尔触发失败，已有 schedule cron 兜底

## 勿碰
- .github/workflows/daily-publish.yml 的 concurrency 配置
- config/prompt_library.json 的基础结构（v10.0 已验证稳定）
