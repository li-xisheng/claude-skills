#!/usr/bin/env node
/**
 * generate_proposal.js
 * 顶级咨询公司风格 .docx 提案书生成器
 *
 * 用法: node generate_proposal.js content.json output.docx
 *
 * content.json 结构参见 references/sample_content.json
 */

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageBreak, Header, Footer, PageNumber, LevelFormat
} = require('docx');

// ============ 咨询风格配色 ============
const COLOR = {
  TITLE: '1F3864',
  H1: '1F3864',
  H2: '2E4C8C',
  TEXT: '2E2E2E',
  MUTED: '666666',
  TABLE_HEADER_BG: 'D5E8F0',
  TABLE_BORDER: 'CCCCCC',
  ACCENT: 'C00000',
};

function getFont(language) {
  if (language === 'zh') return 'Microsoft YaHei';
  if (language === 'ja') return 'Meiryo';
  return 'Calibri';
}

// ============ 元素构造器 ============
function txt(text, opts = {}) {
  return new TextRun({
    text: String(text),
    font: { name: opts.font || 'Meiryo', eastAsia: opts.font || 'Meiryo' },
    size: opts.size || 20,
    bold: opts.bold || false,
    color: opts.color || COLOR.TEXT,
    italics: false,
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0 },
    alignment: opts.align || AlignmentType.LEFT,
    children: Array.isArray(text) ? text : [txt(text, opts)],
  });
}

function h1(text, font) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    children: [new TextRun({
      text, bold: true, color: COLOR.H1, size: 30,
      font: { name: font, eastAsia: font },
    })],
  });
}

function h2(text, font) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 100 },
    children: [new TextRun({
      text: '■ ' + text, bold: true, color: COLOR.H2, size: 24,
      font: { name: font, eastAsia: font },
    })],
  });
}

const thinBorder = { style: BorderStyle.SINGLE, size: 4, color: COLOR.TABLE_BORDER };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function tableCell(text, opts = {}) {
  const isHeader = opts.header;
  return new TableCell({
    borders: cellBorders,
    width: { size: opts.width || 3000, type: WidthType.DXA },
    shading: isHeader
      ? { fill: COLOR.TABLE_HEADER_BG, type: ShadingType.CLEAR }
      : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      children: [txt(text, { bold: isHeader, font: opts.font, size: 19 })],
    })],
  });
}

function buildTable(rows, widths, font) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, ri) =>
      new TableRow({
        children: row.map((cell, ci) =>
          tableCell(cell, { header: ri === 0, width: widths[ci], font }))
      })
    ),
  });
}

// ============ SCQA 框（执行摘要核心元素） ============
function scqaBlock(scqa, font) {
  const labels = { S: 'Situation（情境）', C: 'Complication（冲突）', Q: 'Question（問題）', A: 'Answer（提案）' };
  const rows = [
    ['S', 'Situation', scqa.situation],
    ['C', 'Complication', scqa.complication],
    ['Q', 'Question', scqa.question],
    ['A', 'Answer', scqa.answer],
  ];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [720, 8640],
    rows: rows.map(([code, , text]) => new TableRow({
      children: [
        new TableCell({
          borders: cellBorders,
          width: { size: 720, type: WidthType.DXA },
          shading: { fill: COLOR.H1, type: ShadingType.CLEAR },
          margins: { top: 100, bottom: 100, left: 80, right: 80 },
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: code, bold: true, color: 'FFFFFF', size: 28,
              font: { name: font, eastAsia: font } })],
          })],
        }),
        new TableCell({
          borders: cellBorders,
          width: { size: 8640, type: WidthType.DXA },
          margins: { top: 100, bottom: 100, left: 160, right: 160 },
          children: [para(text, { font })],
        }),
      ],
    })),
  });
}

// ============ 章节渲染 ============
function renderSection(section, font) {
  const out = [];
  if (section.heading) out.push(h1(section.heading, font));
  for (const block of section.content || []) {
    if (typeof block === 'string') {
      out.push(para(block, { font }));
    } else if (block.type === 'h2') {
      out.push(h2(block.text, font));
    } else if (block.type === 'paragraph') {
      out.push(para(block.text, { font }));
    } else if (block.type === 'bullet') {
      out.push(new Paragraph({
        numbering: { reference: 'bullets', level: 0 },
        children: [txt(block.text, { font })],
      }));
    } else if (block.type === 'table') {
      out.push(buildTable(block.rows, block.widths || block.rows[0].map(() => Math.floor(9360 / block.rows[0].length)), font));
      out.push(para('', { font, after: 120 }));
    } else if (block.type === 'pagebreak') {
      out.push(new Paragraph({ children: [new PageBreak()] }));
    }
  }
  return out;
}

// ============ 主函数 ============
function build(content) {
  const font = getFont(content.language || 'ja');
  const children = [];

  // 封面
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 2000, after: 400 },
    children: [new TextRun({
      text: content.title, bold: true, color: COLOR.TITLE, size: 44,
      font: { name: font, eastAsia: font },
    })],
  }));
  if (content.subtitle) {
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 1200 },
      children: [new TextRun({
        text: content.subtitle, color: COLOR.H2, size: 26,
        font: { name: font, eastAsia: font },
      })],
    }));
  }

  // 元信息表
  const m = content.meta || {};
  children.push(buildTable([
    [m.authorLabel || '作成者 / 部署', `${m.author || ''}  /  ${m.department || ''}`],
    [m.dateLabel || '日付', m.date || ''],
    [m.classLabel || '区分', m.classification || ''],
  ], [3000, 6360], font));

  children.push(new Paragraph({ children: [new PageBreak()] }));

  // 执行摘要
  if (content.executive_summary) {
    children.push(h1(content.executive_summary.heading || 'エグゼクティブサマリー', font));
    children.push(scqaBlock(content.executive_summary, font));
    children.push(para('', { font }));
    if (content.executive_summary.approvals && content.executive_summary.approvals.length) {
      children.push(h2('審批申請', font));
      content.executive_summary.approvals.forEach((a, i) => {
        children.push(para(`${['①','②','③','④','⑤'][i] || (i+1)+'.'} ${a}`, { font }));
      });
    }
    children.push(new Paragraph({ children: [new PageBreak()] }));
  }

  // 各章节
  for (const section of content.sections || []) {
    children.push(...renderSection(section, font));
  }

  // 构建 Document
  return new Document({
    creator: m.author || 'Consulting Advisor',
    title: content.title,
    numbering: {
      config: [{
        reference: 'bullets',
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: '•',
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      }],
    },
    styles: {
      default: { document: { run: { font: { name: font, eastAsia: font }, size: 20 } } },
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 }, // A4
          margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({
              text: `${content.title}　【${m.classification || '社外秘'}】`,
              color: COLOR.MUTED, size: 16,
              font: { name: font, eastAsia: font },
            })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: '- ', color: COLOR.MUTED, size: 16 }),
              new TextRun({ children: [PageNumber.CURRENT], color: COLOR.MUTED, size: 16 }),
              new TextRun({ text: ' -', color: COLOR.MUTED, size: 16 }),
            ],
          })],
        }),
      },
      children,
    }],
  });
}

// ============ CLI ============
async function main() {
  const [, , inputPath, outputPath] = process.argv;
  if (!inputPath || !outputPath) {
    console.error('Usage: node generate_proposal.js <content.json> <output.docx>');
    process.exit(1);
  }
  const content = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
  const doc = build(content);
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(`✓ Generated: ${outputPath} (${buffer.length} bytes)`);
}

if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });

module.exports = { build };
