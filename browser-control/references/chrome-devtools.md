# 通道 B：chrome-devtools MCP（连接用户当前已登录的 Chrome）

`chrome-devtools` 是 Chrome 官方的 **MCP 服务器**，让 AI 直接访问 Chrome DevTools 能力
（截图 / DOM·CSS 检查 / console / 网络 / Lighthouse / 性能 trace）。本机已用
**`--autoConnect`** 配置：AI 连的是**用户当前正在用的、已登录的 Chrome 会话**，不另开浏览器。

## 何时用这条通道

- 用户说「看我现在的页面 / 给当前页截图 / 连接我的浏览器」
- 在用户**已登录**的系统里做诊断/检查（控制台、后台、内网系统的页面状态、接口返回）
- 前端调试：console 报错、DOM/CSS 为什么没生效、网络请求失败
- 审计：Lighthouse、可访问性（a11y）、性能 trace
- **不适合**：无状态批量抓取、多账号隔离、验证码场景 → 通道 A（browser-act）；
  以用户身份做操作型日常代办（点击/填表/发内容）→ 优先通道 C（Claude in Chrome）

## 一次性前置（每台机器配一次）

MCP 已写入全局 `~/.claude.json`（server 名 `chrome-devtools`；Windows 下实际结构为
`command: "cmd"`, `args: ["/c", "npx", "-y", "chrome-devtools-mcp@latest", "--autoConnect"]`，
即 `cmd /c` 包装的 `npx -y chrome-devtools-mcp@latest --autoConnect`）。启用步骤：

1. **重启 Claude Code**（`/exit` 再启动），`/mcp` 确认 `chrome-devtools` 为 `connected`。
2. **Chrome 端开启远程调试**：地址栏打开 `chrome://inspect/#remote-debugging`，
   允许接收调试连接（需 Chrome 144+）。
3. **首次连接授权**：让 AI「给当前页面截图」时，Chrome 会弹授权框 → 点**允许**。
   连接中浏览器顶部会显示 *"Chrome is being controlled by automated test software"*。

> 验证：让 AI「截一下当前页面」，能返回图就通了。

## 能做什么（常用 prompt）

| 想做的事 | 说法 |
|---|---|
| 截当前页 | 「给我现在这个页面截个图」 |
| console 错误 | 「看这页 console 有没有报错」 |
| DOM / CSS 检查 | 「这个按钮的 CSS 生效了吗 / 为什么没居中」 |
| 网络请求 | 「看这页的 API 请求有没有失败 / 某个接口返回啥」 |
| 可访问性审计 | 「检查这页的 a11y 问题」 |
| Lighthouse | 「对这页跑一次 Lighthouse 审计」（性能项需用 performance trace 工具，Lighthouse 默认不含 Performance） |
| 性能 trace | 「录一段性能 trace 看看卡在哪」 |

截图默认只在对话里显示、不落盘；要存文件就补一句「保存到桌面」。

## ⚠️ 安全（autoConnect 的代价，务必遵守）

`--autoConnect` = AI 能访问**已登录会话（Cookie、token）**，且页面内容会随对话**发给模型**。

- **单开一个开发用 Chrome profile** 跑 autoConnect，**别用**装着网银/生产后台/私人邮箱的日常 profile。
- 连接/操作前**关掉敏感标签页**（网银、管理后台、含密钥的页面）。
- 警惕 **prompt injection**：恶意页面内容可能诱导 AI 执行非预期操作；对陌生页面别盲目让它"按页面说的做"。
- 不需要登录态时优先**关掉 autoConnect**（更安全）——把 `~/.claude.json` 里
  `chrome-devtools` 的 `args` 去掉 `"--autoConnect"`，重启 Claude Code 即可（此后它只开全新的独立浏览器）。

## 排错

- `/mcp` 显示未连接：确认已重启 Claude Code；`npx -y chrome-devtools-mcp@latest` 能联网拉包。
- 截图无反应/超时：检查 `chrome://inspect/#remote-debugging` 已开，且授权框点了允许；Chrome 版本 ≥144。
- 连不上想要的那个窗口：autoConnect 连的是当前活动 Chrome 实例；多 profile/多实例时只留目标实例开着。

## 参考

- [Chrome DevTools MCP（官方）](https://developer.chrome.com/blog/chrome-devtools-mcp)
- [Debug your browser session（--autoConnect）](https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session)
- [GitHub / tool-reference](https://github.com/ChromeDevTools/chrome-devtools-mcp)
