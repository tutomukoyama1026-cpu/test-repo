# Pythonスニペット by Workato：ToDo リスト（Teams の「リスト」）に登録する宿題の作成
#
# LLM の回答の宿題（議題ごとの actions、議題外の actions）を、1件1行の ToDo にする。
# 同じ会議の議事録を作り直したときに二重に登録しないよう、1件ごとに「キー」を付ける。
# レシピは、リストに同じキーの行がなければ追加する（あれば何もしない。状態は人が更新するため）。
#
# 入力  llm_text       LLM API の回答（p5 と同じもの）
#       meeting_type   会議の種類（総合定例会議／定例会議／分科会）
#       meeting_date   開催日（YYMMDD）
#       number         回数（2桁）
#       minutes_url    Box の議事録（.xlsx）のリンク
# 出力  todos（[{"title","owner","due","meeting","agenda_no","minutes_url","key"}] の JSON）, count

import json
import re


def parse_llm(text):
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(s[s.find("{"):s.rfind("}") + 1])


def compact(s):
    return re.sub(r"[\s\u3000]", "", s)


def main(input):
    data = parse_llm(input["llm_text"])
    mtype, date, number = input["meeting_type"], input["meeting_date"], input["number"]
    meeting = f"{mtype} 第{number}回（{date}）"
    todos = []
    for kind, items in (("", data.get("items") or []), ("議題外", data.get("new_items") or [])):
        for item in items:
            no = f"議題外：{item.get('title', '')}" if kind else f"No.{item.get('no', '')}"
            for i, a in enumerate(item.get("actions") or [], 1):
                task = (a.get("task") or "").strip()
                if not task:
                    continue
                due = a.get("due") or ""
                todos.append({
                    "title": task,
                    "owner": a.get("owner") or "",
                    "due": due if re.fullmatch(r"\d{4}-\d{2}-\d{2}", due) else "",
                    "meeting": meeting,
                    "agenda_no": no,
                    "minutes_url": input.get("minutes_url", ""),
                    # 会議・議題・宿題の中身で決まるキー（作り直しても同じになる）
                    "key": f"{date}_{mtype}_{no}_{compact(task)[:40]}",
                })
    return {"todos": json.dumps(todos, ensure_ascii=False), "count": len(todos)}
