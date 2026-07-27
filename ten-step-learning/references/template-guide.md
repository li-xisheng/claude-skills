# 模板填充规范 · assets/template.html

> 工作方式：**不直接改模板、不手写整份 HTML**。为每个 `{{...}}` 占位符写一个
> 同名片段文件到构建目录 `fragments/`（如 `STEP_1_INPUT.html`、`STEP_MAP.html`），
> 然后用 `scripts/assemble.py` 确定性组装。片段只复用模板已定义的组件类，
> 不新造样式、不写改颜色/圆角/阴影的内联 style。

## 设计契约（模板内建，违反会显得廉价）

- **颜色只有四个**：画布 `#eef2e3`（pale sage）/ 纸面 `#fcfcfc` / 品牌 `#043f2e`（deep forest）/
  强调 `#c8f169`（chartreuse）。数据可视化可额外用 `#78c51c`；红 `#c0392b` 仅限"冲突"语义。
- **无阴影**，层次靠 sage → forest → chartreuse 三层色块堆叠。
- **圆角只用 4px 与 16px**（药丸形标签除外）。
- **字体**：标题 Fraunces 衬线且仅用于 36px 以上；正文/UI 一律 Inter。

## 占位符总清单（66 个）

| 占位符 | 位置 | 填什么 |
|---|---|---|
| `{{TOPIC}}` | title / 侧栏 / 总览大标题（多处） | 主题名（短）。由 assemble.py 的 `--topic` 参数统一替换，**不需要写片段文件** |
| `{{METHOD_INTRO}}` | 总览 lead | 2–4 句：这套十步法是什么、这次要带你把该主题学成什么样 |
| `{{STEP_MAP}}` | 总览 | 10 张 `.stepmap` 卡（见下） |
| `{{STEP_N_TITLE}}` | 第 N 步大标题 | 该步针对本主题的一句话标题（可含主题词） |
| `{{STEP_N_PURPOSE}}` | 第 N 步 lead | 1–2 句：这一步在干嘛、为什么重要 |
| `{{STEP_N_TAKEAWAYS}}` | 第 N 步·学习结果 | `<ul><li>` 3–5 条提炼结论 |
| `{{STEP_N_VIZ}}` | 第 N 步·可视化槽 | 仅 1/2/6 步写片段；其余步**不写文件**（脚本自动置空） |
| `{{STEP_N_OUTPUT}}` | 第 N 步·输出面板 | 该步完整原始产物，`.prose` 排版（第 5/8 步用专用组件） |
| `{{STEP_N_INPUT}}` | 第 N 步·输入面板 | `.upstream` 上游标签 + `.prompt-block` 提示词 |
| `{{CLOSING_INTRO}}` | 收尾 lead | 2–3 句：十步连成一条线的复述（开局→吃透→检验→压缩） |
| `{{LOOP_DIAGRAM}}` | 收尾 | 环形闭环 SVG（见下） |
| `{{CLOSING_DELIVERABLES}}` | 收尾 forest 卡 | `.prose`：最终可带走的交付物清单（简报/阶梯/速查表各一句） |

> N = 1…10。assemble.py 会自动校验：非 VIZ 占位符缺片段 → 报错；组装后残留 `{{` → 报错。

## 通用组件片段

### 学习结果 `STEP_N_TAKEAWAYS.html`
```html
<ul>
  <li><strong>连对手都承认的：</strong> ……（一句结论）</li>
  <li>……</li>
</ul>
```

### 输入面板 `STEP_N_INPUT.html`
```html
<div class="upstream">消费上游：<span class="tag tag--sage">第1步·五视角</span><span class="tag tag--sage">第2步·矛盾图谱</span></div>
<div class="prompt-block">这里粘该步实际使用的提示词（已把 {{主题}}/{{角色}} 填成真实值——注意：片段里如需展示提示词占位符原文，写成【主题】等中文括号形式，避免与模板占位符语法冲突）。</div>
```
> 第 8、9 步的输入面板末尾加一句：
> `<p class="res__v" style="margin-top:12px;color:var(--charcoal)">注：原方法该步为一问一答的交互式版本，此处为一次性生成的可复用材料；交互版可在对话中体验。</p>`

### 输出面板 `STEP_N_OUTPUT.html`（通用步用 `.prose`）
```html
<div class="prose">
  <h4>小节标题</h4>
  <p>段落……</p>
  <ul><li>要点……</li></ul>
</div>
```

### 总览步骤地图 `STEP_MAP.html`（10 张卡）
```html
<a href="#view-1" data-view="view-1"><div class="stepmap__n">01</div><div class="stepmap__t">五视角 STORM</div><div class="stepmap__d">让 5 种人吵一架</div></a>
<!-- …一直到 view-10；data-view 必须与目标 section id 一致，JS 才会切换 -->
```

## 专用组件

### 第 1 步 · 五视角 persona 卡 → `STEP_1_VIZ.html`
```html
<div class="persona-grid">
  <div class="persona">
    <div class="persona__role">实践者</div>
    <div class="persona__tag">每天跟这东西打交道的人</div>
    <div class="persona__block"><div class="persona__k">核心立场</div><div class="persona__v">两句话……</div></div>
    <div class="persona__block"><div class="persona__k">最强证据</div><div class="persona__v">真实证据 + <a href="...">来源</a></div></div>
    <div class="persona__insight"><div class="persona__k">只有他会告诉你</div>独有洞察……</div>
  </div>
  <!-- 学者 / 怀疑者 / 经济学家 / 历史学家 共 5 张 -->
</div>
```
> `STEP_1_OUTPUT.html` 放更细的展开叙述；persona 卡负责一眼看全。

### 第 2 步 · 矛盾图谱 SVG → `STEP_2_VIZ.html`
5 个视角作节点摆成五边形，**冲突用红线、共识用绿线**连接，盲区在角落标注。用 viewBox 保证自适应。
```html
<div class="viz">
  <svg viewBox="0 0 640 420" role="img" aria-label="矛盾图谱">
    <line x1="320" y1="60" x2="120" y2="200" stroke="#c0392b" stroke-width="2"/>                      <!-- 冲突边(红) -->
    <line x1="120" y1="200" x2="520" y2="200" stroke="#78c51c" stroke-width="2" stroke-dasharray="5 5"/><!-- 共识边(绿) -->
    <g><circle cx="320" cy="60" r="34" fill="#043f2e"/><text x="320" y="65" text-anchor="middle" fill="#fcfcfc" font-size="13" font-family="Inter">实践者</text></g>
    <!-- …其余 4 个节点，均匀分布… -->
    <text x="320" y="400" text-anchor="middle" fill="#242423" font-size="12" font-family="Inter">盲区：没有任何视角提到 ……</text>
  </svg>
  <div class="legend">
    <span><i style="border-color:#c0392b"></i>直接冲突</span>
    <span><i style="border-color:#78c51c"></i>全体共识</span>
  </div>
  <div class="viz__cap">图注：一句话说清最大的那条冲突，以及"一旦回答就能化解它"的关键问题。</div>
</div>
```

### 第 5 步 · 资源卡 → `STEP_5_OUTPUT.html`
```html
<div class="res">
  <div class="res__head"><span class="res__name"><a href="https://…">资源名（真实，带链接）</a></span><span class="tag tag--pill tag--sage">书/课/社区</span></div>
  <div class="res__meta"><span class="tag tag--pill">约 3 小时</span><span class="tag tag--pill tag--sage">读 / 看 / 练</span></div>
  <div class="res__k">为什么比同类强</div><div class="res__v">……</div>
  <div class="res__k">该拿走的一个关键点</div><div class="res__v">……</div>
</div>
<!-- 5 张资源卡后，追加"被高估的坑"与"一周路径" -->
<div class="card" style="margin-top:16px"><div class="prose"><h4>被高估的坑</h4><ul><li>……</li></ul><h4>一周学习路径</h4><ol><li>第 1-2 天……</li></ol></div></div>
```

### 第 6 步 · 学习阶梯 → `STEP_6_VIZ.html`（VIZ 放阶梯；8 要素明细放 OUTPUT 的 .prose）
```html
<div class="ladder">
  <div class="rung"><div class="rung__lv">级别 1 · 完全初学者</div><div class="rung__name">阶段名</div><div class="rung__milestone"><strong>里程碑：</strong>能做到……就可进级</div></div>
  <div class="rung"><div class="rung__lv">级别 2 · 基本理解</div>……</div>
  <!-- 5 级，column-reverse 会让级别 5 显示在顶端 -->
</div>
```

### 第 8 步 · 题库翻卡 → `STEP_8_OUTPUT.html`（点开题目才显示答案）
```html
<details class="flash">
  <summary><span class="flash__lv">初级</span><span class="flash__q">题目 1 ……</span><span class="flash__reveal">显示答案 ▾</span></summary>
  <div class="flash__a">
    <div class="persona__k">参考答案（满分长这样）</div><div class="res__v">……</div>
    <div class="rubric"><strong>评分标准：</strong>满分=…… / 及格=…… / 常见薄弱点=……</div>
  </div>
</details>
<!-- 10 题（初3/中3/高2/专家2）。最后 5 道终极挑战题只给题目，不给答案： -->
<div class="card--forest" style="margin-top:16px"><p class="eyebrow">5 道终极挑战（自己想）</p><div class="prose" style="color:#eef3ea"><ol><li>……</li></ol><p>全部答好 = 达到 ______ 水平。</p></div></div>
```

### 收尾 · 环形闭环 SVG → `LOOP_DIAGRAM.html`
四段弧（开局→吃透→检验→压缩）围成一个环，回到起点，体现"一个闭环"。
```html
<svg viewBox="0 0 520 360" role="img" aria-label="学习闭环">
  <circle cx="260" cy="180" r="120" fill="none" stroke="#043f2e" stroke-width="2"/>
  <g><circle cx="260" cy="60" r="30" fill="#c8f169"/><text x="260" y="65" text-anchor="middle" font-size="12" font-family="Inter" fill="#000">开局</text></g>
  <!-- 吃透(右)/检验(下)/压缩(左)，均匀 4 等分；箭头示意顺时针闭合 -->
  <text x="260" y="185" text-anchor="middle" font-family="Fraunces" font-size="20" fill="#043f2e">一个闭环</text>
</svg>
```

## 填充顺序建议

1. 十步执行时边跑边写 `steps/step-NN-*.md`（原始产物落盘）。
2. 全部跑完后，按 `steps/` 取材逐个写 `fragments/*.html`：
   先 `METHOD_INTRO` / `STEP_MAP`，再 1→10 各步的 TITLE/PURPOSE/TAKEAWAYS/OUTPUT/INPUT
   （1/2/6 步补 VIZ），最后收尾三项。
3. 运行 `scripts/assemble.py`；报缺片段或残留占位符就补齐重跑。
4. 打开产物 HTML 抽查 2–3 个步骤的三栏内容是否语义正确、无占位符残留。
