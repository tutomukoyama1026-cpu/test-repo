# Pythonスニペット by Workato：定例フォルダの中のファイルの特定と、つなげる文字起こしの決定
#
# 定例フォルダの中から、議題（名前に「議題」を含む .xlsx）と課題リスト（「課題」を含む .xlsx）を探す。
# 定例中に録音・文字起こしが止められると文字起こしが複数に分かれるので、
# フォルダにすでに移した文字起こしと、00_受付 にあるこの日の文字起こしを、作成日時の順につなげる。
#
# 入力（すべて文字列）
#   meeting_date    p1a の meeting_date（YYMMDD）
#   number          p1a の number（2桁）
#   folder_items    定例フォルダの中のファイル一覧（[{"id","name","created_at"}] の JSON）
#   inbox_items     00_受付 のファイル一覧（同上）
#   inbox_ids       p1a の inbox_ids
# 出力
#   found, agenda_id, issues_id, minutes_exists（この回の議事録がすでにある＝作り直し）,
#   combine（つなげる文字起こし。[{"id","in_inbox","new_name"}] を作成日時の順に。JSON）, log

import json


def main(input):
    date, number = input["meeting_date"], input["number"]
    items = json.loads(input["folder_items"] or "[]")
    inbox_ids = set(json.loads(input["inbox_ids"] or "[]"))
    inbox = [i for i in json.loads(input["inbox_items"] or "[]") if i["id"] in inbox_ids]

    def xlsx(word, exclude=""):
        found = [i for i in items if i["name"].lower().endswith(".xlsx") and word in i["name"] and not (exclude and exclude in i["name"])]
        return found[0] if found else None

    agenda = xlsx("議題", exclude="議事録")
    issues = xlsx("課題")
    minutes_exists = xlsx("議事録") is not None
    log = []
    if not agenda:
        return {"found": False, "agenda_id": "", "issues_id": "", "minutes_exists": minutes_exists, "combine": "[]",
                "log": "定例フォルダに議題（名前に「議題」を含む Excel）が見つかりません"}
    if not issues:
        log.append("定例フォルダに課題リスト（名前に「課題」を含む Excel）が見つかりません。課題リストなしで続けます")

    done = [dict(i, in_inbox=False) for i in items if i["name"].lower().endswith(".vtt")]
    new = [dict(i, in_inbox=True) for i in inbox]
    count = len(done)
    combine = []
    for i in sorted(done + new, key=lambda i: i["created_at"]):
        name = ""
        if i["in_inbox"]:
            count += 1
            name = f"{date}_第{number}回_文字起こし.vtt" if count == 1 else f"{date}_第{number}回_文字起こし_{count}.vtt"
        combine.append({"id": i["id"], "in_inbox": i["in_inbox"], "new_name": name})
    if len(combine) > 1:
        log.append(f"文字起こしが {len(combine)} 個に分かれていたため、時刻の順につなげました")
    if minutes_exists:
        log.append("この回の議事録がすでにあるため、追加された文字起こしを含めて作り直しました（前の版は Box のバージョン履歴に残ります）")
    return {"found": True, "agenda_id": agenda["id"], "issues_id": issues["id"] if issues else "",
            "minutes_exists": minutes_exists, "combine": json.dumps(combine, ensure_ascii=False), "log": "\n".join(log)}
