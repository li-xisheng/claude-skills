---
name: harness-builder
description: >-
  为一个代码仓库搭建、运行并定期纠偏一整套 Claude Code「harness（外围工程体系）」：分层 CLAUDE.md、Hooks、
  Skills、Plugins、MCP、LSP、子 agent、权限边界，以及 Project Taste / 验收标准即代码 / 对抗性审查
  等「判断层」。当用户想给项目「搭一套 harness / 配 CLAUDE.md / 做 Agent 工程化 / 让 Claude Code
  在大代码库里更好用 / 把团队的隐性规范沉淀下来」，或抱怨「context 老爆、Claude 总找错文件、跨文件大改动
  改一半就崩、团队里只有我会用」，或想「定期体检 / 纠偏 harness、检查 CLAUDE.md 是不是过长 / 过期 / 被
  Goodhart 化、看看 harness 有没有偏离最佳实践」时，必须使用本技能。本技能有三种模式：搭建(build)、按 harness
  作业(operate)、定期纠偏(audit)。Use this skill whenever someone wants to set up, work by, or audit a
  Claude Code project "harness" — even if they don't say the word "harness".
---

# Harness Builder — 给项目搭建 / 运行 / 纠偏 Claude Code 工程体系

## 这个技能在解决什么问题

很多人评估 Claude Code 好不好用，第一反应是看模型（Sonnet 还是 Opus？要不要升 Max？）。但 Anthropic
官方的反直觉结论是 **「The harness matters as much as the model」——围绕模型搭的那套外壳，对最终效果的
影响和模型本身一样大。** 打个比方：模型是米其林大厨，harness 是你家的灶台、菜刀、调料架、抽油烟机。灶台不行，
再牛的厨师也炒不出锅气。

所以在大代码库里 **context 老爆、不是模型太小，是 harness 没搭好。** 这个技能就是把「搭 harness」这件
一次性但回报极高的工程，变成一套可执行、可复用、可定期纠偏的流程。

**harness 的本质（四篇资料综合）= 工具 + 知识 + 上下文管理 + 权限边界 + 判断标准。**
你不是在「开发」一个智能体，而是在「给一个本来就很聪明的智能体造一个好用的工作环境」。环境搭好，剩下的它自己会搞定。

---

## 三种模式：先判断用户要哪一种，不要默认从头搭

| 模式 | 触发信号 | 产出 |
|---|---|---|
| **A · 搭建 build** | 「给这个项目搭 harness」「配 CLAUDE.md」「让 Claude Code 在这个库里好用起来」「从零做 Agent 工程化」 | 一套落地的 harness 文件 + harness 清单 |
| **B · 作业 operate** | 「按这套 harness 帮我改 X」「这个跨服务的大改动怎么干」「帮我推进某个重构」 | 遵循 harness 规范完成具体开发任务 |
| **C · 纠偏 audit** | 「体检一下 harness」「CLAUDE.md 是不是过期/过长了」「最近 Claude 怎么用都上不去」「定期检查」 | 一份偏差报告 + 分优先级的修正动作 |

判断不了时，先问一句：**「你是想第一次搭一套（A），还是按已有的规范干活（B），还是给现有 harness 做体检纠偏（C）？」**
如果仓库里已经有 `.claude/` 和多个 `CLAUDE.md`，用户又说「优化 / 检查 / 怎么用不顺」，默认走 **C（纠偏）**。

> ⚠️ **本技能默认「Plan → 审批 → 落地」**：任何会写文件、改配置的动作，先把方案讲清楚让用户确认，再动手。
> 在一个已有的真实仓库里直接大改是危险的。除非用户明确说「全自动，别问我」。

---

## 心智模型：harness 的层次与搭建顺序

每一层都建立在前一层之上。**严格按这个顺序搭——顺序错了，后面的层就是在给噪音加噪音。**

```
第 0 层  侦察          先读懂这个仓库长什么样（agentic search 需要一个好起点）
─────────────────────  知识 / 上下文
第 1 层  CLAUDE.md     分层：根目录只放指针和关键的坑，子目录放模块细节
第 2 层  权限边界      .claude/settings.json 的 permissions.deny + .ignore + 每个子目录的测试/lint 命令
第 3 层  代码库地图    根目录一张 markdown 地图，列出每个顶层目录一句话说明
─────────────────────  自进化 / 按需知识 / 精确检索
第 4 层  Hooks         不只是防错，真正价值是让整套设置「自我进化」
第 5 层  Skills        按需加载（progressive disclosure），高频操作沉淀成 SOP
第 6 层  LSP           按符号搜索而非字符串 grep——多语言大库里「最高价值的投资之一」
第 7 层  子 agent / 会话拆分 / batch   隔离上下文，扛住跨大量文件的改动
─────────────────────  团队分发（最后才上）
第 8 层  Plugins / MCP 打包分发给团队 + 接入外部系统。基础没搭好就上 MCP，接进来的全是噪音
─────────────────────  判断层（贯穿全程，最难也最值钱）
判断层   Project Taste / 验收标准即代码 / 对抗性审查
```

> 全公司「最高 ROI 的三个动作」是：**CLAUDE.md 砍到 200 行以内 + 在子目录启动 Claude + 装 LSP。** 任何模式下，
> 这三件都应该最先确认。各层的「是什么 / 何时做 / 怎么做 / 例子」详见 [references/harness-layers.md](references/harness-layers.md)。

---

## 模式 A：搭建（Plan → 审批 → 落地）

### 步骤 0 · 侦察仓库（必做，给后面所有判断一个好起点）

跑侦察脚本，拿到一份结构化报告，而不是自己瞎翻烧 context：

```bash
python ~/.claude/skills/harness-builder/scripts/recon.py <repo_path>
```

它会输出：总规模 / 主要语言 / 顶层目录 / 是否 git / 是否 monorepo / 已有的 CLAUDE.md 及行数 /
已有的 `.claude/settings.json`、skills、hooks、plugins、MCP / 构建产物与生成目录。**把这份报告作为方案的依据。**

### 步骤 1 · 适配性判断（别给不合适的项目硬搭）

Claude Code 围绕「Git + 工程师为主 + 标准目录结构」这个最大公约数设计。先对照 [references/harness-layers.md](references/harness-layers.md)
里的「Q7 适配性清单」。如果命中**游戏引擎/大量二进制资源、非常规 VCS（Perforce/SVN/自研）、非工程师为主贡献**
这几类，**先如实告诉用户「这类项目 harness 适配成本高」**，再决定要不要继续、要做哪些定制。

### 步骤 2 · 产出分层方案（按搭建顺序，逐层写清「改什么、为什么」）

依据侦察报告，对照上面的层次表，产出一份方案，覆盖第 1–8 层 + 判断层中**这个项目当下真正需要的部分**。
不要一上来就堆满八层——小项目可能只需要第 1–3 层 + 一两个 skill。方案里每一层都要回答：

- 这一层对这个仓库具体要落什么文件 / 改什么配置？
- 为什么（解决哪个具体痛点）？
- 内容草稿（关键文件给出可审阅的初稿，模板见 `assets/templates/`）。

### 步骤 3 · 逐层落地（每一层一个审批门）

按顺序一层一层来，**每层先给用户看初稿，确认后再写**：

1. **CLAUDE.md**：根目录用 [assets/templates/CLAUDE.root.md](assets/templates/CLAUDE.root.md)，每个值得的子目录用
   [assets/templates/CLAUDE.subdir.md](assets/templates/CLAUDE.subdir.md)。**单文件 200 行以内**，根目录只放
   跨包通用约定 + 关键的坑 + 指针。写法与「删除测试」见 [references/claude-md-guide.md](references/claude-md-guide.md)。
2. **权限边界**：用 [assets/templates/settings.json](assets/templates/settings.json) 写 `permissions.deny`
   （生产数据库、密钥目录等）+ 排除生成物/构建产物/第三方代码；在每个子目录 CLAUDE.md 写清「这块用什么命令测、怎么 lint」。
3. **代码库地图**：目录结构不直观时，用 [assets/templates/codebase-map.md](assets/templates/codebase-map.md) 放在根目录。
4. **Hooks**：从 [assets/templates/hooks-examples.md](assets/templates/hooks-examples.md) 里挑——PostToolUse 自动
   格式化、Stop 自动反思并回写 CLAUDE.md、SessionStart 按子目录注入 context。**先挂能自进化的那一两个，别一次堆满。**
5. **Skills**：把「一天会做不止一次」的高频操作沉淀成 skill（可绑定到特定子目录路径）。怎么判断、怎么写见 [references/harness-layers.md](references/harness-layers.md) 的 Skills 节。
6. **LSP**：多语言或符号歧义高（C/C++/Java/PHP）时强烈建议。给出 `/plugin` 装哪个 + 装哪个语言服务器二进制的具体命令。
7. **判断层**：用 [assets/templates/project-taste.md](assets/templates/project-taste.md) 起一份 Project Taste；
   需要时引入验收标准即代码、对抗性审查。原理与边界见 [references/judgment-and-taste.md](references/judgment-and-taste.md)。
8. **Plugins / MCP**：**最后才上**。前面没打磨好就别接 MCP。

### 步骤 4 · 收尾

在仓库根写一份 `.claude/HARNESS.md`「harness 清单」：记录搭了哪些层、各层文件位置、为什么这么搭、下次纠偏该看什么、
建议的复审周期（3–6 个月）。这份清单是模式 C（纠偏）的入口。然后做一次自检：CLAUDE.md 是否都 ≤200 行？子目录能否独立测试/lint？地图是否和真实目录对得上？

---

## 模式 B：按 harness 作业

当 harness 已经搭好、用户要在它上面干一件具体的事，遵循以下要点（完整操作手册见 [references/operating-playbook.md](references/operating-playbook.md)）：

- **在子目录启动**，不要在仓库根。要改支付服务就 `cd services/payments` 再开工——context 立刻聚焦到一个领域。
- **复杂任务先 Plan 后写**：把功夫花在 plan 上，让 Claude「一发命中」地实现（Pour your effort into the plan）。
- **先派子 agent 探索、主 agent 留干净 context**：让子 agent 读几十个文件、只回传一份几百字 findings，再动手改。
- **跨大量文件的改动 = 拆成多个会话，不是写更长的 prompt**：会话1 出 plan、会话2/3 各实现一个模块，用 plan 文件做桥梁。
- **大规模迁移用 `/batch`**：派出几十个并行子 agent，各自在独立 git worktree 里跑、自测、开 PR。
- **权限用白名单而非 `--dangerously-skip-permissions`**：`/permissions` 预先放行常用安全命令，保留审计。

---

## 模式 C：纠偏（定期给 harness 做体检）

harness 不是「搭一次放着」的，模型在进化、代码在变，harness 会过期、会变长、会被指标带歪。纠偏流程：

### 步骤 1 · 跑体检脚本

```bash
python ~/.claude/skills/harness-builder/scripts/audit_harness.py <repo_path>
```

它会机械地查出：每个 CLAUDE.md 的行数（>200 标红）、CLAUDE.md 里引用但已不存在的文件/路径（漂移）、
harness 各层的有无清单。**机械能查的让脚本查，省下 context 做判断。**

### 步骤 2 · 对照纠偏清单逐项核对

打开 [references/audit-checklist.md](references/audit-checklist.md)，逐项过：CLAUDE.md 分层与瘦身、
权限与忽略、地图与真实目录、Hooks 是否在自进化、高频操作是否已沉淀为 skill、MCP 是否上早了、子目录测试命令是否齐。

### 步骤 3 · 判断层体检（最容易被忽略、也最危险）

对照 [references/judgment-and-taste.md](references/judgment-and-taste.md) 检查三件事：

- **Goodhart 化**：有没有把「覆盖率>85%」「行数<50」这种纯量化指标写成硬目标？这类规则会被 AI 钻空子刷数字。
  按「判断力光谱 S1–S5」给每条规则归档，量化指标（S2）只做参考、别当目标。
- **过度显形（不可能三角）**：是不是把战略方向、价值观底线、带疤痕的禁忌、审美争论这些**本该留白的东西也写死了**？
  这些是「刻意不刻」的，写死反而有害。
- **过期**：距上次完整复审是否超过 3–6 个月？有没有为旧模型弱点写的、现在已成枷锁的规则/hook/skill？

### 步骤 4 · 出纠偏报告 + 审批落地

产出一份分优先级（高/中/低）的偏差报告：每条写明「现状 → 问题 → 建议改动 → 为什么」。用户确认后，按模式 A
步骤 3 的审批门逐项落地。最后更新 `.claude/HARNESS.md` 的复审记录。

---

## 贯穿三种模式的红线

1. **CLAUDE.md 单文件 ≤200 行、分层加载、用「删除测试」狠删**：删掉这行 Claude 还会做对吗？会→删。
2. **渐进式披露**：能进 skill / 子目录 CLAUDE.md / reference 的，就别堆进每次都全量加载的根 CLAUDE.md。
3. **搭建顺序不能乱**：先 CLAUDE.md / skill 打磨好 → 再 plugin 打包 → 最后才上 MCP。
4. **按判断力光谱归档规则**：硬规则（Lint/类型）放 S1；语义验收放 S3；偏好放 S4/Project Taste；别把 S2 量化指标当目标。
5. **四样东西刻意不刻**：战略方向、价值观底线、带疤痕的禁忌、审美争论——留白本身是组织健康的信号。
6. **改动前先审批**：本技能默认 Plan → 审批 → 落地，尤其在真实仓库里。

---

## 参考文件索引

读 SKILL.md 不够时，按需深入：

- [references/harness-layers.md](references/harness-layers.md) — 每一层「是什么/何时做/怎么做/例子」+ Q7 适配性清单。**搭建时必读。**
- [references/claude-md-guide.md](references/claude-md-guide.md) — CLAUDE.md 写法：200 行规则、分层、删除测试、3–6 月复审、根/子目录模板讲解。
- [references/judgment-and-taste.md](references/judgment-and-taste.md) — 判断层：Project Taste、验收标准即代码、对抗性审查、Goodhart、不可能三角、判断力光谱 S1–S5、刻意不刻。**纠偏时必读。**
- [references/operating-playbook.md](references/operating-playbook.md) — 模式 B 完整手册：子目录启动、Plan Mode、子 agent、会话拆分、/batch、创始人工作流。
- [references/audit-checklist.md](references/audit-checklist.md) — 模式 C 的逐项纠偏清单（机械可查项 + 需判断项）。
- `scripts/recon.py` — 侦察仓库现状。`scripts/audit_harness.py` — 机械体检 harness。
- `assets/templates/` — 可直接套用的初稿：根/子目录 CLAUDE.md、代码库地图、Project Taste、settings.json、hooks 示例。
