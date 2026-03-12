# beauty-generator STATUS v9.0.0 — 2026-03-12

## 断点
- ��次完成：v9.0 大版本升级
  - 修复双重执行（移除 schedule cron，只保留 repository_dispatch + workflow_dispatch）
  - 删除冷风格（御姐系、知性系、冷艳系）
  - 新增4大贴近生活风格：国风系、职场系、生活场景系、邻家女孩系
  - 7日风格轮换：周一性感→周二甜美→周三国风→周四职场→周五居家→周��纯欲→周日邻家
  - prompt_library.json 新增国风/职场/居家/邻家穿搭、国风/居家/街头/职场场景
  - generate_beauty.py 新增4个风格的场景/穿搭/姿势映射逻辑
- 下一步：观察明天自动发布效果，确认新风格图片质量

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 触发：CF Worker 每天 UTC 11:30 → repository_dispatch → GitHub Actions
- API：Google Imagen 4 Ultra (主力) + 豆包 Seedream 4.5 (回退) + imgbb (图床)
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)

## 已知问题
- CF Worker 偶尔触发失败（3/10、3/11），但已移除 schedule 备用，失败时需手动 workflow_dispatch
