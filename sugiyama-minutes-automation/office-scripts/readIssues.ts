/**
 * 課題リスト読み取りスクリプト（Excel Online / Office Scripts）
 *
 * 定例資料として配布された課題リストから、課題No ごとの概要・経過・期限を JSON で返す。
 * セルに収まらず複数行に分けて書かれた課題（同じ No が続く行、経過が「（続き）」で始まる行）は
 * 1件にまとめる。戻り値は議事録作成プロンプトの {{課題リストJSON}} に渡す。
 */

interface Issue {
  no: string;
  categories: string;
  issued: string;
  from: string;
  summary: string;
  parties: string;
  history: string;
  due: string;
  done: string;
}

const SHEET_NAME = "課題リスト";
const FIRST_ROW = 7;
// 経過が長い課題は末尾だけ渡す（AI に渡す文字数を抑えるため）
const HISTORY_TAIL = 800;

function main(workbook: ExcelScript.Workbook): string {
  const ws = workbook.getWorksheet(SHEET_NAME) ?? workbook.getWorksheets()[0];
  const used = ws.getUsedRange();
  if (!used) return "[]";
  const lastRow = used.getRowIndex() + used.getRowCount();
  if (lastRow < FIRST_ROW) return "[]";

  // 対象区分（B〜G列）の見出しは4行目
  const categoryNames = ws.getRange("B4:G4").getTexts()[0].map((t) => t.trim());
  const texts = ws.getRange(`A${FIRST_ROW}:O${lastRow}`).getTexts();
  const issues: Issue[] = [];
  for (const r of texts) {
    const no = r[0].trim();
    if (no === "") continue;
    const history = r[11].replace(/^（続き）\s*/, "").trim();
    const prev = issues.length > 0 ? issues[issues.length - 1] : undefined;
    if (prev && prev.no === no) {
      if (history !== "") prev.history += "\n" + history;
      continue;
    }
    issues.push({
      no,
      categories: categoryNames.filter((name, i) => name !== "" && r[1 + i].trim() === "〇").join("・"),
      issued: r[7].trim(),
      from: r[8].trim(),
      summary: r[9].trim(),
      parties: r[10].trim(),
      history,
      due: r[13].trim(),
      done: r[14].trim(),
    });
  }

  for (const issue of issues) {
    issue.history = issue.history.replace(/\n{2,}/g, "\n").trim();
    if (issue.history.length > HISTORY_TAIL) issue.history = "…" + issue.history.slice(-HISTORY_TAIL);
  }
  return JSON.stringify(issues);
}
