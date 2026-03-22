# beauty-generator STATUS v11.2.0 — 2026-03-22

## 断点
- 本次完成：v11.1.1 → v11.2.0 手动提示词库
  - 新增 config/manual_prompts.json 独立提示词库（与自动模式 prompt_library.json 完全隔离）
  - publish_wechat.py: 新增 load/save/list/get 四个提示词库函数
  - 手动模式发布成功后自动存档（prompt、配文、标签、图片URL、时间戳、自增ID）
  - 新增 --list-prompts 浏览 / --use-prompt <ID> 复用已保存提示词
  - SKILL.md 更新到 v11.2.0，文档同步
- 下一步：实际使用手动模式积累提示词；观察自动存档效果；考虑扩充关键词映射库

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker UTC 11:30 → repository_dispatch（自动模式）+ workflow_dispatch（手动模式）+ schedule cron UTC 12:00 兜底
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)
- 自动提示词库：config/prompt_library.json v10.0（284 元素，9 维度，1.14 万亿组合）
- 手动提示词库：config/manual_prompts.json（独立存储，发布成功自动存档）

## 已知问题
- WeChat API (wx.limyai.com) 间歇性超时，SSL 证书过期需跳过验证
- CF Worker 偶尔触发失败，已有 schedule cron 兜底

## 勿碰
- config/prompt_library.json 的基础结构（v10.0 已验证稳定）
- .github/workflows/daily-publish.yml 的 concurrency 和 workflow_dispatch inputs 配置
- config/manual_prompts.json 不要与 prompt_library.json 合并，两条线独立
