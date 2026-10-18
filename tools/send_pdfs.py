#!/usr/bin/env python3
"""zip から PDF だけを取り出し、Gmail API で会社メールに送る。

使い方:
    python3 -I tools/send_pdfs.py <zipファイル> [--to 宛先] [--subject 件名] [--dry-run]

必要な環境変数（Claude の環境設定に登録する。リポジトリには書かない）:
    GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN
設定手順は tools/Gmail送信_設定手順.md。
"""
import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
import zipfile
from email.message import EmailMessage

DEFAULT_TO = "tutomu.koyama@shimz.co.jp"
# Gmail の上限は 25MB（エンコード後に約1.37倍になる）。余裕を見て1通あたり元サイズ 17MB まで
BATCH_LIMIT = 17 * 1024 * 1024


def ssl_context():
    for p in (os.environ.get("SSL_CERT_FILE"), "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


def extract_pdfs(zip_path):
    """zip 内の PDF を (ファイル名, bytes) のリストで返す。Windows の zip（cp932）にも対応。"""
    pdfs, seen = [], set()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if not info.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("cp932")
                except UnicodeError:
                    pass
            base = name.replace("\\", "/").split("/")[-1]
            if info.is_dir() or not base.lower().endswith(".pdf") or base.startswith("._"):
                continue
            stem, n, unique = base[:-4], 2, base
            while unique in seen:
                unique = f"{stem}({n}).pdf"
                n += 1
            seen.add(unique)
            pdfs.append((unique, z.read(info)))
    return pdfs


def batches(pdfs):
    out, cur, size = [], [], 0
    for name, data in pdfs:
        if cur and size + len(data) > BATCH_LIMIT:
            out.append(cur)
            cur, size = [], 0
        cur.append((name, data))
        size += len(data)
    if cur:
        out.append(cur)
    return out


def access_token(ctx):
    try:
        body = urllib.parse.urlencode({
            "client_id": os.environ["GMAIL_CLIENT_ID"],
            "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
            "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }).encode()
    except KeyError as e:
        sys.exit(f"環境変数 {e.args[0]} が設定されていません（tools/Gmail送信_設定手順.md を参照）")
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body)
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.load(r)["access_token"]


def send(ctx, token, msg):
    req = urllib.request.Request(
        "https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send?uploadType=media",
        data=msg.as_bytes(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "message/rfc822"},
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.load(r)["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--to", default=DEFAULT_TO)
    ap.add_argument("--subject")
    ap.add_argument("--dry-run", action="store_true", help="送信せずに内容だけ表示する")
    a = ap.parse_args()

    pdfs = extract_pdfs(a.zip)
    if not pdfs:
        sys.exit("zip の中に PDF がありません")
    subject = a.subject or (pdfs[0][0][:-4] + (f" 他{len(pdfs) - 1}件" if len(pdfs) > 1 else ""))
    groups = batches(pdfs)

    ctx = ssl_context()
    token = None if a.dry_run else access_token(ctx)
    for i, group in enumerate(groups, 1):
        msg = EmailMessage()
        msg["To"] = a.to
        msg["Subject"] = subject + (f" ({i}/{len(groups)})" if len(groups) > 1 else "")
        msg.set_content("添付ファイル\n" + "".join(f"・{n}\n" for n, _ in group))
        for name, data in group:
            msg.add_attachment(data, maintype="application", subtype="pdf", filename=name)
        size = sum(len(d) for _, d in group)
        print(f"[{i}/{len(groups)}] 件名: {msg['Subject']} / 宛先: {a.to} / {size / 1e6:.1f}MB")
        for name, data in group:
            print(f"    {name} ({len(data) / 1e6:.1f}MB)")
        if not a.dry_run:
            print(f"    送信済み (id: {send(ctx, token, msg)})")


if __name__ == "__main__":
    main()
