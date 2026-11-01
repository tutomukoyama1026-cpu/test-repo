#!/usr/bin/env python3
"""各担当ブランチの最新の成果物を 成果物/01_社長〜08_工程管理 に集める。
使い方: python3 統括報告/scripts/seikabutsu.py   （リポジトリ直下で実行。事前に git fetch）
"""
import fnmatch, os, shutil, subprocess, sys

ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
OUT = os.path.join(ROOT, '成果物')
# (フォルダ, ブランチ, パターンのリスト)
PLAN = [
    ('01_社長', 'claude/sugiyama-tokatsu', ['統括報告/組織図.html', '統括報告/工程表_修正提案_*.html', '統括報告/*_朝の報告.html@latest']),
    ('02_図面計画書リスト', 'claude/confident-bohr-tpkdbt', ['椙山改修/*_図面・計画書リスト.xlsx']),
    ('03_課題リスト', 'claude/adoring-brahmagupta-1rck9y', ['椙山改修/*課題リスト*.xlsx', '椙山改修/作業報告.md']),
    ('04_増減リスト', 'claude/zougaku-list', ['椙山改修/*_増減リスト.xlsx']),
    ('05_図面チェック', 'claude/zumen-check', ['椙山改修/チェック/*']),
    ('06_計画書チェック', 'claude/sugiyama-tokatsu', ['統括報告/配布/*']),
    ('06_計画書チェック', 'claude/keikaku-check', ['椙山改修/チェック/*']),
    ('07_定例議事録', 'claude/gijiroku', ['椙山改修/*_議事録.xlsx', '椙山改修/議事録_様式.xlsx']),
    ('08_工程管理', 'claude/koutei', ['椙山改修/工程表.xlsx', '椙山改修/工程表.pdf', '椙山改修/工程リンク.xlsx', '椙山改修/工程/*']),
]

def files(branch):
    out = subprocess.check_output(['git', '-c', 'core.quotepath=false', 'ls-tree', '-r', '--name-only', 'origin/' + branch], cwd=ROOT, text=True)
    return out.splitlines()

# はじめに読む.md は残し、担当フォルダだけ作り直す
os.makedirs(OUT, exist_ok=True)
for n in os.listdir(OUT):
    if n[:2].isdigit() and os.path.isdir(os.path.join(OUT, n)):
        shutil.rmtree(os.path.join(OUT, n))
cache = {}
for folder, branch, pats in PLAN:
    d = os.path.join(OUT, folder); os.makedirs(d, exist_ok=True)
    fl = cache.setdefault(branch, files(branch))
    for p in pats:
        latest = p.endswith('@latest'); p = p.replace('@latest', '')
        hit = sorted(f for f in fl if fnmatch.fnmatch(f, p) and '/OLD/' not in f)
        if latest: hit = hit[-1:]
        for f in hit:
            data = subprocess.check_output(['git', 'show', f'origin/{branch}:{f}'], cwd=ROOT)
            with open(os.path.join(d, os.path.basename(f)), 'wb') as w: w.write(data)
            print(folder, os.path.basename(f))
