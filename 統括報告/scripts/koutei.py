"""工程表.xlsx から指定期間の主な工程・行事を抜き出す。
使い方: python3 -I koutei.py 工程表.xlsx 2026-10-26 2026-11-08
- バー：4行目以降・131行目までで、塗りが休み(index 11)／稼働日(index 9)以外の色の連続セル。
  土日・休み（4行目がオレンジの列）だけをはさんで同じ色・同じ名称が続くものは1本にまとめる。
- 名称：バーの1行上（無ければその行・2行上）の文字。バーの開始列+1列以内で、いちばん右にあるもの
  （休みをはさんだ続きのバーは開始列より左だけ）。
  1つのセルに全角スペース2つ以上で区切って作業名が2つ書いてある所（例 BQ72「下り壁下地鉄骨　　　　　ハンガードア下地」）は、
  文字数から後ろの名称の位置（列）を見積もって分ける。
- 区分は B 列の見出し（【西エリア】など）。
- 行事・注記：図形（drawing1.xml）のテキスト。期間に重なるもの。
"""
import sys, re, zipfile, datetime
import openpyxl
path, s, e = sys.argv[1], *[datetime.date.fromisoformat(x) for x in sys.argv[2:4]]
D0 = datetime.date(2026, 10, 17)  # G列
C0, C1 = 7, 172  # G〜FP
dt = lambda c: D0 + datetime.timedelta(c - 7)  # 1-indexed列
ws = openpyxl.load_workbook(path).worksheets[0]

def color(cell):
    f = cell.fill
    if not f.fill_type: return None
    k = f.fgColor
    v = k.indexed if k.type == 'indexed' else (k.rgb if k.type == 'rgb' else f't{k.theme}')
    return None if v in (9, 11, 64) else v

holiday = {c for c in range(C0, C1 + 1) if ws.cell(4, c).fill.fgColor.indexed == 11}

def labels(r):
    """r行の文字 → [(列, 名称)]。全角スペース2つ以上の区切りは列を見積もって分ける。"""
    out = []
    for c in range(C0, C1 + 1):
        v = ws.cell(r, c).value
        if not (isinstance(v, str) and v.strip()): continue
        w = ws.column_dimensions[ws.cell(r, c).column_letter].width or 13
        pt = ws.cell(r, c).font.sz or 11
        per = (w * 7 + 5) / (pt * 96 / 72)  # 1列に入る全角文字数
        pos = 0
        for part in re.split(r'([　]{2,})', v.strip()):
            if part and not part.startswith('　　'):
                out.append((c + round(pos / per), part.strip(), pos > 0))  # 3つ目＝分けた後ろの名称（位置は見積もり）
            pos += len(part)
    return out

area = ''; bars = []
for r in range(7, 132):
    b = ws.cell(r, 2).value
    if isinstance(b, str) and b.strip().startswith('【'): area = b.strip()
    segs = []; c = C0
    while c <= C1:
        col = color(ws.cell(r, c))
        if col is None: c += 1; continue
        c0 = c
        while c <= C1 and color(ws.cell(r, c)) == col: c += 1
        segs.append([c0, c - 1, col])
    if not segs: continue
    labs = labels(r - 1) or labels(r) or labels(r - 2)
    prev = None
    for sg in segs:
        # 休みだけをはさんで同じ色が続くバー（続き）は、開始列より左の名称だけを見る。
        # 新しいバーは開始列+1列まで、分けた後ろの名称は位置が見積もりなので+2列まで見る。
        cont = prev and prev[2] == sg[2] and all(cc in holiday for cc in range(prev[1] + 1, sg[0]))
        left = [l for l in labs if l[0] <= sg[0] + (2 if l[2] else 0 if cont else 1)]
        sg.append(max(left)[1] if left else (min(labs)[1] if labs else '（名称なし）'))
        prev = sg
    merged = [segs[0]]
    for sg in segs[1:]:
        p = merged[-1]
        if sg[2] == p[2] and sg[3] == p[3] and all(cc in holiday for cc in range(p[1] + 1, sg[0])):
            p[1] = sg[1]
        else:
            merged.append(sg)
    for c0, c1, _, name in merged:
        st, en = dt(c0), dt(c1)
        if en < s or st > e: continue
        bars.append((st, en, area, name, f'行{r}'))

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

for b in sorted(set(bars)): print('工程', *b, sep='\t')
for n in sorted(notes): print('注記', n[0], n[1], f'行{n[2]}', n[3], sep='\t')
