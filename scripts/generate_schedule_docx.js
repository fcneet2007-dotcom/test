#!/usr/bin/env node
/**
 * schedule_data.json から月間予定表の Word 文書(.docx)を生成する。
 *
 * 使い方: node scripts/generate_schedule_docx.js output/schedule_data.json output/予定表.docx
 */

const fs = require("fs");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, PageNumber,
  Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, VerticalAlign,
  WidthType, Packer,
} = require("docx");

const FONT = "Yu Gothic";
const COLS = [1100, 1500, 5600, 2200]; // 日付 / 時間 / 予定 / 場所・備考
const TABLE_WIDTH = COLS.reduce((a, b) => a + b, 0);

const COLOR = {
  header: "2F5496",
  headerText: "FFFFFF",
  saturday: "DEEAF6",
  sunday: "FBE4E4",
  allDay: "FFF2CC",
  task: "E2F3F9", // ToDo リストのタスク（カレンダー上の水色に合わせる）
  border: "BFBFBF",
  muted: "808080",
};

const [dataPath, outPath] = process.argv.slice(2);
if (!dataPath || !outPath) {
  console.error("usage: node generate_schedule_docx.js <schedule_data.json> <out.docx>");
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

const text = (value, opts = {}) =>
  new TextRun({ text: value, font: FONT, size: opts.size || 20, bold: !!opts.bold, color: opts.color });

const para = (value, opts = {}) =>
  new Paragraph({
    alignment: opts.alignment,
    spacing: { before: opts.before || 0, after: opts.after || 0 },
    children: Array.isArray(value) ? value : [text(value, opts)],
  });

function cell(children, opts = {}) {
  return new TableCell({
    width: { size: opts.width, type: WidthType.DXA },
    rowSpan: opts.rowSpan,
    verticalAlign: opts.verticalAlign || VerticalAlign.CENTER,
    shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill, color: "auto" } : undefined,
    margins: { top: 40, bottom: 40, left: 90, right: 90 },
    children,
  });
}

function headerRow() {
  const labels = ["日付", "時間", "予定", "場所・備考"];
  return new TableRow({
    tableHeader: true,
    children: labels.map((label, i) =>
      cell([para(label, { bold: true, color: COLOR.headerText, alignment: AlignmentType.CENTER })],
        { width: COLS[i], fill: COLOR.header })),
  });
}

/** 日付セル。土日祝は色を変え、祝日名を添える。 */
function dateCell(day, rowSpan) {
  const fill = day.holiday || day.is_sunday ? COLOR.sunday : day.is_saturday ? COLOR.saturday : undefined;
  const color = day.holiday || day.is_sunday ? "C00000" : day.is_saturday ? "1F4E79" : undefined;
  const children = [
    para(`${data.month}/${day.day}`, { bold: true, alignment: AlignmentType.CENTER, color }),
    para(`(${day.weekday})`, { alignment: AlignmentType.CENTER, size: 18, color }),
  ];
  if (day.holiday) {
    children.push(para(day.holiday, { alignment: AlignmentType.CENTER, size: 15, color }));
  }
  return cell(children, { width: COLS[0], rowSpan, fill, verticalAlign: VerticalAlign.TOP });
}

function eventRows(day) {
  if (day.events.length === 0) {
    return [new TableRow({
      children: [
        dateCell(day, 1),
        cell([para("—", { alignment: AlignmentType.CENTER, color: COLOR.muted })], { width: COLS[1] }),
        cell([para("予定なし", { color: COLOR.muted })], { width: COLS[2] }),
        cell([para("")], { width: COLS[3] }),
      ],
    })];
  }

  return day.events.map((event, index) => {
    const fill = event.is_task ? COLOR.task : event.all_day ? COLOR.allDay : undefined;
    const label = event.calendar ? `[${event.calendar}]` : "";
    const detail = [label, event.location, event.note].filter(Boolean).join(" / ");
    // タスクは頭に □ を付けて、当日チェックできるようにする
    const title = event.is_task ? `□ ${event.summary}` : event.summary;
    return new TableRow({
      children: [
        ...(index === 0 ? [dateCell(day, day.events.length)] : []),
        cell([para(event.time, { alignment: AlignmentType.CENTER, size: 18 })], { width: COLS[1], fill }),
        cell([para(title, { bold: event.all_day })], { width: COLS[2], fill,
          verticalAlign: VerticalAlign.CENTER }),
        cell([para(detail, { size: 18, color: detail ? undefined : COLOR.muted })], { width: COLS[3], fill }),
      ],
    });
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: COLOR.border };
const table = new Table({
  columnWidths: COLS,
  width: { size: TABLE_WIDTH, type: WidthType.DXA },
  borders: { top: border, bottom: border, left: border, right: border,
    insideHorizontal: border, insideVertical: border },
  rows: [headerRow(), ...data.days.flatMap(eventRows)],
});

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [{
    properties: {
      page: { margin: { top: 720, bottom: 720, left: 720, right: 720 } },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ font: FONT, size: 16, color: COLOR.muted,
            children: ["", PageNumber.CURRENT, " / ", PageNumber.TOTAL_PAGES] })],
        })],
      }),
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [text(data.title || `${data.year}年${data.month}月 予定表`, { bold: true, size: 32 })],
      }),
      para(`Google カレンダーより作成 ／ 予定 ${data.total_events} 件 ／ 作成日 ${data.generated_at}`,
        { alignment: AlignmentType.CENTER, size: 18, color: COLOR.muted, after: 180 }),
      table,
      para("※ 黄色の行は終日予定、水色の行は ToDo リストのタスク（□ 付き）です。"
        + "土曜は青、日曜・祝日は赤で表示しています。",
        { size: 16, color: COLOR.muted, before: 160 }),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log(`${outPath}: ${data.total_events} 件を書き出しました`);
});
