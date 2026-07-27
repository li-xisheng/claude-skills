# 通道 A：browser-act CLI（独立隔离浏览器）

Browser automation CLI for AI agents。运行**它自己**的完整浏览器引擎（与用户日常
Chrome 完全隔离）：导航与交互、数据提取与网络捕获、截图、表单自动化、多浏览器并行、
用户自配代理、人机协作。

**⚠️ 铁律：绝不直接凭记忆拼 `browser-act` 命令。任何操作前必须先执行下面的
`get-skills core` 拿到当前环境状态和完整指令集。**

## 何时用这条通道

- 无状态抓取 JS 渲染页面（比 WebFetch/curl 强的替代品，`extract` 甚至不用开会话）
- 多账号 / 多浏览器隔离并行操作
- 表单填写、文件上传、点击流程等自动化任务
- 需要验证码处理（stealth 浏览器 → `solve-captcha` → `remote-assist` 三级策略）
- 需要用户亲手操作一步（OAuth/2FA/生物识别）→ `remote-assist` 人机协作
- 捕获 XHR/fetch/HAR 网络响应
- **不适合**：要在用户当前的 Chrome 里做事——诊断/查看当前页面 → 通道 B（chrome-devtools MCP）；
  以用户身份做日常代办 → 通道 C（Claude in Chrome）

## 入口（每次都从这里开始）

```bash
browser-act get-skills core --skill-version 2.0.2   # 工作流、环境状态、可用浏览器、操作指令
```

**不要跳过这一步，不管命令看起来多简单；不要截断输出**——里面有浏览器选择规则、
安全约束和当前会话状态，`--help` 里没有这些。

之后按它返回的指令操作。要点速记（以 `get-skills` 实际输出为准）：

- 所有浏览器操作命令都要 `--session <name>`；环境里已有活跃会话就直接用，别重复 `browser open`
- 绝不关闭本次对话之外创建的 session（可能属于别的工作流）
- 浏览器 `desc` 是跨会话记忆，登录新站点/用途变化后主动 `browser update <id> --desc-append` 更新
- 命令失败时读错误输出——里面有原因和修法，不要盲目重试

## 安全与确认门（Confirmation Gate）

以下操作**必须先获得用户明确批准**：

- 首次安装（`uv tool install browser-act-cli --python 3.12`，从 PyPI 下载）
- 创建 / 删除浏览器
- 敏感操作：登录、表单提交、文件上传
- `chrome-direct` 类型（CDP 直连本机 Chrome）需要用户显式确认

数据隐私：cookies、登录态、页面内容、凭据、浏览器 profile 全部本地存储处理，
唯一出网数据是调用 `solve-captcha` 时的验证码挑战图片（不含 cookie 和页面内容）。

## 安装与元信息

| 项 | 值 |
|---|---|
| 安装 | `uv tool install browser-act-cli --python 3.12` |
| 运行时 | Python 3.12+，uv |
| 主页 | <https://www.browseract.com> |
| 原作者 | BrowserAct（官方 skill v2.0.2，本文件为其整合适配版） |
