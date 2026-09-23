/**
 * 次回定例用の課題リスト作成スクリプト（Excel Online / Office Scripts）
 *
 * 課題リスト運用ルール⑤の自動化。定例で確認した課題リストのコピーに対して、
 *   - 課題の行（7行目以降）の文字をすべて黒字に戻す
 *   - 右上の定例日（O1）を次回定例日にする
 * を行う。次回に向けた追記は、各自がこのファイルに赤字で書き足す（運用ルール①）。
 */

const SHEET_NAME = "課題リスト";
const FIRST_ROW = 7;
const LAST_COL = "P";
const DATE_CELL = "O1";

// nextMeetingDate: "YYYY-MM-DD"
function main(workbook: ExcelScript.Workbook, nextMeetingDate: string): string {
  const ws = workbook.getWorksheet(SHEET_NAME) ?? workbook.getWorksheets()[0];
  const used = ws.getUsedRange();
  if (used) {
    const lastRow = used.getRowIndex() + used.getRowCount();
    if (lastRow >= FIRST_ROW) {
      ws.getRange(`A${FIRST_ROW}:${LAST_COL}${lastRow}`).getFormat().getFont().setColor("#000000");
    }
  }

  const [y, m, d] = nextMeetingDate.split("-").map(Number);
  if (!y || !m || !d) return `次回定例日「${nextMeetingDate}」を読み取れないため、定例日（${DATE_CELL}）は変更していません`;
  ws.getRange(DATE_CELL).setValue(`${y}/${m}/${d}`);
  return "OK";
}
