# beauty-generator STATUS v11.1.0 — 2026-03-22

## 断点
- 本次完成：v11.1.0 新增手动提示词模式，自动+手动双模式（2026-03-22 GitHub 同步）
  - generate_beauty.py: 新增 generate_custom() 函数 + --prompt 参数（1280行）
  - publish_wechat.py: 新增 --prompt / --caption-text 参数透传（517行）
  - workflow_dispatch 支持在 GitHub Actions 手动输入提示词触发
- 下一步：观察每日自动发布效果，如需指定主题可在 GitHub Actions 手动 dispatch

## 上一版本
- v11.0.0（2026-03-21）动态配文+标签系统，META 元数据协议
- v9.1（2026-03-14）去AI化 prompt 改造：真实相机描述+自然瑕疵+反AI锚点

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker UTC 11:30 → repository_dispatch + schedule cron UTC 12:00 兜底
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)

## 勿碰
- .github/workflows/daily-publish.yml 的 concurrency 配置
- scripts/publish_wechat.py 的微信发布逻辑
