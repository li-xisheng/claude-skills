<!--
子目录 CLAUDE.md 模板。放「这个模块特有」的东西；通用约定留在根目录，别重复。
Claude 在子目录启动时会自动往上走树，把根 CLAUDE.md 也加载进来，所以这里只写增量。
同样 ≤200 行。
-->

# <模块名>（如 server / src / services/payments）

## 这个模块负责什么
<一两句职责边界：它管什么、不管什么。>

## 怎么测 / 怎么 lint（只测这个模块，别跑全量）
- 测试: `<命令，例：npm run test -- src/foo>`
- lint: `<命令>`
- 类型检查: `<命令>`
> 写清楚这一条能避免 Claude 改一个文件却跑整仓测试、几十分钟烧光 context。

## 本模块特有的约定 / 坑
- <例：所有 API 响应走统一信封 { success, data, error }。>
- <例：这里的金额单位是「分」，不是「元」。>

## 关键入口与数据流（可选，帮 Claude 找对起点）
- <例：请求入口 `server/index.ts` → 路由 `server/routes/*` → service → repository。>

## 本模块的高频操作（可考虑沉淀为 skill）
- <例：新增一个 API 端点的标准步骤……如果一天做不止一次，做成 skill。>
