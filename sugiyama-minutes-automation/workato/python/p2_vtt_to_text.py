# Pythonスニペット by Workato：文字起こし（Teams の .vtt）を「話者：発言」の形に整える
#
# 入力  vtts          文字起こしファイルの中身の一覧（p1 の combine の順。文字列の配列の JSON）
#                     1つだけのときは、その1つを配列に入れて渡す
# 出力  transcript    「話者：発言」を1行ずつ並べた文字列（同じ話者の続く発言はまとめる）
#       speakers      話者名の一覧（JSON）
#       chars         文字数（AI に渡す量の目安）

import json
import re


def parse(text):
    lines = []  # [話者, 発言]
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
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
    return lines


def main(input):
    parts = [parse(v) for v in json.loads(input["vtts"])]
    blocks = []
    for i, lines in enumerate(parts, 1):
        text = "\n".join(f"{s}：{t}" for s, t in lines)
        # 途中で止めて分かれたときは、つなぎ目がわかるようにする
        blocks.append(text if len(parts) == 1 else f"――（文字起こし {i}／{len(parts)}）――\n{text}")
    transcript = "\n".join(blocks)
    speakers = sorted({s for lines in parts for s, _ in lines})
    return {"transcript": transcript, "speakers": json.dumps(speakers, ensure_ascii=False), "chars": len(transcript)}
