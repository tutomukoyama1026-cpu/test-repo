# Pythonスニペット by Workato：文字起こし（Teams の .vtt）を「話者：発言」の形に整える
#
# 入力  vtt           文字起こしファイルの中身（文字列）
# 出力  transcript    「話者：発言」を1行ずつ並べた文字列（同じ話者の続く発言はまとめる）
#       speakers      話者名の一覧（JSON）
#       chars         文字数（AI に渡す量の目安）

import json
import re


def main(input):
    text = input["vtt"].replace("\r\n", "\n")
    lines = []  # [話者, 発言]
    for block in re.split(r"\n\s*\n", text):
        rows = [r for r in block.split("\n") if r.strip()]
        # 先頭の WEBVTT、番号行、タイムスタンプ行を除く
        rows = [r for r in rows if r.strip() != "WEBVTT" and "-->" not in r and not re.fullmatch(r"[0-9a-f\-/]+", r.strip())]
        if not rows:
            continue
        body = " ".join(rows)
        m = re.search(r"<v ([^>]+)>(.*?)(</v>|$)", body)
        speaker, said = (m.group(1).strip(), m.group(2).strip()) if m else ("（不明）", re.sub(r"<[^>]+>", "", body).strip())
        if not said:
            continue
        if lines and lines[-1][0] == speaker:
            lines[-1][1] += " " + said
        else:
            lines.append([speaker, said])

    transcript = "\n".join(f"{s}：{t}" for s, t in lines)
    speakers = sorted({s for s, _ in lines})
    return {"transcript": transcript, "speakers": json.dumps(speakers, ensure_ascii=False), "chars": len(transcript)}
