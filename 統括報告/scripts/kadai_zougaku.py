"""課題リストと増額リストを突き合わせて、増額リストに反映が要るものを出す。
使い方: python3 -I kadai_zougaku.py <課題リスト.xlsx> <増額リスト.xlsx>
課題リスト：シート「課題リスト」6行目以降（A No.、J 概要、M 概算金額、O 完了日、P 指示書番号）
増額リスト：シート1枚目 4行目が見出し、5行目以降（C 発生元「課題 No.N」、G 金額、I 状態）
金額はマイナス（減額）も扱う。
"""
import sys, re, openpyxl
kp, zp = sys.argv[1:3]
ks = openpyxl.load_workbook(kp, data_only=True)['課題リスト']
zs = openpyxl.load_workbook(zp, data_only=True).worksheets[0]

def num(v):
    if isinstance(v, (int, float)): return v
    if isinstance(v, str):
        t = v.replace(',', '').replace('円', '').replace('▲', '-').replace('△', '-').strip()
        try: return float(t)
        except ValueError: return None
    return None

kadai = {}
for r in range(6, ks.max_row + 1):
    no = ks[f'A{r}'].value
    if no is None: continue
    kadai[int(no)] = dict(j=str(ks[f'J{r}'].value or '')[:30], m=ks[f'M{r}'].value,
                          o=ks[f'O{r}'].value, p=ks[f'P{r}'].value)

zou = {}
for r in range(5, zs.max_row + 1):
    c = str(zs[f'C{r}'].value or '')
    m = re.search(r'課題\s*No\.?\s*(\d+)', c)
    if m: zou[int(m[1])] = dict(row=r, c=c, g=zs[f'G{r}'].value, i=zs[f'I{r}'].value, b=zs[f'B{r}'].value)

out = []
for no, k in sorted(kadai.items()):
    z = zou.get(no)
    if k['m'] not in (None, ''):
        if not z:
            out.append(('未登録', no, k['j'], f"課題の概算金額 {k['m']} が増額リストに無い → 追加"))
            continue
        km, zg = num(k['m']), num(z['g'])
        if km is not None and km != zg:
            out.append(('金額ちがい', no, k['j'], f"課題 {k['m']} ／ 増額 {z['g']} → 増額リストを直すか確認"))
        if km is None and zg is None:
            out.append(('金額未確定', no, k['j'], f"課題の金額が「{k['m']}」で未確定のまま"))
    elif z:
        out.append(('課題側の金額なし', no, k['j'], f"増額リストにはあるが課題の概算金額が空欄（増額 {z['g']}）→ 確認"))
    if z and k['o'] and z['i'] in ('見積中', '提出済み'):
        out.append(('状態の確認', no, k['j'], f"課題は完了（{k['o']:%m/%d}）だが増額は「{z['i']}」→ 承認／不採用を確認"))
    if z and k['p'] and str(k['p']) not in z['c']:
        out.append(('指示書番号', no, k['j'], f"課題の指示書番号 {k['p']} を発生元に併記"))
for no, z in zou.items():
    if no not in kadai:
        out.append(('課題No.なし', no, z['b'], '課題リストに該当の No. が無い（番号の振り直し？）'))

for o in out: print(*[str(x).replace('\n', ' ') for x in o], sep='\t')
if not out: print('ずれなし')
