# Pythonスニペット by Workato：定例ファイルの特定と、つなげる文字起こしの決定
#
# 定例中に録音・文字起こしが止められると、文字起こしが複数に分かれる。
# 同じ開催日の文字起こしは、00_受付 にあるものも、すでに文字起こしフォルダに移したものも、
# すべて作成日時の順につなげて1つの議事録にする。
# レシピは「同時実行数 1」で動かす。先の実行が受付のファイルをまとめて移した場合、
# 後の実行は already_processed=true で何もせずに終わる。
#
# 入力（すべて文字列）
#   transcript_id      トリガーになったファイルの ID
#   transcript_name    そのファイル名
#   uploaded_at        そのファイルの作成日時（ISO 8601）
#   inbox_items        00_受付 のファイル一覧（[{"id","name","created_at"}] の JSON）
#   transcript_items   文字起こしフォルダのファイル一覧（同上）
#   folder_items       901_総合定例会議資料 直下のファイル一覧（[{"id","name"}] の JSON）
# 出力
#   already_processed, found, meeting_date（YYMMDD）, meeting_date_iso, number（2桁）,
#   agenda_id, issues_id, minutes_exists（この日の議事録がすでにある＝作り直し）,
#   combine（つなげる文字起こし。[{"id","in_inbox","new_name"}] を作成日時の順に。JSON）, log

import json
import re
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def jst_date(name, created_at):
    # ファイル名の先頭に日付（6 桁の YYMMDD。8 桁の YYYYMMDD も可）があればそれを、
    # なければ置いた日（日本時間）を開催日とする
    m = re.match(r"(?:20)?(\d{2}[01]\d[0-3]\d)(?!\d)", name)
    if m:
        return m.group(1)
    return datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(JST).strftime("%y%m%d")


def main(input):
    inbox = [i for i in json.loads(input["inbox_items"] or "[]") if i["name"].lower().endswith(".vtt")]
    moved = json.loads(input["transcript_items"] or "[]")
    items = json.loads(input["folder_items"] or "[]")

    result = {"already_processed": False, "found": False, "meeting_date": "", "meeting_date_iso": "", "number": "",
              "agenda_id": "", "issues_id": "", "minutes_exists": False, "combine": "[]", "log": ""}
    if input["transcript_id"] not in [i["id"] for i in inbox]:
        result["already_processed"] = True
        return result

    date = jst_date(input["transcript_name"], input["uploaded_at"])
    result.update(meeting_date=date, meeting_date_iso=f"20{date[:2]}-{date[2:4]}-{date[4:]}")

    agenda = issues = None
    number = ""
    for item in items:
        a = re.fullmatch(rf"{date}_第(\d+)回_議題\.xlsx", item["name"])
        if a:
            agenda, number = item, a.group(1).zfill(2)
        if re.fullmatch(rf"{date}_第\d+回_課題リスト\.xlsx", item["name"]):
            issues = item
        if re.fullmatch(rf"{date}_第\d+回_議事録\.xlsx", item["name"]):
            result["minutes_exists"] = True

    log = []
    if not agenda:
        log.append(f"議題が見つかりません（901 に {date}_第NN回_議題.xlsx がありません）")
        result["log"] = "\n".join(log)
        return result
    if not issues:
        log.append(f"課題リストが見つかりません（901 に {date}_第NN回_課題リスト.xlsx がありません）。課題リストなしで続けます")

    # この日の文字起こし：移動済みのもの ＋ 受付にあるもの を作成日時の順に
    done = [dict(i, in_inbox=False) for i in moved if i["name"].startswith(f"{date}_")]
    new = [dict(i, in_inbox=True) for i in inbox if jst_date(i["name"], i["created_at"]) == date]
    all_items = sorted(done + new, key=lambda i: i["created_at"])
    count = len(done)
    combine = []
    for i in all_items:
        name = ""
        if i["in_inbox"]:
            count += 1
            name = f"{date}_第{number}回_文字起こし.vtt" if count == 1 else f"{date}_第{number}回_文字起こし_{count}.vtt"
        combine.append({"id": i["id"], "in_inbox": i["in_inbox"], "new_name": name})
    if len(combine) > 1:
        log.append(f"文字起こしが {len(combine)} 個に分かれていたため、時刻の順につなげました")
    if result["minutes_exists"]:
        log.append("この日の議事録がすでにあるため、追加された文字起こしを含めて作り直しました（前の版は Box のバージョン履歴に残ります）")

    result.update(found=True, number=number, agenda_id=agenda["id"], issues_id=issues["id"] if issues else "",
                  combine=json.dumps(combine, ensure_ascii=False), log="\n".join(log))
    return result
