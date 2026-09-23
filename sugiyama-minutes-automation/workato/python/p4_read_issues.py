# Pythonスニペット by Workato：課題リストの読み取り
#
# 入力  text     「課題リスト」シートの使用範囲の表示文字列（Graph の usedRange の text。2次元配列の JSON）
#       address  使用範囲のアドレス（例：課題リスト!A1:Q109）
# 出力  issues_json   課題No ごとの概要・経過・期限（続き行はまとめる。経過が長いものは末尾だけ）
#       last_row      使用範囲の最終行（黒字に戻す範囲に使う）

import json
import re

FIRST_ROW = 7
HISTORY_TAIL = 800


def main(input):
    t = json.loads(input["text"])
    m = re.search(r"!?\$?([A-Z]+)\$?(\d+)(?::\$?[A-Z]+\$?(\d+))?$", input["address"])
    top = int(m.group(2))
    last_row = int(m.group(3) or m.group(2))

    def row(r):
        i = r - top
        rr = t[i] if 0 <= i < len(t) else []
        return [str(x).strip() for x in rr] + [""] * (16 - len(rr))

    categories = row(4)[1:7]
    issues = []
    for r in range(FIRST_ROW, last_row + 1):
        c = row(r)
        if not c[0]:
            continue
        history = re.sub(r"^（続き）\s*", "", c[11]).strip()
        if issues and issues[-1]["no"] == c[0]:
            if history:
                issues[-1]["history"] += "\n" + history
            continue
        issues.append({
            "no": c[0],
            "categories": "・".join(n for n, x in zip(categories, c[1:7]) if n and x == "〇"),
            "issued": c[7], "from": c[8], "summary": c[9], "parties": c[10],
            "history": history, "due": c[13], "done": c[14],
        })
    for i in issues:
        h = re.sub(r"\n{2,}", "\n", i["history"]).strip()
        i["history"] = "…" + h[-HISTORY_TAIL:] if len(h) > HISTORY_TAIL else h
    return {"issues_json": json.dumps(issues, ensure_ascii=False), "last_row": last_row}
