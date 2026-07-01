# 逐层详解 — 搭建 harness 时的必读参考

这篇是搭建（模式 A）时按需深入的「逐层手册」。SKILL.md 给了总纲和搭建顺序，这里把**每一层讲透、给具体文件和命令、给例子、列常见错误**。

## 目录

- [先回到本质：harness 是什么](#先回到本质harness-是什么)
- [层次表与搭建顺序](#层次表与搭建顺序)
- [第 0 层 · 侦察](#第-0-层--侦察)
- [第 1 层 · CLAUDE.md](#第-1-层--claudemd)
- [第 2 层 · 权限边界](#第-2-层--权限边界)
- [第 3 层 · 代码库地图](#第-3-层--代码库地图)
- [第 4 层 · Hooks](#第-4-层--hooks)
- [第 5 层 · Skills](#第-5-层--skills)
- [第 6 层 · LSP](#第-6-层--lsp)
- [第 7 层 · 子 agent / 会话拆分 / batch](#第-7-层--子-agent--会话拆分--batch)
- [第 8 层 · Plugins / MCP](#第-8-层--plugins--mcp)
- [Q7 适配性清单](#q7-适配性清单)
- [最高 ROI 的三件事](#最高-roi-的三件事)

---

## 先回到本质：harness 是什么

**harness = 工具 + 知识 + 上下文管理 + 权限边界 + 判断标准。** 你不是在「开发」一个智能体——模型本来就很聪明——你是在**给一个聪明的智能体造一个好用的工作环境**。模型是司机，harness 是车；你不去教司机怎么开，你去把车造好。这也是为什么官方说 **The harness matters as much as the model**：同一个 Opus，放进一辆好车和一辆烂车里，跑出来的结果天差地别。

把上面五个词映射到下面的层：**知识**靠侦察（第 0 层）和 CLAUDE.md（第 1 层）+ 地图（第 3 层）；**权限边界**是第 2 层；**上下文管理**靠 Hooks（第 4 层）、Skills 的 progressive disclosure（第 5 层）、LSP 的精确检索（第 6 层）、子 agent 与会话拆分（第 7 层）；**工具**的分发与外接靠 Plugins / MCP（第 8 层）；**判断标准**是贯穿全程的判断层。所谓「context 老爆」，绝大多数时候不是模型太小，而是这几层没搭好。

---

## 层次表与搭建顺序

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
─────────────────────  判断层（贯穿全程）
判断层   Project Taste / 验收标准即代码 / 对抗性审查（见 references/judgment-and-taste.md）
```

下面逐层展开。

---

## 第 0 层 · 侦察

### 是什么

在动任何文件之前，先把仓库看懂：规模、语言、目录、是不是 git、是不是 monorepo、已有的 CLAUDE.md / settings / skills / hooks、构建产物和生成目录在哪。这一层的产物是**知识**，给后面每一层的判断一个事实基础。

为什么这层这么关键，要从 Claude Code 的检索方式说起。Claude Code **不用 embedding / 向量库**，它用的是 grep + 读文件 + 列目录，官方叫 **agentic search**——像一个真实的工程师那样工作：`ls` 根目录 → 进 `auth/` → grep "login" → 读 `middleware.ts`、`session.ts`，每读一个文件决定下一步读哪个，循环往复。这种方式的代价是一句话：**it relies heavily on a good starting context**。没有一个清晰的起点，Claude 就会到处乱翻、烧 context 去重建仓库结构。**第 0 层到第 3 层存在的全部意义，就是给 agentic search 一个好起点。**

为什么是 agentic search 而不是 RAG，有三个理由，搭建时要能讲给用户听：

1. **索引会过期。** 一个千人团队一天提交几百次，embedding 流水线根本追不上；它会返回两周前、早已被改名的函数。Claude 拿着过期信息推理 → 改崩。
2. **冷启动几乎为零。** RAG 给一个百万行的库建索引要十几分钟起步；agentic search 是「打开就能用」（open and go）。
3. **精确匹配向量干不了。** 你要 `getUserById`，向量会返回 `getUserByName` / `getUserByEmail` / `fetchUserInfo`——「相似」不等于「相等」，代码里你要的往往是后者。

### 何时该搭

**每次搭建的第一步，无条件做。** 哪怕是个小仓库，也先跑一遍侦察脚本拿事实，而不是凭印象。

### 怎么搭

跑侦察脚本，拿结构化报告，别自己瞎翻烧 context：

```bash
python ~/.claude/skills/harness-builder/scripts/recon.py <repo_path>
```

它输出：总规模 / 主要语言 / 顶层目录 / 是否 git / 是否 monorepo / 已有的 CLAUDE.md 及行数 / 已有的 `.claude/settings.json`、skills、hooks、plugins、MCP / 构建产物与生成目录。**把这份报告当作整套方案的依据。**

### 例子

侦察报告显示「主要语言 C++ + Python，12 个顶层目录，无任何 CLAUDE.md，`node_modules/` 和 `build/` 各几十万文件」——你立刻就知道：要装 LSP（多语言、C++ 符号歧义高）、要在第 2 层把 `build/` 排掉、要从零写分层 CLAUDE.md、目录多到要画地图。这些判断都来自报告，而不是来自你翻了二十分钟。

### 常见错误

- **跳过侦察直接写 CLAUDE.md**：你会漏掉生成目录、误判语言、把不存在的目录写进地图。
- **用 Claude 自己去「探索一遍」代替脚本**：那正是在烧 context 重建结构——这层的目的恰恰是避免它。
- **侦察完不沉淀**：报告看完就忘，后面每层又从头判断。把报告留在手边，贯穿整个搭建。

---

## 第 1 层 · CLAUDE.md

### 是什么

CLAUDE.md 是每次会话**全量加载**进 context 的知识文件。正因为全量加载，它的纪律极其严格：**单文件 200 行以内、分层、根目录只放指针和关键的坑**。超过约 200 行后，Claude「看不见」指令的概率会肉眼可见地上升——长文件在偷走它的工作空间。

分层的意思是：根目录 CLAUDE.md 只放**跨包通用约定 + 关键 gotcha + 指针**（「别碰生产库」「PR 前先 lint」），每个子目录有自己的 CLAUDE.md 放模块细节；Claude 会**沿目录树向上**把沿途每个 CLAUDE.md 都加载进来。

### 何时该搭

**第 0 层之后立刻搭，这是 harness 的地基。** 没有 CLAUDE.md，后面所有层都缺一个挂载点。

### 怎么搭

- 根目录套 `assets/templates/CLAUDE.root.md`，每个值得的子目录套 `assets/templates/CLAUDE.subdir.md`。
- 守住 200 行红线，用「删除测试」狠删：**删掉这行，Claude 还会做对吗？** 会（常识 / 代码里已有）→ 删；不会才留。

### 例子

根目录 CLAUDE.md 里出现「函数要写注释」——删，这是常识，删了 Claude 照样写；出现「本仓库的迁移脚本必须先在 `migrations/staging` 跑过才能进 prod，否则会锁表」——留，这是删了就会出事的坑。

### 常见错误

- **把所有规范堆进根 CLAUDE.md**：很快破 200 行，且子目录细节变成全局噪音。
- **Claude 反复犯同一个错就急着加规则**：先看 CLAUDE.md 是不是已经太长、把规则淹了——加规则可能让情况更糟。

> CLAUDE.md 这层只点要害。完整写法（200 行原理、分层、删除测试、3–6 月复审、根/子目录模板逐段讲解）见 `references/claude-md-guide.md`。

---

## 第 2 层 · 权限边界

### 是什么

权限边界回答两个问题：**哪些操作绝对不许做**（生产库、密钥），**哪些文件根本不该进 Claude 的视野**（生成物、构建产物、第三方代码）。再加一个常被忽略但极费 context 的点：**每个子目录里「怎么测、怎么 lint」必须写清楚**。

为什么测试命令属于权限边界这层？因为如果不写清，Claude 改了一个 `payments` 文件，会去跑**全量测试套件**——几十分钟、把 context 烧光。每个子目录 CLAUDE.md 写明「只测这块用什么命令」，是省 context 的关键一刀。

### 何时该搭

**写完 CLAUDE.md 紧接着搭。** 尤其是仓库里有生产配置、密钥目录、或巨大的 `node_modules/` / `build/` 时，越早排掉越省事。

### 怎么搭

- 用 `assets/templates/settings.json` 写 `.claude/settings.json` 的 `permissions.deny`：把生产数据库、密钥/凭证目录等明确拒掉。
- 用 `.ignore` 风格规则 + `permissions` 排除**生成物、构建产物、第三方代码**（`dist/`、`build/`、`node_modules/`、`vendor/`、自动生成的 `*.pb.go` 等）。
- 把这些 deny / 排除规则**提交到 git 的 `.claude/settings.json`**，让整个团队自动共享同一套边界。
- 在每个子目录 CLAUDE.md 里写明「这块用什么命令测、怎么 lint」。

### 例子

`services/payments/CLAUDE.md` 里写：「测试：`pytest services/payments -q`；lint：`ruff check services/payments`。不要跑根目录的 `make test`，那会跑全 12 个服务。」——这一句话可能就省下一次几十分钟的全量测试。

`settings.json` 里 `permissions.deny` 放上对生产连接串文件、`secrets/` 目录的拒绝，Claude 就不会在某次「帮我看看配置」时意外读到或改到它们。

### 常见错误

- **不排除生成物**：Claude grep 一个符号，`node_modules/` 里命中三千条，全在烧 context。
- **deny 规则只写在本地、不进 git**：团队里别人没有这层保护，边界形同虚设。
- **忘了写子目录测试命令**：这是「改一个文件却跑全量测试」的根因，单独拎出来检查。

> settings.json 的写法见 `assets/templates/settings.json`，更多 hook/权限片段见 `assets/templates/hooks-examples.md`。

---

## 第 3 层 · 代码库地图

### 是什么

根目录的一张 markdown 地图：**每个顶层目录一句话说明它是干什么的**。Claude 在动手探索前先扫一眼这张地图，就知道该往哪走，而不是盲目遍历。它是给 agentic search 的「好起点」里最便宜、最高效的一块。

### 何时该搭

**目录结构不直观时搭。** 如果顶层目录名一眼就知道是干嘛的（`src/ tests/ docs/`），可以不画；一旦是 `core/ engine/ pipeline/ adapters/ legacy/` 这种外人看不懂的，就值得画。侦察报告里顶层目录数量多、命名不自解释，就是信号。

### 怎么搭

用 `assets/templates/codebase-map.md` 放在仓库根，照着真实顶层目录逐行填一句话说明。

### 例子

```
# Codebase Map
- services/      各微服务，按业务域分目录（payments / auth / catalog ...）
- packages/      跨服务共享的库（日志、配置、鉴权中间件）
- platform/      基础设施代码：部署、CI、可观测性
- legacy/        正在退役的老单体，新代码不要往这加
- tools/         一次性脚本和内部 CLI
```

有了这张表，Claude 接到「加个新支付回调」时直接进 `services/payments`，而不会先去 `legacy/` 里翻半天。

### 常见错误

- **地图和真实目录对不上**：目录改了名、地图没更新，反而把 Claude 带偏——这是纠偏（模式 C）要重点查的漂移项。
- **写成长篇说明**：地图的价值在「一句话」，每个目录写成一段就又变成噪音了。

---

## 第 4 层 · Hooks

### 是什么

Hooks 是在特定事件点（「编辑文件后」「会话开始前」「工具调用前」）自动运行的脚本。多数人对 hook 的理解停在**防错**（自动 lint / format，防 Claude 写错）。但它真正的、也是更高阶的价值是：**让整套 harness 自我进化**——不只是堵漏，而是让设置随使用越变越好。

区分两类用途，搭建时要想清楚你挂的是哪一类：

- **防错类**：PostToolUse 自动格式化 Claude 写的代码，抹掉那约 10% 的格式遗漏，免得 CI 挂。
- **自进化类**（更值钱）：
  - **Stop hook**：会话结束时自动反思「Claude 这次有没有反复犯同一个错？要不要写进 CLAUDE.md？」然后由 hook 自己去改 CLAUDE.md。
  - **SessionStart hook**：根据当前所在子目录动态注入模块 context（在 `payments/` 就注入支付 skill，在 `auth/` 就注入鉴权 context）。

### 何时该搭

**CLAUDE.md / 权限 / 地图这三层稳定之后再挂 hook。** hook 是建立在「已经知道哪些规则、哪些 context 该注入」之上的；基础不稳就挂 hook，等于自动化一个还没想清的流程。

### 怎么搭

从 `assets/templates/hooks-examples.md` 里挑现成片段。**先挂能自进化的那一两个（Stop 反思回写、SessionStart 按子目录注入），加一个 PostToolUse 自动格式化兜底，别一次堆满。**

### 例子

- PostToolUse：每次 Claude 写完文件自动跑 `prettier --write` / `gofmt -w`，CI 不再因格式问题红。
- Stop：会话结束扫一遍本次对话里 Claude 被纠正了几次同类问题，超过阈值就把这条规则追加进对应子目录 CLAUDE.md——CLAUDE.md 自己在长。
- SessionStart：检测 cwd 在哪个子目录，注入该域专属的 skill 菜单和 gotcha。

### 常见错误

- **只把 hook 当 lint 跑**：浪费了它最大的价值（自进化）。
- **一次挂十个 hook**：每个 hook 都在改环境，堆太多会互相打架且难调试。
- **自进化 hook 不设上限**：Stop hook 无脑往 CLAUDE.md 追加，几周后 CLAUDE.md 破 200 行——自进化也要服从 200 行红线。

---

## 第 5 层 · Skills

### 是什么

Skill 是针对**某个具体任务的 SOP**（「我们这儿数据库迁移怎么走」「标准微服务发布流程」）。它和 CLAUDE.md 最本质的区别是加载方式：

- **CLAUDE.md：全量加载。** 不管这次任务用不用得上，每次会话都整篇进 context。
- **Skill：按需加载（progressive disclosure）。** 启动时只注入每个 skill 的「名字 + 一句话描述」（几十个 token，相当于**给你一份菜单**）；只有当 Claude 判断当前任务真的需要某个 skill 时，才在运行时把完整的 SKILL.md 拉进来（相当于**点了菜才上这道菜的食谱**）。

这就是为什么高频但重的知识应该进 skill 而不是 CLAUDE.md：进 CLAUDE.md 是每次都付全价，进 skill 是用到才付费。

### 何时该搭

判断标准就一句话，Boris 的原话：**「If you do something more than once a day, make it a skill.」**（一天会做不止一次的事，就做成 skill。）一次性的、或者每次都不一样的事，不值得做成 skill。

### 怎么搭

把高频操作写成一个 skill 文件夹（含 SKILL.md，描述什么时候用、怎么一步步做）。**可以把 skill 绑定到特定子目录路径**（支付部署 skill → 绑 `services/payments/`），这样它只在相关目录的菜单里出现，避免污染其他域的 context。

### 例子

- `/commit-push-pr`：提交、推送、开 PR 一条龙——这种一天用几十次的，必须是 skill / slash command。
- 数据库迁移 SOP：绑到 `migrations/` 目录，只有在那干活时才进 context。
- 微服务发布流程：绑到 `services/`，把「先打 tag、再灰度、再全量」的步骤固化下来。

### 常见错误

- **把该进 skill 的东西塞进 CLAUDE.md**：每次会话都全量付费，把 200 行预算吃光。
- **skill 不绑路径**：所有 skill 的菜单项在所有目录都冒出来，菜单本身变成噪音。
- **把一次性流程做成 skill**：维护成本 > 收益，过段时间就成了没人维护的死 skill。

---

## 第 6 层 · LSP

### 是什么

LSP（Language Server Protocol）就是 VS Code 里「转到定义 / 查找引用」背后的那套东西。装上它，Claude 就能**按符号搜索，而不是按字符串 grep**。

差别有多大，一个例子说清：grep `getUser` → 三千条命中（前端、后端、测试全混在一起）→ Claude 要逐条读去判断哪个是你要的 → context 烧光。换成 LSP：问「`auth/login.ts` 里那个 `getUser` 的所有引用」→ **精确返回三条**，过滤在 Claude 读文件之前就完成了。

Anthropic 称 LSP 为多语言大库的 **「one of the highest-value investments」**（最高价值的投资之一）。这不是空话——有真实案例：一家企业软件公司在全公司铺开 Claude Code **之前**，先在**组织层面铺了 LSP**，就是为了让符号歧义极高的 C/C++ 能配合 Claude 正常工作。**先铺 LSP，再铺 Claude Code**，顺序是刻意的。

### 何时该搭

**多语言仓库、或符号歧义高的语言（C/C++/Java/PHP）时强烈建议。** 侦察报告里主要语言是这几类、或者一个 monorepo 里混了多种语言，就是明确信号。纯单一脚本语言的小库可以缓一缓。

### 怎么搭

整个过程不到两分钟：

1. 在 Claude Code 里用 `/plugin`，搜 `lsp`。
2. 装对应语言的代码智能插件：`typescript-lsp` / `pyright-lsp` / `rust-analyzer-lsp` 等。
3. 装对应的语言服务器二进制：`pip install pyright`、`npm install -g typescript-language-server` 等。

### 例子

一个 C++ + TypeScript 的 monorepo：装 `rust-analyzer-lsp` 不对路，应该装 C/C++ 的语言服务（如 clangd 对应插件）+ `typescript-lsp` + 二进制 `typescript-language-server`。装完后，Claude 查 C++ 里一个被几十处调用的方法，从「grep 出几百条逐条读」变成「LSP 精确列引用」，context 占用断崖式下降。

### 常见错误

- **装了插件没装语言服务器二进制**：插件是壳，没有 `pyright` / `typescript-language-server` 这类二进制，符号检索起不来。
- **在多语言库里只装一种语言的 LSP**：其他语言还是退回 grep，问题没解决。
- **小单语言库强上 LSP**：收益有限，不如先把精力放在 CLAUDE.md 和地图上。

---

## 第 7 层 · 子 agent / 会话拆分 / batch

### 是什么

这一层解决「跨大量文件的改动改到一半就崩」。核心三招：**派子 agent 探索（隔离 context）、把大任务拆成多个会话（用 plan 文件做桥梁）、大规模迁移用 `/batch`（几十个并行子 agent，各自独立 git worktree、自测、开 PR）。** 贯穿其中的那句话是 Boris 的 **Pour your effort into the plan so Claude can one-shot the implementation**——功夫花在计划上，让实现一发命中。修正方向是**拆会话 + 上子 agent，不是写更长的 prompt**。

### 何时该搭 / 何时用

这层更多是**作业时（模式 B）的用法**而非搭建时的文件。搭建阶段你要做的是：确认子目录测试命令齐（第 2 层）、确认 plan 文件有地方放，并在 CLAUDE.md 里提示「大改动先出 plan、用子 agent 探索」。

### 怎么用（要点）

- **先派子 agent 探索**：让它在自己的 context 里读几十个文件，只回传一份几百字 findings，主 agent 的 context 保持干净。
- **会话拆分**：会话 1 出 plan、不写码；会话 2/3 各实现一个模块，用 plan 文件做桥梁，每个会话从干净 context 起步。
- **大迁移用 `/batch`**：对话里把迁移方案谈定，再派出几十个并行子 agent，各在独立 worktree 里跑、自测、开 PR。

> 这层只点要害。完整操作手册（子 agent 探索话术、会话拆分节奏、`/batch` 工作流、创始人多终端并行）见 `references/operating-playbook.md`。

---

## 第 8 层 · Plugins / MCP

### 是什么

这是**团队分发层，也是最后一层**。

- **Plugin**：把 skill + hook + MCP + LSP 配置**打包成一个安装包**。解决「好配置只活在小圈子里」。新人 install 一次，就拥有和团队同等的 Claude Code 能力。公司可以建自己的 plugin marketplace。真实案例：一家大型零售公司做了个 skill 让 Claude 连内部数据分析平台，分析师不用切工具就能拉销售数据——它从几个人的本地配置起步，打包成 plugin，全公司铺开。
- **MCP**：接入**外部系统**的桥（Slack / Jira / wiki / 数据库 / 监控）。Slack MCP 搜公司 Slack、BigQuery MCP 跑查询、Sentry MCP 拉生产错误日志。

反直觉的告诫：**别太早上 MCP。** MCP 是最后一层；如果 CLAUDE.md / hooks 还没打磨好，MCP 接进来的数据只是噪音。正确顺序是：**先打磨 CLAUDE.md + skills → 用 plugin 打包 → 最后才接 MCP。**

### 团队 ownership（这层成败的关键，不是技术问题）

成功的组织会在开放访问**之前**，指派一个小团队（哪怕 1–2 人）先把整套基础设施搭好——第一印象很重要，开发者第一次用就失败，很难再赢回来。两种角色：

- **Agent Manager**（半 PM 半工程师）：owning plugin 分发、CLAUDE.md 标准、skill 审批。
- 小团队至少要有一个 **DRI**（直接责任人），对「哪些 skill / plugin 能上」有拍板权。

没有 owner，再好的 plugin 也会变成「没人维护的部落知识」。Anthropic 的原话：**Bottoms-up adoption generates enthusiasm but can fragment without someone to centralize what works.**（自下而上的采用能激发热情，但缺一个把有效做法集中起来的人，就会碎片化。）

### 何时该搭

**前七层都打磨稳了、且需要往团队推广时才上这层。** 单人 / 小项目可以长期不碰 MCP。

### 常见错误

- **基础没搭好就上 MCP**：接进来一堆外部数据，Claude 反而更容易迷失。
- **没人 owner 就全员开放**：plugin 碎片化，第一印象搞砸。
- **把顺序倒过来**：先接 MCP 再回头补 CLAUDE.md——等于先装抽油烟机再砌灶台。

---

## Q7 适配性清单

Claude Code 是围绕一个最大公约数设计的：**Git + 工程师为主 + 标准目录结构。** 搭建前先对照，命中下面三类的，要如实告诉用户「这类项目 harness 适配成本高」，再决定要不要继续、做哪些定制。

**三类不那么适配的项目：**

1. **游戏引擎 / 大量二进制资源**：Claude 读不了 3D 模型、贴图、音频这些二进制资产，仓库的核心内容它看不见。
2. **非常规 VCS**：Perforce / Subversion / 自研 VCS——Claude Code 的很多默认假设建在 Git 上，这些需要额外配置。
3. **非工程师为主贡献**：主要由 PM 改产品文档、设计师改 Figma 配置的仓库——harness 和贡献者的工作方式不匹配。

非标准情况需要**更多定制配置**；Anthropic 的 **Applied AI 团队**会直接和这类客户对接。一句话记住：Claude Code 的甜区是 **Git + 工程师 + 标准目录结构**，偏离越远，搭 harness 的边际成本越高。

判断流程：侦察（第 0 层）报告里如果出现「大量二进制 / 非 Git VCS / 代码占比很低」的信号，先停下来过这张清单，别闷头硬搭。

---

## 最高 ROI 的三件事

如果只能做三件事，就做这三件——它们是全公司验证过的「最高 ROI 动作」，任何模式下都应该最先确认：

1. **CLAUDE.md 砍到 200 行以内**（分层，根目录只放指针和坑）——见第 1 层 + `references/claude-md-guide.md`。
2. **在子目录启动 Claude，而不是仓库根**（Initializing in subdirectories, not at the repo root）——要改支付就 `cd services/payments` 再开工，context 立刻聚焦到一个域；Claude 仍会向上加载根 CLAUDE.md 的通用规则，但优先级给到当前子目录。
3. **装 LSP**——见第 6 层，多语言 / 高符号歧义库里收益最大。

这三件做完，大多数「context 老爆、找错文件」的抱怨就消掉一大半。其余各层是在此之上的增益。
