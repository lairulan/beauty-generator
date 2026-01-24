# Cloudflare Workers 定时触发检查清单

用于确认 `github-scheduler` 是否能稳定触发 `beauty-generator` 的 `repository_dispatch`。

## 1. Worker 与 Cron

- [ ] Worker 名称为 `github-scheduler`
- [ ] `wrangler.toml` 中包含 `0 12 * * *`（UTC 12:00 = 北京时间 20:00）
- [ ] Cloudflare 控制台中该 Worker 的 Cron Triggers 已启用

## 2. 触发配置

- [ ] `JOBS.daily-beauty` 指向仓库 `lairulan/beauty-generator`
- [ ] `event_type` 为 `daily-beauty`
- [ ] `cron_hour=12` 且 `cron_minute=0`

## 3. 权限与密钥

- [ ] Worker 绑定了 `GITHUB_TOKEN` 环境变量
- [ ] `GITHUB_TOKEN` 具备触发仓库 `repository_dispatch` 的权限
- [ ] 近期触发无 401/403 错误

## 4. 触发验证

- [ ] 访问 `https://<worker-domain>/trigger/daily-beauty` 可手动触发
- [ ] GitHub Actions 中能看到 `repository_dispatch` 事件
- [ ] 若 Actions 失败，能在日志中定位失败步骤

## 5. 运行去重与备份

- [ ] GitHub Actions `schedule` 已启用（备份触发）
- [ ] 去重逻辑正常，重复触发会标记为 `skipped`
- [ ] `workflow_logs/actions_runs.md` 能看到记录
