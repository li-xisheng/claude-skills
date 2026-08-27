# 推导过程记录（冷参考·证明档案）

> 本文件回答一个问题：**方法论的每条结论是怎么得出来的、证据在哪**。
> 平时不需要读；当有人问「这条规则凭什么」「推导过程能复核吗」时打开。
> 原始调查数据在 [research/](research/)（8 个角度的结构化发现，2026-08-26 采集）。
> 结论本体见 methodology.md，检验过程见 validation-record.md，本文件补上两者之间的推导链。

## 一、推导链（2026-08-26 一日内完成，各步有档）

| 步 | 输入 | 动作 | 产出 | 对结论的影响 |
|---|---|---|---|---|
| 1 | 一线观察：10 个各估 5 人日的任务，多 agent 并行 10 人日全部关闭；旧 effort-estimator 技能全库 grep 无任何 AI 开发前提 | 问题定义 | 「人日失效」假设 | 起点 |
| 2 | 用户与另一 AI 的长对话 | 推演 | 18 条初始结论（四数字、闭环轮数、DAG、发现池、概率工期、Amdahl、探索预算…） | 方法论毛坯 |
| 3 | 18 条作为基线 | **调查路径 A**：8 角度并行检索（每个 agent 持基线逐条判定 确认/新增/反驳） | [research/angle-\*.json](research/)：8 文件、~100 来源、confirms 38 / novel 68 / counter 27 条 | 证据层 |
| 4 | 同一基线 | **调查路径 B**：另一 AI 独立检索（Thoughtworks/METR/DORA/MSR/Fowler 系） | 用户转贴的独立报告 | 与 A 的重合部分构成**独立复核** |
| 5 | A+B | 交叉比对 | 确认层（瓶颈上移、放大器、3-5 并行）／新增层（Sahaj RAE、双 regime、Novelty Bottleneck、软约束击穿、検証ベース）／反驳层（METR -19%、DORA 组织级持平、区间偏窄） | 三层定稿素材 |
| 6 | 用户两轮质疑：「METR 是 25 年的」「2 月的模型和现在也天差地别」 | 时效性推演 | **测量管线定律**（研究发表周期 6-12 月 > 模型代际 6 月 ⇒ 已发表数字永久过期）→ **快慢变量分层原则** | 方法论**第一设计原则的直接出处**——注意：此条无外部文献，是本次对话的原创推导 |
| 7 | 5+6 | 合并定稿 | methodology.md 前身（总纲四句 + 修正五处） | 结论层 |
| 8 | 定稿 | 三路可靠性检验（专家会诊/第一性原理/跨领域借解） | validation-record.md：打掉 3 项、新增 6 项 | 结论修形 |
| 9 | 检验后定稿 | skill 成形 + eval | v1.0；5 用例 23 断言，with-skill 23/23 vs baseline 13/23（+38pp） | 可用性证明 |
| 10 | v1.0 | 实战检验（ezkotae 三方向，预注册式） | 预注册档案（本地 workspace，未入库）；教训 #1〜#4 | 进行中 |
| 11 | v1.0 全文+引用 | **第三方复核**（2026-08-27，另一 AI 独立重查 DORA/Fowler/arXiv 2607.01904/MSR/METR/2601.00753/PMI/Jørgensen） | 核心五判断确认成立；吸收 3 项：瓶颈迁移表述、WBS 定义回归+作成手引（PMI 背书，2026-08-27 浏览器抓取核实）、Jørgensen 前史 | v1.1 |

## 二、8 角度调查的关键产出（详见 research/ 各文件）

| 角度 | 最重要的单条发现 |
|---|---|
| en-discourse | Sahaj「Residual Attention Estimation」完整替代框架（S/M/L 禁 XL、验证 WIP、dry-run 六因子）——残余注意力估算的直接来源 |
| evidence | METR RCT 感知-实测 39pp 落差 + 2026-02 对照组灭绝自陈——「自报实测降级」与「在线校准是唯一出路」的证据 |
| thought-leaders | Böckeler/Fowler Harness 四象限、Kent Beck「Multi-agent is a feature. Outcome-orientation is the thing」 |
| jp-discourse | 検証ベース计价、三段見積書（「揉める原因の9割…」）、スコープ蠕動——対外层几乎整层来自此角度 |
| cn-discourse | 快手 L1/L2/L3 双指标防 Goodhart、字节「功能正确率≠可交付性」两层验证 |
| practice | Anthropic 70%/20% 决策分布、并行生成串行合并、20%/69% 帕累托审查、agent PR 冲突率 19.8% 实测 |
| spec-driven | McMillan 空结果（指令文件排版不显著、会话每多一函数遵循率 -5.6%）——「别打磨 spec 排版」的出处 |
| contrarian | 「代码库新旧是最大分界线」（Denisov-Blanch 2026-07）、软约束击穿（零审查合并 +31%）、accident/essence 诊断式 |

## 三、关键结论 → 证明位置索引

| 结论 | 证明 |
|---|---|
| 诊断先于估算（-19%〜20x 散布） | MSR +26% 与 METR -19% 的调和：angle_evidence / angle_contrarian |
| 双 regime、静态信号可预测审查量 | arXiv 2601.00753：angle_en-discourse |
| 队列纪律为中枢 | **三路检验独立收敛**（Kingman/CONWIP/医院容量块）：validation-record.md 汇总节 |
| 残余人类注意力为估算单位 | Sahaj：angle_en-discourse；Anthropic 决策分布：angle_practice |
| 软约束击穿（WIP 上限的必要性） | Faros 遥测：angle_en-discourse / angle_contrarian |
| 快慢变量分层 | 本记录 §一-6（**对话原创推导，无文献**，被 METR 方法论危机侧面支持） |
| 検証ベース・三段見積書 | angle_jp-discourse |
| 适用下界（小任务慢 10 倍） | ScottLogic AB 实测：angle_spec-driven |
| 双指标防 Goodhart | 快手实测：angle_cn-discourse |
| WBS 定义回归+作成手引 | PMI Blog 2026-08-14（已核实，原文存档 research/pmi-wbs-blog-2026-08-14.md）+ 第三方复核：本记录 §一-11；external-layer.md §9 |

## 四、被打掉/未采纳的候选（负结果留档）

| 候选 | 结局 | 理由与出处 |
|---|---|---|
| max/min 公式作为计算式 | 降级为心智模型 | 队列延迟叠加于关键路径而非并列、Kingman 方差、RCPSP NP 难：validation-record 路线一 A |
| 蒙特卡洛模拟 | 弃用，改经验分位数 | 任务相关性使区间系统性偏窄：同上 |
| 8 字段任务模板 | 砍到核心 3 字段 | 仪式死风险：validation-record 路线一 B |
| MCP 优先（方向 2） | HTTP `?q=` 优先 | 用户实务判断 + PoC 实测边界（angle 无、实战档案有） |
| 誘引再現試験移出范围 | 后回滚进 4 週枠 | 实战教训：范围裁剪要贴用户已承诺的框架 |

## 五、局限声明（诚实条款）

1. 本记录由参与推导的 AI 整理，**不是独立第三方审计**；对话原文未随档。
2. research/ 内全部数字遵循「方向证据、非常数」纪律——引用时必须带 vintage，禁止当系数。
3. 调查路径 B 的原文未归档（用户转贴件），其结论已并入 methodology.md 证据表。
4. eval 与实战预注册数据在本地 workspace（gitignore），实战成绩单出具后择要归档。
