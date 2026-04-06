# beauty-generator STATUS — 2026-04-06

## 两个 Skill 架构

### beauty-generator（文生图）v9.1.0
- 引擎：Google Imagen 4 Ultra（主力）→ 豆包 Seedream 5.0 Lite（兜底）
- 工作流：daily-publish.yml
- CF Worker 事件：daily-beauty（UTC 12:00 = 北京 20:00）
- 模式：prompt_library 284 元素随机组合，完整 face/hair/skin/body 描述

### beauty-img2img（图生图）v1.0.0
- 引擎：豆包 Seedream 5.0 Lite + image 参考图
- 工作流：daily-publish-i2i.yml
- CF Worker 事件：daily-beauty-i2i（UTC 11:30 = 北京 19:30）
- 模式：参考图决定人物，prompt 只控制场景/服装/光线
- 参考图：ref_02.jpg → https://i.ibb.co/4RR0L47z/ref-02-beauty.jpg

## 本次改动
- 模型升级：doubao-seedream-4-5 → doubao-seedream-5-0-260128
- 图生图参数修正：image_url(字符串) → image(数组)
- Anti-AI 强化：negative prompt 新增 anti_ai + 真实感锚点
- Skill 拆分：文生图/图生图独立工作流和 SKILL 定义
- Google API key 更��，恢复文生图双引擎架构
- 豆包 API key 更新

## 待办
- CF Worker 部署（已修改 wrangler.toml + index.js，待登录后 deploy）

## 环境
- 仓库：https://github.com/lairulan/beauty-generator.git
- 发布：三更熟公众号 (AppID: wx287cdb9d78a498aa)
- 图床：imgbb

## 勿碰
- config/prompt_library.json 的基础结构（v10.0 已验证稳定）
- .github/workflows/ 的 concurrency 配置
- config/manual_prompts.json 不要与 prompt_library.json 合并
