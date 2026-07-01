<!--
代码库地图模板。目录结构不直观时放在仓库根。
作用：让 Claude 动手探索之前先扫一眼，比瞎翻一通省大量 context。
保持极简——每个顶层目录一句话，别写成架构文档。
-->

# 代码库地图

> 每个顶层目录一句话。Claude 探索前先读这张图。

| 目录 | 一句话说明 |
|---|---|
| `src/` | <例：前端源码，Vue3 组件 + 页面 + 状态> |
| `server/` | <例：后端 API，Express 路由 + 业务逻辑> |
| `public/` | <例：静态资源，不含逻辑> |
| `<dir>/` | <说明> |

## 关键流程的起点（可选）
- <例：用户登录 → `src/pages/Login.vue` → `server/routes/auth.ts` → `server/services/auth.ts`>
- <例：日语分词 → `server/services/analyze.ts`（prompt 在 `analysis-prompt.md`）>

## 不要动的地方
- <例：`server/migrations/` 历史 migration 不可改，只能新增。>
