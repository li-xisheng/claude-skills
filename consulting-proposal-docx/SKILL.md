---
name: consulting-proposal-docx
description: "生成顶级咨询公司风格的专业 Word 提案书/稟議書 .docx 文档。采用麦肯锡式 SCQA + 金字塔结构，含执行摘要、现状分析、根本原因、方案建议、对比矩阵、实施路线图、风险管理、审批申请等标准章节。配色采用咨询业标准（深蓝 #1F3864 标题 + 中蓝 #2E4C8C 二级 + 浅灰背景表格），字体中文用 Microsoft YaHei、日文用 Meiryo。当用户需要输出正式提案书、稟議書、董事会汇报材料、内部说服文档（中文/日文/英文 Word .docx）时使用。触发关键词：提案书、稟議書、business proposal、proposal docx、咨询风格提案、内部审批文档、董事会材料、社内稟議、技術提案書、提案資料。"
---

# Consulting Proposal DOCX — 咨询风格提案书生成器

输出咨询公司质感的专业 Word 提案书。中文用宋黑混排+Microsoft YaHei，日文用 Meiryo，标题深蓝 (#1F3864)，二级标题中蓝 (#2E4C8C)，表格浅蓝表头 (#D5E8F0)。

## 推荐工作流

1. **先用 `consulting-advisor` 技能**整理出 SCQA、根因、对比、实施计划等内容
2. **使用本技能的标准章节模板**填入内容
3. **调用 `scripts/generate_proposal.js`**（Node.js + docx 包）生成 .docx
4. **若有修改需求**：解包 XML → 修改 → 重新打包

---

## 标准提案书章节结构

| # | 章节 | 内容要点 |
|---|------|--------|
| 0 | **封面 + 元信息** | 标题、副标题、作成者/部署、日期、社外秘标识 |
| 1 | **エグゼクティブサマリー / 执行摘要** | SCQA 一页浓缩，含3个审批申请项 |
| 2 | **现状分析** | 数据摘要 + 上司指摘对照表 |
| 3 | **技术根本原因分析** | 现行架构图解 + 5 Whys 根因 |
| 4 | **提案** | 新方案介绍 + 现行 vs 提案对比矩阵 |
| 5 | **实施计划** | Phase 1-4 路线图，含负责人列名 |
| 6 | **风险与缓解** | 各风险点对应缓解措施 |
| 7 | **审批申请** | 具体到"批准什么"的3项 |
| 8 | **附录** | 参考资料、技术细节 |

---

## 生成步骤

### 步骤 1：准备内容 JSON

将提案书内容整理为如下结构：

```json
{
  "language": "ja",
  "filename": "HOUSEIチャットボット_基盤更新提案書.docx",
  "title": "HOUSEIチャットボット 基盤更新提案書",
  "subtitle": "～ imprai依存構造 から LlamaIndex自社運用基盤 への移行 ～",
  "meta": {
    "author": "李禧晟",
    "department": "プロダクト事業室",
    "date": "2026年5月22日",
    "classification": "社外秘"
  },
  "executive_summary": { "situation": "...", "complication": "...", "question": "...", "answer": "...", "approvals": ["...", "...", "..."] },
  "sections": [
    { "heading": "現状分析", "content": [ ... ] }
  ]
}
```

### 步骤 2：生成 .docx

```bash
cd <work-dir>

# 依赖（首次运行必须）：在工作目录安装 docx 包到本地 node_modules
npm install docx

# 然后调用脚本
node <skill-path>/scripts/generate_proposal.js content.json output.docx
```

**模块解析提示**：脚本本身放在 skills 目录下，但 Node 解析依赖时从脚本所在目录向上查找。
若工作目录已有 `node_modules/docx`，可设置 `NODE_PATH` 让脚本找到它：
```bash
# Windows PowerShell
$env:NODE_PATH = "$(Get-Location)\node_modules"
# Linux/Mac
export NODE_PATH="$(pwd)/node_modules"
```
或更简单：把 `generate_proposal.js` 复制到工作目录里执行。

`scripts/generate_proposal.js` 是即拿即用的封装：自动应用咨询风格（深蓝标题、表头配色、字体）、自动处理中/日/英文字体切换、自动生成 SCQA 框、比较矩阵、Phase 路线图等元素。

---

## 编辑既存 .docx

如果已有 .docx 文件需要修改文字内容，使用解包-编辑-重打包的方式（比重新生成更安全）：

```python
import zipfile, os

# 1. 解包
with zipfile.ZipFile('input.docx') as z:
    z.extractall('_unpacked')

# 2. 编辑 _unpacked/word/document.xml （以及 header*.xml/footer*.xml）

# 3. 重新打包
with zipfile.ZipFile('output.docx', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('_unpacked'):
        for f in files:
            fp = os.path.join(root, f)
            z.write(fp, os.path.relpath(fp, '_unpacked'))
```

**关键坑**：
- 同一段日/中文字可能被拆分到多个 `<w:r>` 中，按整段字符串搜索可能失败 → 拆短一些
- docx-js 写入的弯引号是 Unicode（U+201C/U+201D），不是 ASCII 双引号
- 修改要同时检查 `word/document.xml`、`word/header*.xml`、`word/footer*.xml`（文件名/标题可能在多处）
- 弯引号 / 全角符号在 Python 替换时使用 `\u201c \u201d` 显式书写更安全

---

## 设计准则（咨询公司风格）

- **配色**：标题深蓝 `1F3864`，二级中蓝 `2E4C8C`，表头浅蓝背景 `D5E8F0`，正文 `2E2E2E`
- **字体**：中文 Microsoft YaHei，日文 Meiryo，英文 Calibri/Arial，全部统一字号 21pt（正文 20pt）
- **表格**：1pt 灰色边框 `CCCCCC`，单元格内边距 80/120 dxa，使用 `ShadingType.CLEAR`（绝不用 SOLID）
- **比较矩阵符号**：✕（不满足）/ ▲（部分满足）/ ○（满足）/ ◎（超额满足）
- **SCQA 框**：在执行摘要中用 4 个左侧深蓝竖线段落，S/C/Q/A 分别标注
- **绝不**使用 emoji 表情（咨询风格忌讳花哨）
- **绝不**使用整页大色块（保持简洁）

---

## 参考资料

- `references/sample_content.json` — 完整内容 JSON 示例
- `scripts/generate_proposal.js` — 主生成脚本
- `scripts/repack_docx.py` — 重打包工具
