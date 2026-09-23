# Pythonスニペット by Workato：次回用の課題リストを作るかどうかの判断
#
# 課題リストは3種類の会議で共通の1つ。同じ日に会議が複数あっても、
# 次回用の課題リスト（OLD への移動と、全部黒字にした次回定例日の課題リストの作成）は
# その日の最初の会議のあとに1回だけ行う。
#   - 902 直下にこの日の課題リスト（{開催日}_課題リスト.xlsx）があれば OLD へ移す
#   - それ以外の課題リストがすでに直下にあれば（同じ日の先の会議で作成済み）、作らない
#     （金子主任が直し始めていても上書きしない）
#
# 入力  meeting_date        開催日（YYMMDD）
#       issues_root_items   902_課題リスト直下のファイル一覧（[{"id","name"}] の JSON）
# 出力  move_id（OLD へ移すファイルの ID。なければ ""）, create_next（true / false）, log

import json


def main(input):
    date = input["meeting_date"]
    root = [i for i in json.loads(input["issues_root_items"] or "[]") if i["name"].lower().endswith(".xlsx")]
    current = next((i for i in root if i["name"] == f"{date}_課題リスト.xlsx"), None)
    others = [i for i in root if i is not current]
    if others:
        return {"move_id": current["id"] if current else "", "create_next": False,
                "log": f"次回用の課題リスト（{others[0]['name']}）は作成済みのため、作りませんでした"}
    return {"move_id": current["id"] if current else "", "create_next": True, "log": ""}
