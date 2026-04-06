# beauty-generator STATUS — 2026-04-06

## 断点
- 本次完成：v9.1.0 恢复文生图独立仓库 + Google Imagen 主力 + 豆包兜底
  - 从 beauty-img2img 拆分为独立仓库
  - 恢复 generate_image_google() + Google→豆包降级
  - prompt 修复 flawless 矛盾，清理图生图残留代码
  - Anti-AI negative prompt 强化
  - Google API key 更新（429 限频中，定时触发应正常）
- 下一步：观察 Google 限频是否在定时触发时恢复正常

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker daily-beauty（UTC 12:00 = 北京 20:00）
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 5.0 Lite (兜底) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)

## 勿碰
- config/prompt_library.json 的基础结构（v10.0 已验证稳定）
- .github/workflows/ 的 concurrency 配置
- config/manual_prompts.json 不要与 prompt_library.json 合并
