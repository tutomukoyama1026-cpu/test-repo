# Pythonスニペット by Workato：議事録への書き込み内容の作成
#
# AI（LLM API）の回答から、議題ファイルに書き込むセルと値を作る。
# 書き込み自体はレシピ側で、writes の1件ごとに Graph の range PATCH を呼ぶ。
#   - 表題（N1）の「第N回」「議題」→「議事録」
#   - 各議題No の「打合せ結果」欄（V列）。議題の行数を超える分は最終行にまとめる
#   - 議題外で出た案件（最終議題の後ろに追記）
#   - 参加者名簿の 現地／WEB チェックボックス（リンク先の非表示列 AM・AN に TRUE。ほかは FALSE）
#   - 次回・次々回開催（K79・K80）
# 年月日・時間・場所は担当者が議題に書いたものをそのまま使う（書き換えない）。
#
# 入力  values         議題ファイル A1:AN120 の表示文字列（p3 と同じもの）
#       llm_text       LLM API の回答（JSON。前後の説明文やコードブロック記号があってもよい）
#       meeting_date   開催日（YYYY-MM-DD）
#       number         回数（2桁）
# 出力  ok, writes（[{"address": "V17:V20", "values": [[...], ...]}] の JSON）,
#       markdown, open_items_markdown, next_meeting_date（YYYY-MM-DD）,
#       next_meeting_file_date（YYYYMMDD）, next_meeting_source（会議の発言／7日後）, log

import json
import re
from datetime import date, timedelta

ITEM_PAGES = [(17, 42), (47, 78)]
RESULT_COL = "V"
LINE_WIDTH = 34  # 結果欄（V〜AJ）1行の全角文字数の目安
ROSTER = (88, 120)
ONSITE_COL, WEB_COL = "AM", "AN"


def col(letters):
    n = 0
    for c in letters:
        n = n * 26 + ord(c) - 64
    return n - 1


def cell(v, addr):
    m = re.fullmatch(r"([A-Z]+)(\d+)", addr)
    r, c = int(m.group(2)) - 1, col(m.group(1))
    return str(v[r][c]).strip() if r < len(v) and c < len(v[r]) else ""


def to_no(s):
    s = str(s).strip().translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return int(s) if s.isdigit() else None


def parse_llm(text):
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    start, end = s.find("{"), s.rfind("}")
    return json.loads(s[start:end + 1])


def wrap(text, width):
    out = []
    for para in text.split("\n"):
        line, w = "", 0.0
        for ch in para:
            cw = 0.5 if ord(ch) < 0x80 else 1.0
            if w + cw > width:
                out.append(line)
                line, w = "", 0.0
            line += ch
            w += cw
        out.append(line)
    return out


def format_result(item):
    lines = [f"【{item.get('status', '')}】{item.get('result', '')}"]
    for a in item.get("actions") or []:
        due = f"（{a['due']}まで）" if a.get("due") else ""
        lines.append(f"→{a.get('owner', '')}：{a.get('task', '')}{due}")
    return "\n".join(lines)


def find_slots(v):
    slots = []
    for first, last in ITEM_PAGES:
        for row in range(first, last + 1):
            no = to_no(cell(v, f"E{row}"))
            if no is None:
                continue
            if slots and slots[-1]["last"] >= row:
                slots[-1]["last"] = row - 1
            slots.append({"no": no, "first": row, "last": last})
    return slots


def skip_page_gap(row):
    for (_, end), (start, _) in zip(ITEM_PAGES, ITEM_PAGES[1:]):
        if end < row < start:
            return start
    return row


def last_used_row(v, first, last):
    used = first
    for row in range(first, last + 1):
        if any(str(x).strip() for x in v[row - 1][col("E"):col("AJ") + 1]):
            used = row
    return used


def schedule(s):
    if not s or not s.get("date"):
        return ""
    _, mo, d = (int(x) for x in s["date"].split("-"))
    return f"{mo}/{d}({s.get('weekday', '')}) {s.get('start', '')}～{s.get('end', '')}　{s.get('place', '')}"


def main(input):
    v = json.loads(input["values"])
    log = []
    try:
        data = parse_llm(input["llm_text"])
    except Exception as e:  # AI の回答が JSON として読めない
        return {"ok": False, "writes": "[]", "markdown": "", "open_items_markdown": "",
                "next_meeting_date": "", "next_meeting_file_date": "", "next_meeting_source": "",
                "log": f"AI の回答を読み取れませんでした：{e}"}

    cells = {}  # "V17" -> 値

    title = cell(v, "N1")
    cells["N1"] = re.sub(r"第[0-9０-９]+回", f"第{int(input['number'] or 0)}回", title).replace("議題", "議事録")

    slots = find_slots(v)
    new_items = list(data.get("new_items") or [])
    for item in data.get("items") or []:
        slot = next((s for s in slots if s["no"] == item.get("no")), None)
        if not slot:
            log.append(f"議題No.{item.get('no')} がシートに見つからないため議題外として追記")
            new_items.append(item)
            continue
        lines = wrap(format_result(item), LINE_WIDTH)
        rows = slot["last"] - slot["first"] + 1
        if len(lines) > rows:
            log.append(f"議題No.{item.get('no')} は結果欄の行が足りないため、最終行にまとめました")
            lines = lines[:rows - 1] + ["".join(lines[rows - 1:])]
        for i, line in enumerate(lines):
            cells[f"{RESULT_COL}{slot['first'] + i}"] = line

    new_items = [i for i in new_items if i.get("title") or i.get("result")]
    if new_items:
        next_no = max((s["no"] for s in slots), default=0) + 1
        row = last_used_row(v, slots[-1]["first"], slots[-1]["last"]) + 2 if slots else ITEM_PAGES[0][0]
        for used in [r for r in range(row, ITEM_PAGES[-1][1] + 1) if f"{RESULT_COL}{r}" in cells]:
            row = max(row, used + 2)
        page_end = ITEM_PAGES[-1][1]
        for item in new_items:
            row = skip_page_gap(row)
            lines = wrap(format_result(item), LINE_WIDTH)
            if row + len(lines) - 1 > page_end:
                log.append(f"議題外「{item.get('title', '')}」は書き込み欄が足りないため省略（議事録要約には記載）")
                continue
            cells[f"E{row}"] = next_no
            cells[f"F{row}"] = f"（議題外）{item.get('title', '')}"
            for i, line in enumerate(lines):
                cells[f"{RESULT_COL}{row + i}"] = line
            next_no += 1
            row += len(lines) + 1

    # 出席チェック：名簿の全行をいったん FALSE にしてから、出席者の行だけ TRUE
    names = [re.sub(r"[\s　]", "", cell(v, f"G{r}")) for r in range(ROSTER[0], ROSTER[1] + 1)]
    checks = [[False, False] for _ in names]
    for a in data.get("attendees") or []:
        n = re.sub(r"[\s　]", "", a.get("name", ""))
        if n and n in names:
            checks[names.index(n)][1 if a.get("mode") == "WEB" else 0] = True
        else:
            log.append(f"参加者「{a.get('name', '')}」が名簿にありません")

    if schedule(data.get("next_meeting")):
        cells["K79"] = schedule(data.get("next_meeting"))
    if schedule(data.get("next_next_meeting")):
        cells["K80"] = schedule(data.get("next_next_meeting"))

    # 同じ列で縦に続くセルは1回の書き込みにまとめる
    writes = []
    by_col = {}
    for addr, val in cells.items():
        m = re.fullmatch(r"([A-Z]+)(\d+)", addr)
        by_col.setdefault(m.group(1), []).append((int(m.group(2)), val))
    for c, rows in by_col.items():
        rows.sort()
        run = [rows[0]]
        for r, val in rows[1:] + [(None, None)]:
            if r is not None and r == run[-1][0] + 1:
                run.append((r, val))
                continue
            addr = f"{c}{run[0][0]}" if len(run) == 1 else f"{c}{run[0][0]}:{c}{run[-1][0]}"
            writes.append({"address": addr, "values": [[x] for _, x in run]})
            if r is not None:
                run = [(r, val)]
    writes.append({"address": f"{ONSITE_COL}{ROSTER[0]}:{WEB_COL}{ROSTER[1]}", "values": checks})

    # 次回定例日：会議で話された日付。なければ開催日の7日後（毎週開催のため）
    nm = (data.get("next_meeting") or {}).get("date", "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", nm or ""):
        next_date, source = nm, "会議の発言"
    else:
        next_date = (date.fromisoformat(input["meeting_date"]) + timedelta(days=7)).isoformat()
        source = "7日後（会議で次回の日付が話されなかったため）"
        log.append(f"次回定例日が会議で話されなかったため、{next_date} として課題リストを作りました")

    return {
        "ok": True,
        "writes": json.dumps(writes, ensure_ascii=False),
        "markdown": data.get("markdown", ""),
        "open_items_markdown": data.get("open_items_markdown", ""),
        "next_meeting_date": next_date,
        "next_meeting_file_date": next_date.replace("-", ""),
        "next_meeting_source": source,
        "log": "\n".join(log),
    }
