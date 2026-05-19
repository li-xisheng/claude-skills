"""
工数見積 Excel 生成スクリプト — 汎用・再利用可能

Usage:
    from generate_excel import EstimateWorkbook
    wb = EstimateWorkbook()
    wb.set_meta(title="案件名", date="2026-05-19", config={...})
    # add sections -> add tasks -> finalize
    wb.add_section("A", "プロジェクト基盤")
    wb.add_task("A1", "kintone技術検証", o=2, m=4, p=8, note="最優先")
    wb.add_subtotal("A", "A. プロジェクト基盤 小計")
    ...
    wb.finalize()
    wb.add_phase_sheet(phase1=[...], phase2=[...])
    wb.add_assumptions_sheet([("仮定", "影響"), ...])
    wb.save("output.xlsx")
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

# ── Styling constants (customize per project if needed) ──

class Styles:
    """Centralized style definitions. Override per-project by passing a subclass."""
    HEADER_FILL = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    HEADER_FONT = Font(bold=True, size=11, color='FFFFFF')
    SECTION_FILL = PatternFill(start_color='D6E4F0', end_color='D6E4F0', fill_type='solid')
    SECTION_FONT = Font(bold=True, size=11, color='1F4E79')
    SUBTOTAL_FILL = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
    SUMMARY_FILL = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
    INPUT_FILL = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
    INPUT_FONT = Font(bold=True, color='C00000')
    FINAL_FONT = Font(bold=True, size=14, color='C00000')
    TITLE_FONT = Font(bold=True, size=14)
    SUBTITLE_FONT = Font(size=9, color='666666')
    BOLD_FONT = Font(bold=True)
    BOLD_FONT_L = Font(bold=True, size=11)
    CHECK_FONT = Font(size=9, color='006100')
    THIN_BORDER = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    CENTER = Alignment(horizontal='center')
    WRAP = Alignment(wrap_text=True)


class EstimateWorkbook:
    """
    Generic estimation workbook builder.

    Sheet structure:
        1. WBS+PERT — task breakdown with formulas, adjustable coefficients, summary
        2. Phase分割 (optional) — phase split view referencing sheet 1
        3. 仮定一覧 (optional) — assumptions table
    """

    def __init__(self, styles=None):
        self.wb = openpyxl.Workbook()
        self.styles = styles or Styles()
        self.meta = {}
        self.config = {}
        self.sections = []          # [(letter, label)]
        self.tasks = []             # [(type, *args)]
        self.section_task_rows = {} # letter -> [row_numbers]
        self.subtotal_rows = {}     # letter -> row_number
        self._row = 5               # current write row in sheet 1
        self._sheet1 = self.wb.active
        self._sheet1.title = 'WBS+PERT'
        self._finalized = False

    # ── Metadata & config ──

    def set_meta(self, title, subtitle='', config=None):
        """
        Set workbook-level metadata.

        config dict keys (all optional):
            skill_coef (float): default 1.0
            mgmt_rate (float): default 0.20
            risk_rate (float): default 0.15
            skill_note (str): hint for skill coeff cell
            mgmt_note (str): hint for mgmt rate cell
            risk_note (str): hint for risk rate cell
            col_widths (dict): {col_letter: width}
        """
        self.meta = {'title': title, 'subtitle': subtitle}
        self.config = {
            'skill_coef': 1.0,
            'mgmt_rate': 0.20,
            'risk_rate': 0.15,
            'skill_note': 'Senior:0.8~1.0 Mid:1.2~1.5 Junior:2.0~3.0',
            'mgmt_note': '定例・レビュー・ドキュメント 10~20%',
            'risk_note': 'PERT減半ルール: 30%→15%',
            **(config or {})
        }

    # ── Sheet 1: WBS+PERT ──

    def _setup_sheet1_columns(self):
        widths = self.config.get('col_widths', {})
        defaults = {'A': 6, 'B': 48, 'C': 10, 'D': 10, 'E': 10, 'F': 12, 'G': 16}
        for col, w in {**defaults, **widths}.items():
            self._sheet1.column_dimensions[col].width = w

    def _write_sheet1_header(self):
        ws = self._sheet1
        self._setup_sheet1_columns()
        ws.merge_cells('A1:G1')
        ws['A1'] = self.meta.get('title', '工数見積')
        ws['A1'].font = self.styles.TITLE_FONT
        if self.meta.get('subtitle'):
            ws.merge_cells('A2:G2')
            ws['A2'] = self.meta['subtitle']
            ws['A2'].font = self.styles.SUBTITLE_FONT
        headers = ['ID', 'タスク', 'O (楽観)', 'M (最可能)', 'P (悲観)', 'PERT期待値', '備考']
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=h)
            cell.font = self.styles.HEADER_FONT
            cell.fill = self.styles.HEADER_FILL
            cell.alignment = self.styles.CENTER
            cell.border = self.styles.THIN_BORDER

    def add_section(self, label):
        """Add a section header row. label is displayed text (e.g. '【A. プロジェクト基盤】')."""
        self.tasks.append(('section', label))

    def add_task(self, tid, name, o, m, p, note=''):
        """Add a task row with O/M/P values. PERT formula = (O+4M+P)/6 auto-applied."""
        self.tasks.append(('task', tid, name, o, m, p, note))

    def add_subtotal(self, letter, label):
        """Add a subtotal row that SUMs all tasks under the given section letter."""
        self.tasks.append(('subtotal', letter, label))

    def _write_tasks(self):
        ws = self._sheet1
        for item in self.tasks:
            if item[0] == 'section':
                ws.merge_cells(f'A{self._row}:G{self._row}')
                ws[f'A{self._row}'] = item[1]
                ws[f'A{self._row}'].font = self.styles.SECTION_FONT
                ws[f'A{self._row}'].fill = self.styles.SECTION_FILL
                self._row += 1
                continue

            if item[0] == 'subtotal':
                _, letter, label = item
                if letter in self.section_task_rows:
                    fr = self.section_task_rows[letter][0]
                    lr = self.section_task_rows[letter][-1]
                    formula = f'=SUM(F{fr}:F{lr})'
                else:
                    formula = '0'
                ws.cell(row=self._row, column=1, value=letter).font = self.styles.BOLD_FONT
                ws.cell(row=self._row, column=2, value=label).font = self.styles.BOLD_FONT
                cell = ws.cell(row=self._row, column=6, value=formula)
                cell.font = self.styles.BOLD_FONT
                cell.number_format = '0.00'
                for c in range(1, 8):
                    ws.cell(row=self._row, column=c).fill = self.styles.SUBTOTAL_FILL
                    ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
                self.subtotal_rows[letter] = self._row
                self._row += 1
                continue

            # task row
            _, tid, name, o, m, p, note = item
            ws.cell(row=self._row, column=1, value=tid)
            ws.cell(row=self._row, column=2, value=name).alignment = self.styles.WRAP
            ws.cell(row=self._row, column=3, value=o).alignment = self.styles.CENTER
            ws.cell(row=self._row, column=4, value=m).alignment = self.styles.CENTER
            ws.cell(row=self._row, column=5, value=p).alignment = self.styles.CENTER
            cell = ws.cell(row=self._row, column=6)
            cell.value = f'=(C{self._row}+4*D{self._row}+E{self._row})/6'
            cell.number_format = '0.00'
            cell.alignment = self.styles.CENTER
            ws.cell(row=self._row, column=7, value=note)
            # Track section
            sec = tid[0] if tid else ''
            if sec not in self.section_task_rows:
                self.section_task_rows[sec] = []
            self.section_task_rows[sec].append(self._row)
            for c in range(1, 8):
                ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
            self._row += 1

    def _write_summary(self, summary_sections, summary_labels):
        """summary_sections: list of section letters. summary_labels: {letter: label}."""
        ws = self._sheet1
        self._row += 1
        ws.merge_cells(f'A{self._row}:G{self._row}')
        ws[f'A{self._row}'] = '▼ 工程別 PERT 純工数 集計'
        ws[f'A{self._row}'].font = Font(bold=True, size=12)
        self._row += 1

        for sec in summary_sections:
            if sec in self.subtotal_rows:
                ws.merge_cells(f'B{self._row}:D{self._row}')
                ws.cell(row=self._row, column=2, value=summary_labels.get(sec, sec))
                cell = ws.cell(row=self._row, column=6, value=f'=F{self.subtotal_rows[sec]}')
                cell.number_format = '0.00'
                for c in range(1, 8):
                    ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
                self._row += 1

        # Total PERT
        self._pert_total_row = self._row
        ws.merge_cells(f'B{self._row}:D{self._row}')
        ws.cell(row=self._row, column=2, value='PERT 純工数 合計').font = self.styles.BOLD_FONT_L
        refs = '+'.join([f'F{self.subtotal_rows[s]}' for s in summary_sections if s in self.subtotal_rows])
        cell = ws.cell(row=self._row, column=6, value=f'=({refs})')
        cell.number_format = '0.00'
        cell.font = self.styles.BOLD_FONT_L
        for c in range(1, 8):
            ws.cell(row=self._row, column=c).fill = self.styles.SUMMARY_FILL
            ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
        self._row += 2

    def _write_adjustments(self):
        """Write the adjustable coefficient cells and the 4-step calculation."""
        ws = self._sheet1
        cfg = self.config

        ws.merge_cells(f'A{self._row}:G{self._row}')
        ws[f'A{self._row}'] = '▼ 調整計算'
        ws[f'A{self._row}'].font = Font(bold=True, size=12)
        self._row += 1

        # -- Adjustable input cells --
        inputs = [
            ('技能係数 (変更可 →)', cfg['skill_coef'], cfg['skill_note']),
            ('管理工数率 (変更可 →)', cfg['mgmt_rate'], cfg['mgmt_note']),
            ('リスクバッファ率 (変更可 →)', cfg['risk_rate'], cfg['risk_note']),
        ]
        cell_refs = {}
        for label, default, note in inputs:
            ws.cell(row=self._row, column=2, value=label)
            cell = ws.cell(row=self._row, column=3, value=default)
            cell.alignment = self.styles.CENTER
            cell.fill = self.styles.INPUT_FILL
            cell.font = self.styles.INPUT_FONT
            if isinstance(default, float) and default < 1:
                cell.number_format = '0%'
            ws.cell(row=self._row, column=7, value=note)
            for c in range(1, 8):
                ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
            cell_refs[label.split(' ')[0]] = f'C{self._row}'
            self._row += 1

        # -- Calculated steps --
        steps = [
            ('Step 1: PERT 純工数', f'=F{self._pert_total_row}', '全タスクの三点見積集計'),
            ('Step 2: 技能係数調整後', f'=F{self._row-3}*{cell_refs["技能係数"]}', ''),
            ('Step 3: 管理工数加算後', f'=F{self._row-2}*(1+{cell_refs["管理工数率"]})', ''),
            ('Step 4: リスクバッファ加算後 ★最終工数★',
             f'=F{self._row-1}*(1+{cell_refs["リスクバッファ率"]})', ''),
        ]
        for label, formula, note in steps:
            ws.cell(row=self._row, column=2, value=label)
            cell = ws.cell(row=self._row, column=6, value=formula)
            cell.number_format = '0.00'
            if '★' in label:
                cell.font = self.styles.FINAL_FONT
                for c in range(1, 8):
                    ws.cell(row=self._row, column=c).fill = self.styles.SUMMARY_FILL
            ws.cell(row=self._row, column=7, value=note)
            for c in range(1, 8):
                ws.cell(row=self._row, column=c).border = self.styles.THIN_BORDER
            self._row += 1

        # Anti-double-buffer check
        self._row += 1
        risk_ref = cell_refs.get("リスクバッファ率", "0%")
        ws.merge_cells(f'A{self._row}:G{self._row}')
        ws[f'A{self._row}'] = (
            f'✔ Anti-double-buffer: PERT使用→バッファ減半 | '
            f'最終バッファ率={risk_ref} | '
            f'=IF({risk_ref}>0.5,"⚠ 50%超！重複の可能性","✔ 50%未満OK")'
        )
        ws[f'A{self._row}'].font = self.styles.CHECK_FONT

    def finalize(self, summary_sections=None, summary_labels=None):
        """
        Finalize sheet 1: write header, tasks, summary, adjustments.
        Must be called after all add_section/add_task/add_subtotal calls.
        summary_sections: ordered list of section letters for the summary table.
        summary_labels: {letter: 'A. 工程名'} dict for display.
        """
        self._write_sheet1_header()
        self._write_tasks()
        if summary_sections is None:
            summary_sections = list(self.subtotal_rows.keys())
        if summary_labels is None:
            summary_labels = {s: s for s in summary_sections}
        self._write_summary(summary_sections, summary_labels)
        self._write_adjustments()
        self._sheet1.freeze_panes = 'A5'
        self._finalized = True

    # ── Sheet 2: Phase 分割 ──

    def add_phase_sheet(self, phases, sheet_name='Phase分割',
                        mgmt_rate=None, risk_rate=None):
        """
        Add a phase split sheet.

        phases: list of dicts, each dict:
            {
                'name': 'Phase 1',
                'label': '日報・議事録 MVP',
                'sections': [('A. プロジェクト基盤', 'A', 1.0), ...]
                    # (display_label, section_letter, ratio) — ratio: 割合 (0.5 for 50%)
                'note': '8月リリース目標',
                'summary_note': '約100人日',  # optional
            }
        mgmt_rate, risk_rate: override sheet1's config if given
        """
        if not self._finalized:
            raise RuntimeError("Call finalize() before add_phase_sheet()")

        ws = self.wb.create_sheet(sheet_name)
        ws.column_dimensions['A'].width = 10
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 14
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 22

        ws.merge_cells('A1:E1')
        ws['A1'] = 'Phase 分割提案'
        ws['A1'].font = self.styles.TITLE_FONT

        for col, h in enumerate(['Phase', '工程', 'PERT純工数', '調整後工数', '備考'], 1):
            cell = ws.cell(row=3, column=col, value=h)
            cell.font = self.styles.HEADER_FONT
            cell.fill = self.styles.HEADER_FILL
            cell.alignment = self.styles.CENTER
            cell.border = self.styles.THIN_BORDER

        mr = mgmt_rate if mgmt_rate is not None else self.config['mgmt_rate']
        rr = risk_rate if risk_rate is not None else self.config['risk_rate']
        r = 4
        phase_totals = []

        for phase in phases:
            start_r = r
            for label, sec, ratio in phase['sections']:
                ws.cell(row=r, column=1, value=phase['name'])
                ws.cell(row=r, column=2, value=label)
                if ratio != 1.0:
                    ws.cell(row=r, column=3, value=f"='WBS+PERT'!F{self.subtotal_rows[sec]}*{ratio}")
                else:
                    ws.cell(row=r, column=3, value=f"='WBS+PERT'!F{self.subtotal_rows[sec]}")
                ws.cell(row=r, column=3).number_format = '0.00'
                ws.cell(row=r, column=4, value=f'=C{r}*(1+{mr})*(1+{rr})')
                ws.cell(row=r, column=4).number_format = '0.00'
                ws.cell(row=r, column=5, value=phase.get('note', ''))
                for c in range(1, 6):
                    ws.cell(row=r, column=c).border = self.styles.THIN_BORDER
                r += 1

            # Phase subtotal
            ws.merge_cells(f'A{r}:B{r}')
            ws.cell(row=r, column=1, value=f'{phase["name"]} 合計').font = self.styles.BOLD_FONT
            ws.cell(row=r, column=3, value=f'=SUM(C{start_r}:C{r-1})').number_format = '0.00'
            ws.cell(row=r, column=3).font = self.styles.BOLD_FONT
            ws.cell(row=r, column=4, value=f'=SUM(D{start_r}:D{r-1})').number_format = '0.00'
            ws.cell(row=r, column=4).font = self.styles.BOLD_FONT
            sn = phase.get('summary_note', '')
            ws.cell(row=r, column=5, value=sn)
            for c in range(1, 6):
                ws.cell(row=r, column=c).fill = self.styles.SUMMARY_FILL
                ws.cell(row=r, column=c).border = self.styles.THIN_BORDER
            phase_totals.append(r)
            r += 1

        # Grand total
        r += 1
        ws.cell(row=r, column=2, value='全体合計').font = Font(bold=True, size=12)
        refs = '+'.join([f'D{pt}' for pt in phase_totals])
        ws.cell(row=r, column=4, value=f'={refs}').number_format = '0.00'
        ws.cell(row=r, column=4).font = Font(bold=True, size=12)

        ws.freeze_panes = 'A4'

    # ── Sheet 3: 仮定一覧 ──

    def add_assumptions_sheet(self, assumptions, sheet_name='仮定一覧'):
        """
        Add an assumptions/reference sheet.

        assumptions: list of (assumption_text, impact_if_changed) tuples.
        """
        ws = self.wb.create_sheet(sheet_name)
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 35

        ws.merge_cells('A1:C1')
        ws['A1'] = '主要仮定と前提条件'
        ws['A1'].font = self.styles.TITLE_FONT

        for col, h in enumerate(['#', '仮定', '変動した場合の影響'], 1):
            cell = ws.cell(row=3, column=col, value=h)
            cell.font = self.styles.HEADER_FONT
            cell.fill = self.styles.HEADER_FILL
            cell.border = self.styles.THIN_BORDER

        for i, (assumption, impact) in enumerate(assumptions, 1):
            ws.cell(row=i+3, column=1, value=f'#{i}')
            ws.cell(row=i+3, column=2, value=assumption).alignment = self.styles.WRAP
            ws.cell(row=i+3, column=2).font = self.styles.BOLD_FONT
            ws.cell(row=i+3, column=3, value=impact).alignment = self.styles.WRAP
            for c in range(1, 4):
                ws.cell(row=i+3, column=c).border = self.styles.THIN_BORDER

    # ── Save ──

    def save(self, path):
        self.wb.save(path)
        print(f'Saved: {path}')


# ── Convenience: generate from a simple dict structure ──

def from_dict(project: dict, output_path: str):
    """
    Quick generation from a declarative dict.

    project = {
        'title': '案件名 工数見積',
        'subtitle': '作成日: 2026-05-19 | ...',
        'config': {  # optional overrides
            'skill_coef': 1.0, 'mgmt_rate': 0.20, 'risk_rate': 0.15,
            'skill_note': '...', 'mgmt_note': '...', 'risk_note': '...',
        },
        'sections': [
            ('A', '【A. 工程名】', [
                ('A1', 'タスク名', o, m, p, '備考'),
                ...
            ]),
        ],
        'summary_sections': ['A','B',...],
        'summary_labels': {'A': 'A. xx', ...},
        'phases': [  # optional
            {'name': 'Phase 1', 'label': '...', 'sections': [...], 'note': '...'},
        ],
        'assumptions': [  # optional
            ('仮定1', '影響1'),
        ],
    }
    """
    wb = EstimateWorkbook()
    wb.set_meta(
        title=project['title'],
        subtitle=project.get('subtitle', ''),
        config=project.get('config')
    )
    for letter, label, tasks in project['sections']:
        wb.add_section(label)
        for t in tasks:
            tid, name, o, m, p = t[0], t[1], t[2], t[3], t[4]
            note = t[5] if len(t) > 5 else ''
            wb.add_task(tid, name, o, m, p, note)
        wb.add_subtotal(letter, f'{letter}. {label.strip("【】").split("】")[-1] if "】" in label else label} 小計')

    wb.finalize(
        summary_sections=project.get('summary_sections'),
        summary_labels=project.get('summary_labels')
    )
    if 'phases' in project:
        wb.add_phase_sheet(project['phases'])
    if 'assumptions' in project:
        wb.add_assumptions_sheet(project['assumptions'])

    wb.save(output_path)
    return wb


if __name__ == '__main__':
    # Example usage (abstract — replace with real project data)
    project = {
        'title': 'サンプル案件 工数見積',
        'subtitle': '作成日: 2026-XX-XX | 開発基準: 一般開発者',
        'config': {},
        'sections': [
            ('A', '【A. サンプル工程】', [
                ('A1', 'サンプルタスク1', 1, 2, 3, ''),
                ('A2', 'サンプルタスク2', 2, 3, 5, '備考例'),
            ]),
            ('B', '【B. 別工程】', [
                ('B1', '別タスク1', 1, 1.5, 3, ''),
            ]),
        ],
        'summary_sections': ['A', 'B'],
        'summary_labels': {'A': 'A. サンプル工程', 'B': 'B. 別工程'},
        'assumptions': [
            ('仮定の例1', '変動した場合 ±X人日'),
            ('仮定の例2', '変動した場合 +Y人日'),
        ],
    }
    from_dict(project, '/tmp/sample_estimate.xlsx')
