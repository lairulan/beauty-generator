# beauty-generator STATUS v9.1.0 — 2026-03-14

## 断点
- 本次完成：v9.1 照片真实感大幅提升
  - 恢复 GitHub Actions schedule cron 兜底（UTC 12:00 = 北京 20:00）
  - prompt 去AI化改造：base_quality→真实相机描述、asian_identity 精简、enhancement→自然瑕疵、negative 新增反AI词、build_prompt 新增反AI锚点
  - 手动补发 3/13 + 3/14（新 prompt 首测）
- 下一步：观察今晚自动发布效果，对比新旧 prompt 图片真实感差异

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker UTC 11:30 → repository_dispatch + schedule cron UTC 12:00 兜底
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退) + imgbb (图床)
- 发布：三更熟公众号 (AppID: ${WECHAT_APP_ID})

## 已知问题
- CF Worker 偶尔触发失败（3/10、3/11、3/13），已恢复 schedule cron 兜底
- 新 prompt 效果待验证（3/14 首次测试运行中）

## 勿碰
- .github/workflows/daily-publish.yml 的 concurrency 配置
- scripts/publish_wechat.py 的微信发布逻辑
