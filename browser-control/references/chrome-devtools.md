# 通道 B：chrome-devtools MCP（连接用户当前已登录的 Chrome）

`chrome-devtools` 是 Chrome 官方的 **MCP 服务器**，让 AI 直接访问 Chrome DevTools 能力
（截图 / DOM·CSS 检查 / console / 网络 / Lighthouse / 性能 trace）。本机已用
**`--autoConnect`** 配置：AI 连的是**用户当前正在用的、已登录的 Chrome 会话**，不另开浏览器。

## 何时用这条通道

- 用户说「看我现在的页面 / 给当前页截图 / 连接我的浏览器」
- 在用户**已登录**的系统里做诊断/检查（控制台、后台、内网系统的页面状态、接口返回）
- 前端调试：console 报错、DOM/CSS 为什么没生效、网络请求失败
- 审计：Lighthouse、可访问性（a11y）、性能 trace
- **不适合**：不该沾用户登录态的抓取、批量并行、干净环境验证 → 通道 A（同一个包换
  `--isolated`，见 [isolated-browser.md](isolated-browser.md)）；
  以用户身份做操作型日常代办（点击/填表/发内容）→ 优先通道 C（Claude in Chrome）

## 一次性前置（每台机器配一次）

MCP 写在 `~/.claude.json`（server 名 `chrome-devtools`）：

```json
{"command":"npx","args":["chrome-devtools-mcp@latest","--channel=stable","--autoConnect"]}
```

> **`--autoConnect` 必须搭配 `--channel` 或 `--userDataDir`，单独给不生效。**
> 源码 `build/src/browser.js` 的分支条件是 `else if (channel || options.userDataDir)`；
> 两者都缺时会掉进默认 `browserURL = http://127.0.0.1:9222` 分支，去请求 `/json/version`。
> 而 Chrome 144+ 的新版远程调试**端口是随机的**（写在 profile 目录的 `DevToolsActivePort`
> 文件里，每次启动都变）且**不再暴露 `/json/version`**（实测 404），于是必然连不上，
> 报错还是含混的 `Could not connect to Chrome. Check if Chrome is running.`
> 官方博客示例写的是 `--channel=beta`，那是 M144 未进稳定版时的写法；稳定版用 `stable`。

启用步骤：

1. **重启 Claude Code**（`/exit` 再启动），`/mcp` 确认 `chrome-devtools` 为 `connected`。
2. **Chrome 端开启远程调试**：地址栏打开 `chrome://inspect/#remote-debugging`，
   允许接收调试连接（需 Chrome 144+）。**注意 `autoConnect` 不会替你启动 Chrome**，
   Chrome 必须已在运行。
3. **首次连接授权**：让 AI「给当前页面截图」时，Chrome 会弹授权框 → 点**允许**。
   连接中浏览器顶部会显示 *"Chrome is being controlled by automated test software"*。

> 验证：让 AI「截一下当前页面」，能返回图就通了。

## 降级链（连不上时按顺序往下退）

四档都在 Windows + Chrome 151 + mcp v1.7.0 上实测通过。改 `~/.claude.json` 里
`chrome-devtools` 的 `args`，改完**重启 Claude Code** 生效。

| 档 | args | 登录态 | 适用 |
|---|---|---|---|
| **1（默认）** | `--channel=stable --autoConnect` | ✅ 复用 | 首选。无机器专属路径，可移植 |
| **2** | `--userDataDir <profile 绝对路径> --autoConnect` | ✅ 复用 | 第1档找不到 profile，或用非默认/多 profile。路径即 `chrome://version` 的「个人资料路径」去掉尾部 `\Default` |
| **3** | `--browserUrl http://127.0.0.1:9222` | ✅ 复用 | 前两档都失败。需**手动**以 `chrome.exe --remote-debugging-port=9222` 启动 Chrome（得先完全退出，托盘也退干净），走的是老式固定端口握手 |
| **4** | `--isolated`（可加 `--headless`） | ❌ 无 | 兜底。MCP 自开全新隔离实例，与用户 Chrome 无关。做无状态诊断/抓取仍可用；需登录的任务改走通道 C。**注意这一档本质上已经是通道 A**，长期要用就别改 B 的配置，另配一个 `chrome-isolated` 条目（见 [isolated-browser.md](isolated-browser.md)） |

**命令行直接验证某一档**（不必改配置、不必重启）：

```bash
(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
 echo '{"jsonrpc":"2.0","method":"notifications/initialized"}'
 sleep 3
 echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_pages","arguments":{}}}'
 sleep 20) | timeout 45 npx -y chrome-devtools-mcp@latest --channel=stable --autoConnect 2>/dev/null | tail -c 800
```

返回里出现**用户真实标签页**即该档可用；只有 `about:blank` 说明连的是新实例（第4档行为）。

### 换机器时

第1档不含机器专属信息，通常直接可用。只有退到第2档才需要改路径（内含用户名）。
若用 Edge：`--channel` 不适用，走第2档指向 Edge 的 profile 目录。

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

- **报 `Could not connect to Chrome. Check if Chrome is running.`（但 Chrome 明明开着）**：
  典型症状是 `args` 里只有 `--autoConnect`。按上文补 `--channel=stable`，重启 Claude Code。
  自查：`netstat -ano | findstr :9222` 无输出 + profile 目录下 `DevToolsActivePort` 里是别的端口
  → 就是这个问题（说明 Chrome 用的是新版随机端口机制，而 MCP 在敲 9222）。
- **`args` 里是 `--wsEndpoint ws://127.0.0.1:<port>/devtools/browser/<GUID>`**：这是**一次性**的。
  GUID 每次 Chrome 启动都变，端口在 Chrome 144+ 也是随机的，所以这份配置只在写下它的那次
  Chrome 会话里有效，重启 Chrome 后必然连不上。当场调试可以这么用，**别留在 `~/.claude.json` 里**——
  长期配置回到第 1 档 `--channel=stable --autoConnect`。
- `/mcp` 显示未连接：确认已重启 Claude Code；`npx -y chrome-devtools-mcp@latest` 能联网拉包。
  另外检查 `args` 首项是否被误写成 `cmd` 之类的包装（应为 `command: "npx"`）。
- 截图无反应/超时：检查 `chrome://inspect/#remote-debugging` 已开，且授权框点了允许；Chrome 版本 ≥144。
- 连不上想要的那个窗口：autoConnect 连的是当前活动 Chrome 实例；多 profile/多实例时只留目标实例开着。
- **`list_pages` 只返回 `about:blank`**：连的是新开的隔离实例而非用户 Chrome。检查是否误用了
  `--isolated`，或 remote debugging 开关没开导致回退。

## 参考

- [Chrome DevTools MCP（官方）](https://developer.chrome.com/blog/chrome-devtools-mcp)
- [Debug your browser session（--autoConnect）](https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session)
- [GitHub / tool-reference](https://github.com/ChromeDevTools/chrome-devtools-mcp)
