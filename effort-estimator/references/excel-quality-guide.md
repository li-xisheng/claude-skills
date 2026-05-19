# Excel 出力 品質ガイド

## 核心原则

**Excel 不是静态报表，是可交互的计算工具。** 客户/审阅者拿到后，应该能直接改数字看结果，不需要懂公式。

---

## 一、必须遵守的规则

### 1. 系数 = 参照セル、禁止硬编码

❌ **错误**：`=D7*1.5`（1.5 写在公式里，改一个系数要改几十个公式）

✅ **正确**：`=D7*C5`（C5 是黄色输入格，改一处全表联动）

所有可变参数（技能系数、管理工数率、风险缓冲率、単価）必须放在**独立的输入单元格**里，公式通过引用这些单元格来计算。输入格用黄色/橙色标记。

### 2. 工程分组 + 小计

任务按工程分组，每组末尾有 `=SUM(Fx:Fy)` 小计行（绿色底色）。

❌ **错误**：一个长列表，无分组，无小计

✅ **正确**：
```
【A. 工程名】          ← 蓝色段头
  A1  任务1  1  2  3  =PERT
  A2  任务2  2  3  5  =PERT
  A. 工程名 小计       =SUM(Fx:Fy)  ← 绿色小计
```

### 3. Anti-double-buffer 明示

最终缓冲率旁边必须有检查公式：
```
=IF(风险率>0.5, "⚠ 50%超！重複チェック", "✔ OK")
```

### 4. PERT 置信区间

除了期望值，显示乐观/悲观两端的合计，让审阅者能看到范围。

### 5. 假设清单独立成表

不在 WBS 表里写长篇备注。假设条件（変動時の影響付き）放独立 Sheet。

### 6. 冻结窗格

`freeze_panes = 'A5'` — 表头固定，滚动时始终可见。

---

## 二、推荐的 Sheet 结构

| Sheet | 内容 | 必须 |
|-------|------|:----:|
| WBS+PERT | 任务明细 + PERT公式 + 可调系数 + 汇总 | ✅ |
| Phase分割 | Phase 引用 Sheet1 自动计算 | 推荐 |
| 仮定一覧 | 假设 + 变动影响 | ✅ |

---

## 三、推荐的视觉规范

| 元素 | 样式 | 用途 |
|------|------|------|
| 表头行 | 蓝底白字 (#4472C4) | 列标题 |
| 段头行 | 浅蓝底深蓝字 (#D6E4F0) | Section header |
| 小计行 | 浅绿底 (#E2EFDA) | 工程小计 |
| 输入格 | 浅橙底红字 (#FCE4D6) | 可调整参数 |
| 汇总行 | 浅黄底 (#FFF2CC) | 总计/最终值 |
| 最终工数 | 大字号红字 (14pt, #C00000) | 一眼看到 |

---

## 四、使用 `scripts/generate_excel.py`

### 方式 1：Python API（精确控制）

```python
from generate_excel import EstimateWorkbook

wb = EstimateWorkbook()
wb.set_meta(
    title='案件名 工数見積',
    subtitle='作成日: 2026-05-19 | ...',
    config={'skill_coef': 1.0, 'mgmt_rate': 0.20, 'risk_rate': 0.15}
)

wb.add_section('【A. 工程名】')
wb.add_task('A1', 'タスク名', o=1, m=2, p=3, note='備考')
wb.add_task('A2', '別タスク', o=2, m=3, p=5)
wb.add_subtotal('A', 'A. 工程名 小計')
# ... more sections ...

wb.finalize(
    summary_sections=['A', 'B', 'C'],
    summary_labels={'A': 'A. ...', 'B': 'B. ...', 'C': 'C. ...'}
)

wb.add_phase_sheet([...])
wb.add_assumptions_sheet([...])
wb.save('output.xlsx')
```

### 方式 2：Dict 声明式（快速生成）

```python
from generate_excel import from_dict

project = {
    'title': '案件名 工数見積',
    'subtitle': '...',
    'config': {},
    'sections': [
        ('A', '【A. 工程名】', [
            ('A1', 'タスク名', o, m, p, '備考'),
        ]),
    ],
    'summary_sections': ['A', 'B'],
    'summary_labels': {'A': 'A. ...', 'B': 'B. ...'},
    'phases': [...],
    'assumptions': [...],
}
from_dict(project, 'output.xlsx')
```

### カスタマイズ

`Styles` クラスを継承して色やフォントを上書き可能：

```python
class MyStyles(Styles):
    HEADER_FILL = PatternFill(...)  # 別の色に
```

---

## 五、よくある間違い（反例）

| 問題 | 症状 | 対策 |
|------|------|------|
| **係数ハードコード** | `=D7*1.5` が 50 行に分散 | 係数は独立セルに入れ、全公式から参照 |
| **小計なし** | どこからどこまでが一つの工程か分からない | 工程ごとに SUM 小計を入れる |
| **バッファ根拠不明** | 「+30%」のみ、理由なし | なぜその数字かの説明を添える |
| **範囲なし** | 「145人日」一点のみ | 楽観/悲観のレンジを併記 |
| **仮定が本文に埋没** | WBS シートの長文備考 | 独立シート「仮定一覧」に分離 |
| **入力と計算の混在** | どれが変えられる数字か分からない | 入力セルは色付け、計算セルと視覚的に区別 |
| **パンくず非固定** | スクロールで表頭が消える | `freeze_panes` 必須 |
