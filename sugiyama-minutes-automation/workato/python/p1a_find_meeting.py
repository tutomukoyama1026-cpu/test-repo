# Pythonスニペット by Workato：定例フォルダの特定
#
# 開催日は、文字起こしのファイル名の先頭の日付（6 桁の YYMMDD。8 桁も可）、
# なければ 00_受付 に置いた日（日本時間）とする。
# 901_総合定例会議資料 の直下から「{開催日}_第NN回_定例会議」フォルダを探す。
# レシピは「同時実行数 1」で動かす。先の実行が同じ日の文字起こしをまとめて移した場合、
# 後の実行は already_processed=true で何もせずに終わる。
#
# 入力（すべて文字列）
#   transcript_id    トリガーになったファイルの ID
#   transcript_name  そのファイル名
#   uploaded_at      そのファイルの作成日時（ISO 8601）
#   inbox_items      00_受付 のファイル一覧（[{"id","name","created_at"}] の JSON）
#   root_items       901_総合定例会議資料 直下の一覧（[{"id","name","type"}] の JSON。type は file / folder）
# 出力
#   already_processed, found, meeting_date（YYMMDD）, meeting_date_iso（YYYY-MM-DD）, number（2桁）,
#   meeting_folder_id, meeting_folder_name, inbox_ids（この日の文字起こしで受付にあるもの。JSON）, log

import json
import re
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def jst_date(name, created_at):
    m = re.match(r"(?:20)?(\d{2}[01]\d[0-3]\d)(?!\d)", name)
    if m:
        return m.group(1)
    return datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(JST).strftime("%y%m%d")


def main(input):
    inbox = [i for i in json.loads(input["inbox_items"] or "[]") if i["name"].lower().endswith(".vtt")]
    root = json.loads(input["root_items"] or "[]")
    result = {"already_processed": False, "found": False, "meeting_date": "", "meeting_date_iso": "", "number": "",
              "meeting_folder_id": "", "meeting_folder_name": "", "inbox_ids": "[]", "log": ""}
    if input["transcript_id"] not in [i["id"] for i in inbox]:
        result["already_processed"] = True
        return result

    date = jst_date(input["transcript_name"], input["uploaded_at"])
    result.update(meeting_date=date, meeting_date_iso=f"20{date[:2]}-{date[2:4]}-{date[4:]}")
    folder = None
    for item in root:
        m = re.match(rf"(?:20)?{date}_第(\d+)回", item["name"])
        if m and item.get("type", "folder") == "folder":
            folder, result["number"] = item, m.group(1).zfill(2)
    if not folder:
        result["log"] = f"定例のフォルダが見つかりません（901 に「{date}_第NN回_定例会議」フォルダがありません）"
        return result

    ids = [i["id"] for i in sorted(inbox, key=lambda i: i["created_at"]) if jst_date(i["name"], i["created_at"]) == date]
    result.update(found=True, meeting_folder_id=folder["id"], meeting_folder_name=folder["name"], inbox_ids=json.dumps(ids))
    return result
