# Claude Skills — westarlsc

Personal collection of Claude Code skills. This is the primary/source-of-truth repo (company account). A personal backup copy is kept at [lxsWestar/claude-skills](https://github.com/lxsWestar/claude-skills), which pulls from here on a schedule.

## Skills

| Skill | Description |
|-------|-------------|
| [effort-estimator](./effort-estimator/) | (westarlsc) 工数估算（中日双语）。WBS/PERT/德尔菲/三维评估/NESMA/Planning Poker 等 10+ 方法，适配日本客户正式見積書格式 |
| [ocrskill](./ocrskill/) | (westarlsc) MinerU2.5-Pro OCR，用于本地 PDF/图片文档解析 |
| [consulting-advisor](./consulting-advisor/) | (westarlsc) 顶级咨询公司思考方法论。SCQA / MECE / 5 Whys / 金字塔原则 / 方案对比矩阵的 6 步分析流程，适用于内部说服与战略提案 |
| [consulting-proposal-docx](./consulting-proposal-docx/) | (westarlsc) 咨询风格 Word 提案书 / 稟議書生成器。JSON-driven，含执行摘要 SCQA 框、对比矩阵、Phase 路线图、审批申请等标准章节 |
| [harness-builder](./harness-builder/) | (westarlsc) 为代码仓库搭建、运行并定期纠偏 Claude Code「harness」：分层 CLAUDE.md、Hooks、Skills、MCP、权限边界与判断标准。支持搭建(build)、按 harness 作业(operate)、定期纠偏(audit) 三种模式 |
| [neat-freak](./neat-freak/) | (卡兹克) 会话收尾时对项目文档、Agent 记忆与工作区规范进行审查、同步和清理 |
| [write-natural-business-japanese](./write-natural-business-japanese/) | (westarlsc) 中文稿件转自然商务日语。三层方法：镜像文章结构、脱离原句法重新表达、扫描同形异义汉语词与职场黑话陷阱 |
| [grill-me](./grill-me/) | (Matt Pocock) 11 行拷问 skill。对已有方案沿决策树逐个追问：一次一问、每问附推荐答案、能查代码就先查代码，直到达成共识 |
| [grill-with-docs](./grill-with-docs/) | (Matt Pocock) grill-me 的文档增强版。拷问时对照领域词汇表 CONTEXT.md 与 ADR：磨尖术语、用代码核对口头理解、决策成形时就地更新文档 |
| [brainstorming](./brainstorming/) | (Jesse Vincent / obra · superpowers) 把模糊想法共创成设计文档：一次一问、发散 2-3 方案再收敛、HARD-GATE 未批准不写码、大需求先拆解，产出设计文档并提交 git。已适配独立使用 |
| [openspec-propose](./openspec-propose/) | (Fission-AI · OpenSpec) 按依赖顺序一步生成 proposal / specs / design / tasks 全套变更文档，schema 状态全绿才算完成。需要 openspec CLI |
| [goal-engineer](./goal-engineer/) | (卡兹克 leader × 向阳乔木 goal-meta 合并) 把模糊想法变成 agent 能独立长程执行的目标。两档同构：轻量档出 7 字段 /goal 指令（默认值优先、编号选择题），完整档走调研→提问→六节任务书→验收全流程，共享防作弊五死法、风险分级与暂停条件，附 lint 脚本 |
| [ten-step-learning](./ten-step-learning/) | (爱AI的大刘 · Daliu-Awesome-Skills) 十步学习法：五视角 STORM → 矛盾图谱 → 简报 → 自检 → 资源 → 阶梯 → 核心 20% → 题库 → 费曼 → 速查表，产出单文件学习 HTML。已重写优化：去除源仓库依赖、新增单步/交互教练模式、fragments + assemble.py 确定性组装 |
| [browser-control](./browser-control/) | (westarlsc 整合，含 BrowserAct 官方 skill v2.0.2) 浏览器操控统一入口。三通道路由：browser-act CLI（独立隔离浏览器，批量/验证码/人机协作）、chrome-devtools MCP（--autoConnect 连当前已登录 Chrome，DevTools 级调试）、Claude in Chrome 插件（claude --chrome 日常代办）。决策树选通道 + 冲突规则 + 跨通道安全总则。**安装后请删除旧的 browser-act 与 chrome-devtools 两个独立 skill，避免重复触发** |
| [voiceskill](./voiceskill/) | (westarlsc) 本地 Qwen3-TTS / Qwen3-ASR 多语言语音服务：参考音频声音克隆、自动语言检测及词/字级时间戳输出 |

## Usage

```bash
# Clone into ~/.claude/skills/
git clone https://github.com/li-xisheng/claude-skills.git ~/.claude/skills/
```

Or install individual skills:

```bash
cp -r consulting-advisor ~/.claude/skills/
```
