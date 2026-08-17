# 通道 C：Claude in Chrome 插件（Claude Code 原生浏览器集成）

Anthropic 官方 Chrome 插件（商店名就叫 **"Claude"**，官方文档称 **"Claude in Chrome"**，
早期营销名 "Claude for Chrome"）。让 Claude Code **以用户身份**在用户真实、已登录的
Chrome 里干活：点击、输入、填表、导航、多标签页管理、截图、读 console、录 GIF。

> 与通道 B（chrome-devtools MCP）同样是"用用户当前的 Chrome + 登录态"，区别在深度与定位：
> B 是 Google 出品的 **DevTools 级深度调试**（性能 trace、网络瀑布、内存快照）；
> C 是 Anthropic 出品的**日常代办**（帮我在已登录的系统里点几下、填个表），
> 带产品级安全护栏（prompt injection 分类器、逐站点权限弹窗）。

## 何时用这条通道

- 用户要 Claude Code **以他的身份**做日常浏览器任务：已登录的 Gmail/Notion/CRM 后台里操作、填表、整理标签页
- 快速可视化核对（改完前端代码，在真实登录态下看一眼效果）
- 遇到登录页或 CAPTCHA 会**自动暂停等人工**——天然适合"人看着 AI 干"的交互式任务
- **不适合**：headless / 无人值守 / 批量并行（→ 通道 A）；性能与网络深度排障（→ 通道 B）

## 可用性判断（先查再用）

这条通道有**账号前提**，用前依次确认：

1. Chrome 装了「Claude」插件（v1.0.36+）。
2. Claude Code 以 **claude.ai 订阅账号**登录（Pro/Max/Team/Enterprise）。
   **用 API key 或 `claude setup-token` 登录时此功能被强制关闭**，传 `--chrome` 也没用。
   Bedrock / Google Cloud / Microsoft Foundry 渠道同样不支持。
3. 平台：Windows / macOS 原生支持（Chrome 与 Edge），**WSL 不支持**。

## 启用与使用

```bash
claude --chrome        # 启动时开启浏览器集成
```

- 会话内 `/chrome`：查看连接状态、管理权限、重连插件、切换浏览器；
  可选 "Enabled by default" 每次启动默认开启（代价：常驻占用 context）。
- VS Code 扩展里装了插件即自动可用，无需 flag。
- 功能以内置 MCP server **`claude-in-chrome`** + 同名 skill 暴露；
  工具列表：`/mcp` → `claude-in-chrome` → View tools（`read_page`、`find`、截图、点击、导航、标签页管理等）。
- 首次启用时 Claude Code 会注册 native messaging host。Windows 下的完整链路（排错时按此核对）：
  注册表 `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_code_browser_extension`
  → 值指向 manifest：`%APPDATA%\Claude Code\ChromeNativeHost\com.anthropic.claude_code_browser_extension.json`
  → 其 `path` 字段指向 `~/.claude/chrome/chrome-native-host.bat`（实际执行 `claude.exe --chrome-native-host`）。

## 安全（官方建议）

- **双层防护**：安全分类器扫描页面内容 + 执行前监控动作；但风险非零，prompt injection 仍需警惕。
- **敏感站点**：官方不建议在金融、法律、医疗类网站使用；插件会截取活跃标签页截图，
  **屏幕上可见的一切都会进入对话上下文**。
- **权限选择**：优先 "Allow this action"（仅本次）；"Always allow actions on this site"
  只给完全信任的站点。
- **硬限制**：不做股票交易、不绕过 CAPTCHA、不录入高度敏感数据。
- 与通道 B 共同的建议：单开一个开发用 Chrome profile，别用装着网银/私人邮箱的日常 profile。

## 本机现状（2026-08-17 实测，暂不可用）

**结论：通道 C 在本机被账号前提挡住，与插件安装无关。** 需要时优先回退通道 B。

已验证**正常**的部分（所以别再查这些）：
- 插件已装；native host 全链路完好——注册表项 → `%APPDATA%\Claude Code\ChromeNativeHost\*.json`
  → `~/.claude/chrome/chrome-native-host.bat` 三者齐全，`allowed_origins` 为官方扩展 ID
  `fcoeoabgfenejglbffodgkkbkcdhcgfn`。

**不满足**的两条（任一即导致不可用）：
1. 环境变量设了 `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`，即非 claude.ai 订阅登录
   → 按上文第 25 行，此功能被**强制关闭**，`--chrome` 也无效。
   （`~/.claude.json` 里虽有 `oauthAccount` 字段，但环境变量优先，实际不走订阅。）
2. Claude Code 版本 2.1.172 < 2.1.216 → 这种情况下**静默失败**，敲 `/chrome` 看不到明确报错，
   表现为 `claude-in-chrome` MCP 始终不出现在工具列表里。

**症状速判**：`/chrome` 无明显报错、但工具列表里没有 `claude-in-chrome` → 查这两条，别去查插件。

**恢复条件**：改用 claude.ai 订阅账号登录（并清掉上述两个环境变量）+ 升级 Claude Code 至 2.1.216+。

## 排错（Windows 常见）

- named pipe `EADDRINUSE` 冲突、native messaging host 崩溃：见官方 troubleshooting。
- 连不上：确认 Claude Code 是 claude.ai 账号登录（不是 API key）；`/chrome` 里重连。
- 旧版 Claude Code（<2.1.216）API key 登录时会**静默失败**（403 不报错）——升级后有明确提示。

## 参考（官方一手来源）

- [Claude Code × Chrome 集成文档](https://code.claude.com/docs/en/chrome)
- [Get started with Claude in Chrome](https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome)
- [Use Claude in Chrome safely](https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely)
- [Claude Code 工具优先级（computer-use.md）](https://code.claude.com/docs/en/computer-use.md)：
  官方默认顺序为 专用 MCP server > Bash > Claude in Chrome > computer use；
  用户显式指令或 skill 自身规则优先于该默认顺序。
