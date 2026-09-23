# Pythonスニペット by Workato：定例ファイルの特定
#
# 入力（すべて文字列）
#   transcript_name  00_受付 に置かれた文字起こしのファイル名
#   uploaded_at      そのファイルの作成日時（ISO 8601。Box トリガーの created_at）
#   folder_items     901_総合定例会議資料 直下のファイル一覧（[{"id": "...", "name": "..."}] の JSON）
# 出力
#   found, meeting_date（YYYYMMDD）, meeting_date_iso（YYYY-MM-DD）, number（2桁）,
#   agenda_id, issues_id, transcript_new_name, log

import json
import re
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def main(input):
    name = input["transcript_name"]
    items = json.loads(input["folder_items"] or "[]")

    # ファイル名に 8 桁の日付があればそれを、なければ置いた日（日本時間）を開催日とする
    m = re.search(r"(20\d{6})", name)
    if m:
        date = m.group(1)
    else:
        uploaded = datetime.fromisoformat(input["uploaded_at"].replace("Z", "+00:00"))
        date = uploaded.astimezone(JST).strftime("%Y%m%d")

    agenda = issues = None
    number = ""
    for item in items:
        a = re.fullmatch(rf"{date}_第(\d+)回_議題\.xlsx", item["name"])
        if a:
            agenda, number = item, a.group(1).zfill(2)
        if re.fullmatch(rf"{date}_第\d+回_課題リスト\.xlsx", item["name"]):
            issues = item

    log = []
    if not agenda:
        log.append(f"議題が見つかりません（901 に {date}_第NN回_議題.xlsx がありません）")
    if not issues:
        log.append(f"課題リストが見つかりません（901 に {date}_第NN回_課題リスト.xlsx がありません）。課題リストなしで続けます")

    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "vtt"
    return {
        "found": agenda is not None,
        "meeting_date": date,
        "meeting_date_iso": f"{date[:4]}-{date[4:6]}-{date[6:]}",
        "number": number,
        "agenda_id": agenda["id"] if agenda else "",
        "issues_id": issues["id"] if issues else "",
        "transcript_new_name": f"{date}_第{number or '00'}回_文字起こし.{ext}",
        "log": "\n".join(log),
    }
