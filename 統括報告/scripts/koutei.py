"""工程表.xlsx から指定期間の主な工程・行事を抜き出す。
使い方: python3 -I koutei.py 工程表.xlsx 2026-10-26 2026-11-08
- バー：4行目以降・131行目までで、塗りが休み(index 11)／稼働日(index 9)以外の色の連続セル。
  名称は同じ列付近でバーの上の行（またはその行）にある文字。区分は B 列の見出し（【西エリア】など）。
- 行事・注記：図形（drawing1.xml）のテキスト。期間に重なるもの。
"""
import sys, re, zipfile, datetime
import openpyxl
path, s, e = sys.argv[1], *[datetime.date.fromisoformat(x) for x in sys.argv[2:4]]
D0 = datetime.date(2026, 10, 17)  # G列
dt = lambda c: D0 + datetime.timedelta(c - 7)  # 1-indexed列
ws = openpyxl.load_workbook(path).worksheets[0]

def color(cell):
    f = cell.fill
    if not f.fill_type: return None
    k = f.fgColor
    v = k.indexed if k.type == 'indexed' else (k.rgb if k.type == 'rgb' else f't{k.theme}')
    return None if v in (9, 11, 64) else v

area = ''; bars = []
for r in range(7, 132):
    b = ws.cell(r, 2).value
    if isinstance(b, str) and b.strip().startswith('【'): area = b.strip()
    c = 7
    while c <= 172:
        col = color(ws.cell(r, c))
        if col is None: c += 1; continue
        c0 = c
        while c <= 172 and color(ws.cell(r, c)) == col: c += 1
        st, en = dt(c0), dt(c - 1)
        if en < s or st > e: continue
        cands = []
        for rr in (r - 1, r, r - 2):
            for cc in range(max(7, c0 - 10), c):
                v = ws.cell(rr, cc).value
                if isinstance(v, str) and v.strip():
                    cands.append((abs(cc - c0) + (0 if cc <= c0 else 5) + (r - rr) * 2, v.strip()))
        name = min(cands)[1] if cands else None
        bars.append((st, en, area, name or '（名称なし）'))

z = zipfile.ZipFile(path)
x = z.read('xl/drawings/drawing1.xml').decode('utf-8')
notes = []
for m in re.finditer(r'<xdr:twoCellAnchor[^>]*>(.*?)</xdr:twoCellAnchor>', x, re.S):
    a = m.group(1)
    f = re.search(r'<xdr:from><xdr:col>(\d+)</xdr:col><xdr:colOff>-?\d+</xdr:colOff><xdr:row>(\d+)</xdr:row>', a)
    t = re.search(r'<xdr:to><xdr:col>(\d+)</xdr:col><xdr:colOff>-?\d+</xdr:colOff><xdr:row>(\d+)</xdr:row>', a)
    txt = ''.join(re.findall(r'<a:t>(.*?)</a:t>', a)).strip()
    if not (f and t and txt) or int(f[2]) > 131: continue
    st, en = dt(int(f[1]) + 1), dt(int(t[1]) + 1)
    if en < s or st > e: continue
    notes.append((st, en, int(f[2]) + 1, re.sub(r'[\s　]+', ' ', txt)))

for b in sorted(set(bars)): print('工程', b[0], b[1], b[2], b[3], sep='\t')
for n in sorted(notes): print('注記', n[0], n[1], f'行{n[2]}', n[3], sep='\t')
