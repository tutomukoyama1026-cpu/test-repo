"""工程表.xlsx から 工程表.pdf を作る（CLAUDE.md の手順どおり）。
使い方: python3 -I koutei_pdf.py 椙山改修/工程表.xlsx 椙山改修/工程表.pdf
作業用コピーで
 ① 独自パレット（indexed 色）を rgb に置き換える
 ② 132行目以降の行・図形と FQ 列より右の列設定を削除し、印刷範囲を A1:FQ131 にする
 ③ A3 横・1ページに収める
→ LibreOffice で PDF に変換 → 白紙ページを除き、表の範囲で切り抜く（1ページ目＝コメントあり、2ページ目＝コメントなし）。
"""
import sys, re, zipfile, subprocess, tempfile, pathlib, shutil
from pypdf import PdfReader, PdfWriter
from PIL import Image

src, dst = map(pathlib.Path, sys.argv[1:3])
LAST_ROW, LAST_COL = 131, 173  # 131行目まで、FQ列まで
tmp = pathlib.Path(tempfile.mkdtemp())
zin = zipfile.ZipFile(src)
files = {i.filename: zin.read(i) for i in zin.infolist()}

# ① パレット
st = files['xl/styles.xml'].decode()
pal = re.findall(r'<rgbColor rgb="(\w+)"/>', re.search(r'<indexedColors>(.*?)</indexedColors>', st, re.S).group(1))
st = re.sub(r'indexed="(\d+)"', lambda m: f'rgb="{pal[int(m[1])].upper()}"' if int(m[1]) < len(pal) else m[0], st)
st = re.sub(r'<colors>.*?</colors>', '', st, flags=re.S)
files['xl/styles.xml'] = st.encode()
for n in [n for n in files if n.startswith('xl/drawings/drawing') and n.endswith('.xml')]:
    # ② 132行目以降の図形（from の row が 0 始まりで 131 以上）
    x = files[n].decode()
    x = re.sub(r'<xdr:(twoCellAnchor|oneCellAnchor)\b[^>]*>(?:(?!</xdr:\1>).)*?<xdr:from><xdr:col>\d+</xdr:col><xdr:colOff>-?\d+</xdr:colOff><xdr:row>(\d+)</xdr:row>.*?</xdr:\1>',
               lambda m: '' if int(m[2]) >= LAST_ROW else m[0], x, flags=re.S)
    files[n] = x.encode()

# ② 行・列・結合セル、③ 用紙
def cell_row(ref): return int(re.sub(r'[^0-9]', '', ref.split(':')[-1]) or 0)
for n in [n for n in files if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]:
    x = files[n].decode()
    x = re.sub(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', lambda m: '' if int(m[1]) > LAST_ROW else m[0], x, flags=re.S)
    x = re.sub(r'<mergeCell ref="([A-Z]+\d+:[A-Z]+\d+)"/>', lambda m: '' if cell_row(m[1].split(':')[0]) > LAST_ROW else m[0], x)
    x = re.sub(r'<mergeCells count="\d+">', lambda m: f'<mergeCells count="{x.count("<mergeCell ref=")}">', x)
    def col(m):
        lo, hi = int(m[1]), int(m[2])
        if lo > LAST_COL: return ''
        return m[0].replace(f'max="{hi}"', f'max="{min(hi, LAST_COL)}"')
    x = re.sub(r'<col min="(\d+)" max="(\d+)"[^>]*/>', col, x)
    x = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:FQ{LAST_ROW}"/>', x)
    x = re.sub(r'<pageSetup ', '<pageSetup paperSize="8" ', re.sub(r' paperSize="\d+"', '', x))
    files[n] = x.encode()
wb = files['xl/workbook.xml'].decode()
names = re.findall(r'<sheet name="([^"]*)"', wb)
dn = ''.join(f'<definedName name="_xlnm.Print_Area" localSheetId="{i}">\'{s.replace(chr(39), chr(39)*2)}\'!$A$1:$FQ${LAST_ROW}</definedName>' for i, s in enumerate(names))
wb = re.sub(r'<definedName name="_xlnm.Print_Area"[^>]*>.*?</definedName>', '', wb)
wb = wb.replace('</definedNames>', dn + '</definedNames>') if '</definedNames>' in wb else wb.replace('</sheets>', f'</sheets><definedNames>{dn}</definedNames>')
files['xl/workbook.xml'] = wb.encode()
files.pop('xl/calcChain.xml', None)

work = tmp / 'koutei_work.xlsx'
with zipfile.ZipFile(work, 'w', zipfile.ZIP_DEFLATED) as z:
    for i in zin.infolist():
        if i.filename in files: z.writestr(i, files[i.filename])
subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(tmp), str(work)], check=True, capture_output=True)
pdf = tmp / 'koutei_work.pdf'

# 白紙ページを除き、表の範囲で切り抜く
r = PdfReader(pdf); w = PdfWriter()
for i, p in enumerate(r.pages):
    png = tmp / f'p{i}'
    subprocess.run(['pdftoppm', '-r', '72', '-f', str(i + 1), '-l', str(i + 1), '-png', '-singlefile', str(pdf), str(png)], check=True)
    im = Image.open(f'{png}.png').convert('L').point(lambda v: 255 if v > 245 else 0)
    inv = Image.eval(im, lambda v: 255 - v)
    bb = inv.getbbox()
    if not bb: continue
    # 表の下で白が 20px 以上続いたら、そこから下（ページ番号など）は切る
    W, H = im.size; gap = 0
    for y in range(bb[1], bb[3]):
        gap = gap + 1 if not inv.crop((0, y, W, y + 1)).getbbox() else 0
        if gap >= 20: bb = inv.crop((0, 0, W, y - gap + 1)).getbbox(); break
    W, H = im.size; pw, ph = float(p.mediabox.width), float(p.mediabox.height)
    sx, sy = pw / W, ph / H; m = 2
    l, t, rr, b = bb
    p.mediabox.lower_left = (max(0, l * sx - m), max(0, ph - b * sy - m))
    p.mediabox.upper_right = (min(pw, rr * sx + m), min(ph, ph - t * sy + m))
    p.cropbox = p.mediabox
    w.add_page(p)
with open(dst, 'wb') as f: w.write(f)
print(f'{dst}: {len(w.pages)} ページ（元 {len(r.pages)} ページ）')
shutil.rmtree(tmp)
