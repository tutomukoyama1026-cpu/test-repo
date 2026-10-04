#!/usr/bin/env python3
"""フォルダ直下のファイルを種類ごとのサブフォルダに振り分けるスクリプト。

使い方:
    python organize.py ~/Downloads            # 確認のみ(何も動かさない)
    python organize.py ~/Downloads --run      # 実際に移動する
    python organize.py ~/Downloads --undo     # 直前の移動を元に戻す
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

CATEGORIES = {
    "画像": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tif", ".tiff"},
    "動画": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".m4v"},
    "音楽": {".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"},
    "文書": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".pages"},
    "表計算": {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
    "プレゼン": {".ppt", ".pptx", ".odp", ".key"},
    "圧縮ファイル": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "インストーラー": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage"},
    "プログラム": {".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".c", ".cpp", ".sh", ".bat"},
}
OTHER = "その他"
LOG_NAME = ".organize_log.json"


def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for name, exts in CATEGORIES.items():
        if ext in exts:
            return name
    return OTHER


def unique_destination(dest: Path) -> Path:
    """同名ファイルがあれば「名前 (1).拡張子」のように番号を付ける。"""
    if not dest.exists():
        return dest
    n = 1
    while True:
        candidate = dest.with_name(f"{dest.stem} ({n}){dest.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def organize(target: Path, run: bool) -> None:
    script = Path(__file__).resolve()
    files = [
        p for p in sorted(target.iterdir())
        if p.is_file() and not p.name.startswith(".") and p.resolve() != script
    ]
    if not files:
        print("整理するファイルがありません。")
        return

    moves = []
    for src in files:
        folder = target / category_for(src)
        dest = unique_destination(folder / src.name)
        print(f"{src.name}  ->  {folder.name}/{dest.name}")
        if run:
            folder.mkdir(exist_ok=True)
            shutil.move(str(src), str(dest))
            moves.append({"from": str(src), "to": str(dest)})

    if run:
        (target / LOG_NAME).write_text(json.dumps(moves, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{len(moves)} 個のファイルを移動しました。元に戻すには --undo を付けて実行してください。")
    else:
        print(f"\n確認のみです({len(files)} 個)。実際に移動するには --run を付けて実行してください。")


def undo(target: Path) -> None:
    log = target / LOG_NAME
    if not log.exists():
        print("元に戻す記録がありません。")
        return
    moves = json.loads(log.read_text(encoding="utf-8"))
    for m in reversed(moves):
        src, dest = Path(m["to"]), Path(m["from"])
        if src.exists() and not dest.exists():
            shutil.move(str(src), str(dest))
            print(f"{src.name}  ->  元の場所")
        else:
            print(f"スキップ: {src}")
    for folder in {Path(m["to"]).parent for m in moves}:
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()
    log.unlink()
    print("元に戻しました。")


def main() -> None:
    parser = argparse.ArgumentParser(description="フォルダ内のファイルを種類ごとに整理します。")
    parser.add_argument("folder", help="整理したいフォルダ(例: ~/Downloads)")
    parser.add_argument("--run", action="store_true", help="実際にファイルを移動する")
    parser.add_argument("--undo", action="store_true", help="直前の整理を元に戻す")
    args = parser.parse_args()

    target = Path(args.folder).expanduser()
    if not target.is_dir():
        sys.exit(f"フォルダが見つかりません: {target}")

    if args.undo:
        undo(target)
    else:
        organize(target, args.run)


if __name__ == "__main__":
    main()
