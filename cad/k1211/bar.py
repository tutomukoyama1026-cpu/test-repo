"""K1211（SK棚板）に、両側壁ブラケット固定のバー案を追記する。
バー: 奥壁仕上面から 325、FL+1775（モップ掛と同高さ・既存下地補強内）、φ25（両端フランジ ビス留め・両側下地補強）
使い方: python bar.py <FAMF-K1211-INO.dxf> <出力フォルダ>
"""
import sys
from pathlib import Path
import ezdxf, ezdxf.bbox
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

FL_Y = 1114.0
BAR_D, BAR_FL, BAR_FROM_BACK = 25.0, 1775.0, 325.0   # 高さはモップ掛と同じ（既存下地補強内）
FLANGE_D, FLANGE_T = 60.0, 12.0
CLOTH = 450.0                   # 掛けた布・手袋の垂れ下がり（想定）
BACK_Y = 6304.8                 # 平面図: 奥壁仕上面
ROOMS = {
    # front: 正面展開図の左右壁面X / side_back: 側面展開図の奥壁X（扉側が+）/ plan: 平面図の左右壁面X
    "東WWC": dict(front=(862.4, 1678.4), side_back=2159.2, plan=(862.4, 1678.4), rail_from_back=410.8),
    "東MWC": dict(front=(4087.0, 5296.6), side_back=5908.2, plan=(4087.0, 5296.6), rail_from_back=390.8),
}
LAY = "追記_バー案"

def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]

doc, _ = recover.readfile(SRC)
msp = doc.modelspace()
doc.layers.add(LAY, color=3)
if "追記文字" not in doc.styles:
    doc.styles.add("追記文字", font="msgothic.ttc")
A = dict(layer=LAY, color=256)
AD = dict(A, linetype="DASHED") if "DASHED" in doc.linetypes else A
by = FL_Y + BAR_FL
r = BAR_D / 2
pl = lambda pts, att=A: msp.add_lwpolyline(pts, dxfattribs=att)
dim = lambda **k: msp.add_linear_dim(dimstyle="GMM011", override={"dimdec": 0}, dxfattribs=A, **k).render()
txt = lambda s, x, y, h=55: msp.add_mtext(s, dxfattribs=dict(A, style="追記文字", char_height=h, insert=(x, y), attachment_point=7))

for room, R in ROOMS.items():
    xl, xr = R["front"]
    # ---- 正面展開図: バー + 両端フランジ + 布の範囲
    pl(rect(xl + FLANGE_T, by - r, xr - FLANGE_T, by + r))
    for xw, s in ((xl, 1), (xr, -1)):
        pl(rect(xw, by - FLANGE_D / 2, xw + s * FLANGE_T, by + FLANGE_D / 2))
    pl(rect(xl + 60, by - CLOTH, xr - 60, by - r), AD)
    txt("掛け物の範囲（想定）", xl + 80, by - 90, 45)
    dim(base=(xl - 150, 0), p1=(xl, FL_Y), p2=(xl, by), angle=90)
    # ---- 側面展開図: バー断面（円）+ 布の厚み範囲
    sx = R["side_back"] + BAR_FROM_BACK
    msp.add_circle((sx, by), r, dxfattribs=A)
    pl(rect(sx - FLANGE_D / 2, by - FLANGE_D / 2, sx + FLANGE_D / 2, by + FLANGE_D / 2))
    pl(rect(sx - 40, by - CLOTH, sx + 40, by - r), AD)
    dim(base=(0, by + 230), p1=(R["side_back"], by), p2=(sx, by))
    gap = R["rail_from_back"] - BAR_FROM_BACK - FLANGE_D / 2
    txt(f"固定バー φ25（SUS想定）\\P両端フランジ ビス留め\\P既存の両側下地補強内\\P奥壁から325　FL+{BAR_FL:.0f}（モップ掛と同高さ）\\Pモップ掛 端部まで {gap:.0f}",
        R["side_back"] + 60, by - 560, 50)
    # ---- 平面図: バー + フランジ
    pxl, pxr = R["plan"]
    py = BACK_Y - BAR_FROM_BACK
    pl(rect(pxl + FLANGE_T, py - r, pxr - FLANGE_T, py + r))
    for xw, s in ((pxl, 1), (pxr, -1)):
        pl(rect(xw, py - FLANGE_D / 2, xw + s * FLANGE_T, py + FLANGE_D / 2))
    dim(base=(pxl + 120, 0), p1=(pxl + 60, BACK_Y), p2=(pxl + 60, py), angle=90)

stem = "FAMF-K1211-INO_固定バー案"
doc.saveas(OUT / f"{stem}.dxf")

# ---- PDF（表示用にSHXを日本語TTFへ差し替え）
rd, _ = recover.readfile(OUT / f"{stem}.dxf")
for s in rd.styles:
    s.dxf.font = "wqy-zenhei.ttc"; s.dxf.discard("bigfont")
plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
with PdfPages(OUT / f"{stem}.pdf") as pdf:
    for title, lim in (("固定バー案 ― 東WWC", (300, 950, 3700, 6900)),
                       ("固定バー案 ― 東MWC", (3800, 950, 7500, 6900)),
                       ("FAMF-K1211-INO 全体（追記入り）", (790, -50, 11250, 7900))):
        fig = plt.figure(figsize=(16.54, 11.69))
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.9])
        Frontend(RenderContext(rd), MatplotlibBackend(ax),
                 config=Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)).draw_layout(rd.modelspace(), finalize=False)
        ax.set_xlim(lim[0], lim[2]); ax.set_ylim(lim[1], lim[3]); ax.set_aspect("equal"); ax.axis("off")
        fig.text(0.03, 0.95, title, fontsize=18)
        fig.text(0.03, 0.925, f"緑線＝追記。バー：奥壁から325・FL+{BAR_FL:.0f}（モップ掛と同高さ）・φ25、両側の壁にフランジでビス留め（突っ張りではない）", fontsize=10, color="#555")
        pdf.savefig(fig); plt.close(fig)
print("ok")
