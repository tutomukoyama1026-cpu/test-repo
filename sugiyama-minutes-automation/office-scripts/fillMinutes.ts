/**
 * 議事録書き込みスクリプト（Excel Online / Office Scripts）
 *
 * 議題記入済みの「打合せ会議記録」ブックに、AI が文字起こしから作成した
 * JSON（prompts/01_議事録作成プロンプト.md の出力形式）を書き込む。
 *   - 年月日・時間・場所
 *   - 各議題No の「打合せ結果」欄（V列）
 *   - 議題外で出た案件（最終議題の後ろに追記）
 *   - 参加者名簿の 現地／WEB 欄にチェック（セル内チェックボックスなら TRUE、なければ ○）
 *   - 次回・次々回開催
 * 議題本文（F〜T列）には一切書き込まない。
 */

interface Action {
  task: string;
  owner: string;
  due: string;
}

interface ItemResult {
  no: number;
  title: string;
  status: string;
  result: string;
  actions: Action[];
}

interface Attendee {
  name: string;
  mode: string;
}

interface Schedule {
  date: string;
  weekday: string;
  start: string;
  end: string;
  place: string;
}

interface Minutes {
  meeting: { number: number; date: string; weekday: string; start: string; end: string; place: string };
  attendees: Attendee[];
  items: ItemResult[];
  new_items: ItemResult[];
  next_meeting?: Schedule;
  next_next_meeting?: Schedule;
}

const ITEM_PAGES: number[][] = [[17, 42], [47, 78]];
const RESULT_COL = "V";
// 結果欄（V〜AJ）1行に収める全角文字数の目安。印刷して溢れる場合はここを調整
const LINE_WIDTH = 34;
const ROSTER_FIRST_ROW = 88;
const ROSTER_LAST_ROW = 120;
const MARK = "○";

function main(workbook: ExcelScript.Workbook, minutesJson: string): string {
  const data: Minutes = JSON.parse(minutesJson);
  data.new_items = data.new_items ?? [];
  data.attendees = data.attendees ?? [];
  const ws = workbook.getWorksheets()[0];
  const log: string[] = [];

  writeHeader(ws, data);

  // 議題No → 書き込める行範囲
  const slots = findItemSlots(ws);
  for (const item of data.items) {
    const slot = slots.find((s) => s.no === item.no);
    if (!slot) {
      log.push(`議題No.${item.no} がシートに見つからないため議題外として追記`);
      data.new_items.push(item);
      continue;
    }
    writeLines(ws, slot.first, slot.last, formatResult(item));
  }

  appendNewItems(ws, slots, data.new_items, log);
  markAttendees(ws, data.attendees, log);

  if (data.next_meeting) ws.getRange("K79").setValue(formatSchedule(data.next_meeting));
  if (data.next_next_meeting) ws.getRange("K80").setValue(formatSchedule(data.next_next_meeting));

  return log.length === 0 ? "OK" : log.join("\n");
}

function writeHeader(ws: ExcelScript.Worksheet, data: Minutes) {
  const m = data.meeting;
  const title = String(ws.getRange("N1").getValue());
  ws.getRange("N1").setValue(title.replace(/第[0-9０-９]+回/, `第${m.number}回`).replace("議題", "議事録"));

  const [y, mo, d] = m.date.split("-").map(Number);
  ws.getRange("F6").setValue(y);
  ws.getRange("J6").setValue(mo);
  ws.getRange("L6").setValue(d);
  ws.getRange("N6").setValue(`(${m.weekday})`);

  const [sh, sm] = m.start.split(":").map(Number);
  const [eh, em] = m.end.split(":").map(Number);
  ws.getRange("F7").setValue(sh);
  ws.getRange("H7").setValue(sm);
  ws.getRange("K7").setValue(eh);
  ws.getRange("M7").setValue(em);
  if (m.place) ws.getRange("F8").setValue(m.place);
}

interface Slot {
  no: number;
  first: number;
  last: number;
}

function findItemSlots(ws: ExcelScript.Worksheet): Slot[] {
  const slots: Slot[] = [];
  for (const [first, last] of ITEM_PAGES) {
    const values = ws.getRange(`E${first}:E${last}`).getValues();
    for (let i = 0; i < values.length; i++) {
      const no = toNumber(values[i][0]);
      if (no === undefined) continue;
      if (slots.length > 0 && slots[slots.length - 1].last >= first + i) {
        slots[slots.length - 1].last = first + i - 1;
      }
      slots.push({ no, first: first + i, last });
    }
  }
  return slots;
}

function formatResult(item: ItemResult): string {
  const lines = [`【${item.status}】${item.result}`];
  for (const a of item.actions) {
    lines.push(`→${a.owner}：${a.task}${a.due ? `（${a.due}まで）` : ""}`);
  }
  return lines.join("\n");
}

function writeLines(ws: ExcelScript.Worksheet, first: number, last: number, text: string) {
  const lines = wrap(text, LINE_WIDTH);
  const rows = last - first + 1;
  for (let i = 0; i < rows && i < lines.length; i++) {
    // 行が足りない場合は最終行に残りをまとめる
    const value = i === rows - 1 ? lines.slice(i).join("") : lines[i];
    ws.getRange(`${RESULT_COL}${first + i}`).setValue(value);
  }
}

function appendNewItems(ws: ExcelScript.Worksheet, slots: Slot[], items: ItemResult[], log: string[]) {
  if (items.length === 0) return;
  let nextNo = slots.reduce((max, s) => Math.max(max, s.no), 0) + 1;
  // 最終議題の本文が終わった次の空行から追記
  const lastSlot = slots[slots.length - 1];
  let row = lastSlot ? lastUsedRow(ws, lastSlot.first, lastSlot.last) + 2 : ITEM_PAGES[0][0];
  const pageEnd = ITEM_PAGES[ITEM_PAGES.length - 1][1];

  for (const item of items) {
    row = skipPageGap(row);
    const lines = wrap(formatResult(item), LINE_WIDTH);
    const needed = Math.max(lines.length, 1);
    if (row + needed - 1 > pageEnd) {
      log.push(`議題外「${item.title}」は書き込み欄が不足のため省略（要約.md には記載）`);
      continue;
    }
    ws.getRange(`E${row}`).setValue(nextNo++);
    ws.getRange(`F${row}`).setValue(`（議題外）${item.title}`);
    writeLines(ws, row, row + needed - 1, lines.join("\n"));
    row += needed + 1;
  }
}

// 1ページ目と2ページ目の間（見出し行）に掛かる場合は2ページ目の先頭へ
function skipPageGap(row: number): number {
  for (let p = 0; p < ITEM_PAGES.length - 1; p++) {
    if (row > ITEM_PAGES[p][1] && row < ITEM_PAGES[p + 1][0]) return ITEM_PAGES[p + 1][0];
  }
  return row;
}

function lastUsedRow(ws: ExcelScript.Worksheet, first: number, last: number): number {
  const values = ws.getRange(`E${first}:AJ${last}`).getValues();
  let used = first;
  values.forEach((r, i) => {
    if (r.some((v) => String(v).trim() !== "")) used = first + i;
  });
  return used;
}

function markAttendees(ws: ExcelScript.Worksheet, attendees: Attendee[], log: string[]) {
  const names = ws.getRange(`G${ROSTER_FIRST_ROW}:G${ROSTER_LAST_ROW}`).getValues().map((r) => normalize(String(r[0])));
  for (const a of attendees) {
    const i = names.indexOf(normalize(a.name));
    if (i < 0 || names[i] === "") {
      log.push(`参加者「${a.name}」が名簿にありません`);
      continue;
    }
    const cell = ws.getRange(`${a.mode === "WEB" ? "E" : "C"}${ROSTER_FIRST_ROW + i}`);
    // セル内チェックボックス（挿入→チェックボックス）なら TRUE、それ以外は ○
    cell.setValue(typeof cell.getValue() === "boolean" ? true : MARK);
  }
}

function formatSchedule(s: Schedule): string {
  const [, mo, d] = s.date.split("-").map(Number);
  return `${mo}/${d}(${s.weekday}) ${s.start}～${s.end}　${s.place}`;
}

// 全角=1、半角=0.5 で数えて折り返す
function wrap(text: string, width: number): string[] {
  const out: string[] = [];
  for (const para of text.split("\n")) {
    let line = "";
    let w = 0;
    for (const ch of para) {
      const cw = ch.charCodeAt(0) < 0x80 ? 0.5 : 1;
      if (w + cw > width) {
        out.push(line);
        line = "";
        w = 0;
      }
      line += ch;
      w += cw;
    }
    out.push(line);
  }
  return out;
}

function normalize(s: string): string {
  return s.replace(/[\s　]/g, "");
}

function toNumber(v: string | number | boolean): number | undefined {
  if (typeof v === "number") return v;
  const s = String(v).trim().replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
  return /^\d+$/.test(s) ? Number(s) : undefined;
}
