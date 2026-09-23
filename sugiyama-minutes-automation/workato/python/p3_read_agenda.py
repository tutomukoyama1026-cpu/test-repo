# Pythonスニペット by Workato：議題ファイルの読み取り
#
# 入力  values   議題ファイル 1枚目のシート A1:AN120 の表示文字列（Graph の range の text。2次元配列の JSON）
# 出力  agenda_json    AI に渡す議題（工事名・表題・開催情報・議題No と本文・参加者名簿）
#       meeting_info   開催情報の文字列（AI の {{開催情報}} に渡す）

import json
import re

ITEM_PAGES = [(17, 42), (47, 78)]
ROSTER = (88, 120)


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
    s = s.strip().translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return int(s) if s.isdigit() else None


def main(input):
    v = json.loads(input["values"])

    items = []
    for first, last in ITEM_PAGES:
        current = None
        for row in range(first, last + 1):
            no = to_no(cell(v, f"E{row}"))
            if no is not None:
                current = {"no": no, "row": row, "text": ""}
                items.append(current)
            if current is None:
                continue
            line = " ".join(t for t in (str(x).strip() for x in v[row - 1][col("F"):col("T") + 1]) if t)
            if line:
                current["text"] += ("\n" if current["text"] else "") + line

    roster, company = [], ""
    for row in range(ROSTER[0], ROSTER[1] + 1):
        s = cell(v, f"G{row}")
        if not s:
            continue
        if re.search(r"[\s　]", s):
            roster.append({"company": company, "name": s})
        else:
            company = s

    info = {
        "date": f"{cell(v, 'F6')}年{cell(v, 'J6')}月{cell(v, 'L6')}日{cell(v, 'N6')}",
        "time": f"{cell(v, 'F7')}:{cell(v, 'H7').zfill(2)}～{cell(v, 'K7')}:{cell(v, 'M7').zfill(2)}",
        "place": cell(v, "F8"),
    }
    agenda = {"project": cell(v, "C4"), "title": cell(v, "N1"), "meeting": info, "items": items, "roster": roster}
    return {
        "agenda_json": json.dumps(agenda, ensure_ascii=False),
        "meeting_info": f"{info['date']} {info['time']}／場所：{info['place']}",
    }
