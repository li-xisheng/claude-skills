# Claude Skills — westarlsc

Personal collection of Claude Code skills. This repo mirrors [lxsWestar/claude-skills](https://github.com/lxsWestar/claude-skills) (weekly, additive-only sync — see `.github/workflows/sync-from-company.yml`) plus skills that live only here.

## Skills

| Skill | Description |
|-------|-------------|
| [effort-estimator](./SKILL.md) | 工数估算（中日双语）。WBS/PERT/德尔菲/三维评估/NESMA/Planning Poker 等 10+ 方法，适配日本客户正式見積書格式 |
| [ocrskill](./ocrskill/) | MinerU2.5-Pro OCR，用于本地 PDF/图片文档解析 |
| [consulting-advisor](./consulting-advisor/) | 顶级咨询公司思考方法论。SCQA / MECE / 5 Whys / 金字塔原则 / 方案对比矩阵的 6 步分析流程，适用于内部说服与战略提案 |
| [consulting-proposal-docx](./consulting-proposal-docx/) | 咨询风格 Word 提案书 / 稟議書生成器。JSON-driven，含执行摘要 SCQA 框、对比矩阵、Phase 路线图、审批申请等标准章节 |

## Usage

```bash
# Clone into ~/.claude/skills/
git clone https://github.com/li-xisheng/claude-skills.git ~/.claude/skills/
```

Or install individual skills:

```bash
cp -r consulting-advisor ~/.claude/skills/
```
