/**
 * 議題シート読み取りスクリプト（Excel Online / Office Scripts）
 *
 * メールで送付した「打合せ会議記録」ブック（議題記入済み）から、
 * 議題No・議題本文・参加者名簿を JSON で返す。
 * Power Automate の「スクリプトの実行」アクションから呼び出し、
 * 戻り値をそのまま AI プロンプトの入力にする。
 */

interface AgendaItem {
  no: number;
  row: number;
  text: string;
}

interface RosterEntry {
  company: string;
  name: string;
}

interface AgendaResult {
  project: string;
  title: string;
  items: AgendaItem[];
  roster: RosterEntry[];
}

// フォーマットの行範囲（1ページ目・2ページ目の議題欄と参加者名簿）
const ITEM_PAGES: number[][] = [[17, 42], [47, 78]];
const ROSTER_FIRST_ROW = 88;
const ROSTER_LAST_ROW = 120;
// 議題本文は F〜T 列
const TEXT_FIRST_COL = "F";
const TEXT_LAST_COL = "T";

function main(workbook: ExcelScript.Workbook): string {
  const ws = workbook.getWorksheets()[0];

  const items: AgendaItem[] = [];
  for (const [first, last] of ITEM_PAGES) {
    const noValues = ws.getRange(`E${first}:E${last}`).getValues();
    const textValues = ws.getRange(`${TEXT_FIRST_COL}${first}:${TEXT_LAST_COL}${last}`).getValues();
    let current: AgendaItem | undefined;
    for (let i = 0; i < noValues.length; i++) {
      const row = first + i;
      const no = toNumber(noValues[i][0]);
      if (no !== undefined) {
        current = { no, row, text: "" };
        items.push(current);
      }
      if (!current) continue;
      const line = textValues[i]
        .map((v) => String(v).trim())
        .filter((v) => v !== "")
        .join(" ");
      if (line !== "") current.text += (current.text === "" ? "" : "\n") + line;
    }
  }

  const roster: RosterEntry[] = [];
  const rosterValues = ws.getRange(`G${ROSTER_FIRST_ROW}:G${ROSTER_LAST_ROW}`).getValues();
  let company = "";
  for (const [v] of rosterValues) {
    const s = String(v).trim();
    if (s === "") continue;
    // 氏名は姓名の間に空白がある。空白なしの行は会社名の見出しとして扱う
    if (/[\s　]/.test(s)) {
      roster.push({ company, name: s });
    } else {
      company = s;
    }
  }

  const result: AgendaResult = {
    project: String(ws.getRange("C4").getValue()).trim(),
    title: String(ws.getRange("N1").getValue()).trim(),
    items,
    roster,
  };
  return JSON.stringify(result);
}

function toNumber(v: string | number | boolean): number | undefined {
  if (typeof v === "number") return v;
  const s = String(v).trim().replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
  return /^\d+$/.test(s) ? Number(s) : undefined;
}
