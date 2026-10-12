"""K1211（SK棚板）B案: 棚板下面にブラケットをビス留めし、手前へ持ち出してバーを吊る。
バー: 奥壁仕上面から 350、FL+1650、φ25。ブラケット: SUS FB-6×32（想定）2か所、左右壁から100。
使い方: python shelf_bar.py <FAMF-K1211-INO.dxf> <出力フォルダ>
"""
import sys, math
from pathlib import Path
import ezdxf
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# ---- 既存（K1211 から読み取り。図面座標 = 実寸mm）
FL_Y = 1114.0
SHELF_BOT, SHELF_D = 1775.0, 250.0      # 棚板下面 FL / 奥行（ポリ合板 t25、上端 FL1800）
SK_IN = (275.0, 585.0)                  # SK 水受け内側（奥壁から）
SK_FRONT = 665.0                        # SK 前縁（奥壁から）
HOOK3 = 511.0                           # モップ掛 3番フック（奥壁から）。吊り物は 381〜 に来る
BACK_Y = 6304.8                         # 平面図: 奥壁仕上面
ROOMS = {
    "東WWC": dict(front=(862.4, 1678.4), side_back=2159.2, plan=(862.4, 1678.4)),
    "東MWC": dict(front=(4087.0, 5296.6), side_back=5908.2, plan=(4087.0, 5296.6)),
}
# ---- B案
BAR_D, BAR_FL, BAR_FROM_BACK = 25.0, 1650.0, 350.0
BAR_END = 60.0                          # 壁〜バー端
BR_W, BR_T, BR_FROM_WALL = 32.0, 6.0, 100.0
SCREWS = (60.0, 150.0, 230.0)           # ブラケットのビス位置（奥壁から）
BR_BACK = 40.0                          # ブラケット後端（奥壁から）
CLOTH = 450.0
LAY = "追記_B案_棚下持出しバー"

def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]

doc, _ = recover.readfile(SRC)
msp = doc.modelspace()
doc.layers.add(LAY, color=4)
if "追記文字" not in doc.styles:
    doc.styles.add("追記文字", font="msgothic.ttc")
A = dict(layer=LAY, color=256)
AD = dict(A, linetype="DASHED") if "DASHED" in doc.linetypes else A
pl = lambda pts, att=A: msp.add_lwpolyline(pts, dxfattribs=att)
dim = lambda **k: msp.add_linear_dim(dimstyle="GMM011", override={"dimdec": 0}, dxfattribs=A, **k).render()
txt = lambda s, x, y, h=50: msp.add_mtext(s, dxfattribs=dict(A, style="追記文字", char_height=h, insert=(x, y), attachment_point=7))
sb_y, by = FL_Y + SHELF_BOT, FL_Y + BAR_FL
r = BAR_D / 2

for room, R in ROOMS.items():
    xl, xr = R["front"]
    # ---- 正面展開図
    pl(rect(xl + BAR_END, by - r, xr - BAR_END, by + r))
    for xb in (xl + BR_FROM_WALL, xr - BR_FROM_WALL):
        pl(rect(xb - BR_T / 2, by - 20, xb + BR_T / 2, sb_y - BR_T))      # 垂れ下がり部
        pl(rect(xb - BR_W / 2, sb_y - BR_T, xb + BR_W / 2, sb_y))          # 棚下の水平部（見付）
    pl(rect(xl + BAR_END, by - CLOTH, xr - BAR_END, by - r), AD)
    txt("掛け物の範囲（想定）", xl + 80, by - 80, 40)
    dim(base=(xl - 150, 0), p1=(xl, FL_Y), p2=(xl, by), angle=90)
    # ---- 側面展開図（奥壁が左、扉側が右）
    s0 = R["side_back"]
    xf = s0 + BAR_FROM_BACK
    pl([(s0 + BR_BACK, sb_y), (xf + BR_W / 2, sb_y), (xf + BR_W / 2, by - 20), (xf - BR_W / 2, by - 20),
        (xf - BR_W / 2, sb_y - BR_T), (s0 + BR_BACK, sb_y - BR_T), (s0 + BR_BACK, sb_y)])
    msp.add_circle((xf, by), r, dxfattribs=A)
    for sx in SCREWS:
        msp.add_line((s0 + sx, sb_y - BR_T - 8), (s0 + sx, sb_y + 20), dxfattribs=A)
    pl(rect(xf - 30, by - CLOTH, xf + 30, by - r), AD)
    dim(base=(0, sb_y + 120), p1=(s0, sb_y), p2=(xf, sb_y))
    dim(base=(0, sb_y + 60), p1=(s0 + SHELF_D, sb_y), p2=(xf, sb_y))
    dim(base=(xf + 150, 0), p1=(xf, by), p2=(xf, sb_y), angle=90)
    txt("B案 棚下持出しバー\\P"
        f"φ25 SUS（想定） 奥壁から{BAR_FROM_BACK:.0f}　FL+{BAR_FL:.0f}\\P"
        f"ブラケット SUS FB-6×32（想定）2か所\\P 棚板下面にビス3本留め（壁から{BR_FROM_WALL:.0f}）\\P"
        f"雑巾の水は SK 水受け（奥壁から{SK_IN[0]:.0f}〜{SK_IN[1]:.0f}）へ落ちる",
        s0 + 40, by - 520, 42)
    # ---- 平面図（棚下なのでブラケットは破線）
    pxl, pxr = R["plan"]
    py = BACK_Y - BAR_FROM_BACK
    pl(rect(pxl + BAR_END, py - r, pxr - BAR_END, py + r))
    for xb in (pxl + BR_FROM_WALL, pxr - BR_FROM_WALL):
        pl(rect(xb - BR_W / 2, py - BR_W / 2, xb + BR_W / 2, BACK_Y - BR_BACK), AD)
    dim(base=(pxl + 40, 0), p1=(pxl + 30, BACK_Y), p2=(pxl + 30, py), angle=90)

stem = "FAMF-K1211-INO_B案_棚下持出しバー"
doc.saveas(OUT / f"{stem}.dxf")

# ===================== 検討 =====================
G, E, FY = 9.81, 193000.0, 205.0
D, T = 25.0, 1.2
I = math.pi / 64 * (D**4 - (D - 2 * T)**4); Z = I / (D / 2)
Zfb = BR_W * BR_T**2 / 6                        # FB 平使い
PER, PITCH, FACTOR, P_MIS = 0.35, 70.0, 1.5, 20.0
lever = BAR_FROM_BACK - SHELF_D                 # 棚前端からの持出し
rs = [SHELF_D - s for s in SCREWS]              # 棚前端を支点としたビスの腕
res = {}
for room, R in ROOMS.items():
    W = R["front"][1] - R["front"][0]
    L = W - 2 * BR_FROM_WALL                    # ブラケット間
    n = int((W - 2 * BAR_END - 2 * 30) // PITCH) + 1
    wkg = n * PER * FACTOR
    Pn, Pm = wkg / 2 * G, P_MIS / 2 * G        # ブラケット1か所あたり
    res[room] = dict(W=W, L=L, n=n, wkg=wkg,
                     bar_s=P_MIS * G * L / 4 / Z, bar_d=P_MIS * G * L**3 / (48 * E * I),
                     br_s=Pm * lever / Zfb, screw=Pm * lever * max(rs) / sum(x * x for x in rs) / G,
                     per_n=wkg / 2)

plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
rd, _ = recover.readfile(OUT / f"{stem}.dxf")
for s in rd.styles:
    s.dxf.font = "wqy-zenhei.ttc"; s.dxf.discard("bigfont")
with PdfPages(OUT / f"{stem}.pdf") as pdf:
    # 1) 断面の考え方（側面）
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.text(0.04, 0.95, "B案 棚下持出しバー ― 断面の考え方（側面）", fontsize=22, weight="bold")
    fig.text(0.04, 0.925, "単位：mm　寸法は奥壁仕上面から。既存（棚・SK・モップ掛）は K1211 から読み取り", fontsize=11, color="#444")
    ax = fig.add_axes([0.04, 0.05, 0.55, 0.85]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-120, 980); ax.set_ylim(550, 2000)
    ax.add_patch(Rectangle((-60, 550), 60, 1450, hatch="///", fill=False, color="#888"))
    ax.add_patch(Rectangle((0, SHELF_BOT), SHELF_D, 25, color="#c9a46a")); ax.text(20, SHELF_BOT + 40, "棚板 t25（既存）", fontsize=10)
    ax.add_patch(Rectangle((0, 550), SK_FRONT, 130, fill=False, ls="--", color="#c0c")); ax.text(300, 600, "SK（既存・概形）", fontsize=10, color="#c0c")
    ax.add_patch(Rectangle((SK_IN[0], 600), SK_IN[1] - SK_IN[0], 80, color="#cfe8ff")); ax.text(SK_IN[0] + 5, 690, "水受け", fontsize=9)
    ax.plot([SK_FRONT, SK_FRONT], [550, 2000], ":", color="#c0c"); ax.text(SK_FRONT + 5, 1960, f"SK前縁 {SK_FRONT:.0f}", fontsize=10, color="#c0c")
    ax.add_patch(Rectangle((411, 1725), 500, 100, fill=False, color="#888")); ax.text(415, 1840, "モップ掛（右壁・既存）", fontsize=9, color="#666")
    ax.add_patch(Rectangle((HOOK3 - 130, 1100), 260, 650, fill=False, ls="--", color="#888")); ax.text(HOOK3 - 120, 1080, "3番フックの吊り物範囲", fontsize=9, color="#666")
    xf = BAR_FROM_BACK
    ax.add_patch(plt.Polygon([(BR_BACK, SHELF_BOT), (xf + 16, SHELF_BOT), (xf + 16, BAR_FL - 20), (xf - 16, BAR_FL - 20),
                              (xf - 16, SHELF_BOT - BR_T), (BR_BACK, SHELF_BOT - BR_T)], color="#2a9"))
    for s in SCREWS: ax.plot([s, s], [SHELF_BOT - 14, SHELF_BOT + 20], color="k", lw=1.5)
    ax.add_patch(Circle((xf, BAR_FL), 12.5, color="#2a9", ec="k"))
    ax.add_patch(Rectangle((xf - 30, BAR_FL - CLOTH), 60, CLOTH - 13, color="#7ab6e8", alpha=0.6))
    for k in range(3):
        ax.add_patch(FancyArrowPatch((xf - 15 + 15 * k, BAR_FL - CLOTH - 10), (xf - 15 + 15 * k, 700), arrowstyle="-|>", mutation_scale=10, color="#36c", ls=":"))
    ax.text(xf + 40, 1000, "しずく → 水受けへ", fontsize=11, color="#36c")
    ax.text(xf + 40, BAR_FL - 10, f"バー φ25  FL+{BAR_FL:.0f}", fontsize=11)
    ax.annotate("", (xf, 1930), (0, 1930), arrowprops=dict(arrowstyle="<->")); ax.text(xf / 2 - 30, 1940, f"{BAR_FROM_BACK:.0f}", fontsize=11)
    ax.annotate("", (xf, 1880), (SHELF_D, 1880), arrowprops=dict(arrowstyle="<->")); ax.text(SHELF_D + 20, 1890, f"持出し {lever:.0f}", fontsize=11)
    ax.annotate("", (SK_FRONT, 1300), (xf, 1300), arrowprops=dict(arrowstyle="<->")); ax.text(xf + 100, 1310, f"SK前縁から {SK_FRONT - xf:.0f}", fontsize=11)
    ax.annotate("", (xf + 90, BAR_FL), (xf + 90, SHELF_BOT), arrowprops=dict(arrowstyle="<->")); ax.text(xf + 100, BAR_FL + 40, f"{SHELF_BOT - BAR_FL:.0f}", fontsize=11)
    # 右側: 比較表と検討
    ax2 = fig.add_axes([0.62, 0.45, 0.35, 0.42]); ax2.axis("off")
    ax2.set_title("A案（壁ブラケット）との比較", fontsize=13, loc="left")
    rows = [["バー位置（奥壁から）", "325", f"{BAR_FROM_BACK:.0f}"], ["バー高さ FL", "1775", f"{BAR_FL:.0f}"],
            ["SK前縁からの距離", "340", f"{SK_FRONT - BAR_FROM_BACK:.0f}"], ["しずく", "水受けへ", "水受けへ"],
            ["固定先", "左右の壁（既存補強）", "棚板下面（ビス）"], ["ブース側パネル", "ビス留めが必要", "触らない"],
            ["支点間", "壁〜壁", f"WWC {res['東WWC']['L']:.0f}／MWC {res['東MWC']['L']:.0f}"]]
    t = ax2.table(cellText=rows, colLabels=["", "A案", "B案（本案）"], colWidths=[0.36, 0.28, 0.42], loc="upper left", cellLoc="left")
    t.auto_set_font_size(False); t.set_fontsize(10.5); t.scale(1, 1.7)
    for (i, j), c in t.get_celld().items():
        if i == 0: c.set_facecolor("#e8e8e8")
        if j == 2 and i > 0: c.set_facecolor("#eaf7f2")
    ax3 = fig.add_axes([0.62, 0.06, 0.35, 0.36]); ax3.axis("off")
    ax3.set_title("荷重検討（濡れ雑巾 0.35kg/本×1.5／誤使用 20kg 中央）", fontsize=13, loc="left")
    rows = []
    for k, rr in res.items():
        rows.append([k, f"{rr['n']}本 {rr['wkg']:.1f}kg", f"{rr['bar_s']:.0f} / {rr['bar_d']:.1f}",
                     f"{rr['br_s']:.0f}", f"{rr['screw']:.1f}"])
    t = ax3.table(cellText=rows, colLabels=["室", "常時荷重", "バー 応力/たわみ\n（誤使用）", "ブラケット応力\n（誤使用）", "ビス引抜\n最大 kg/本"],
                  colWidths=[0.14, 0.22, 0.26, 0.2, 0.18], loc="upper left", cellLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 2.2)
    for (i, j), c in t.get_celld().items():
        if i == 0: c.set_facecolor("#e8e8e8")
    ax3.text(0, 0.42, f"・応力は N/mm²（許容 {FY:.0f}）、たわみ mm。\n　バー SUS φ25 t1.2、ブラケット FB-6×32 平使い（想定）。\n"
             f"・ブラケット1か所 最大 {P_MIS/2:.0f}kg、持出し {lever:.0f}。\n　棚前端を支点にビスが引き抜かれる向きになる。\n"
             f"　最も奥のビスで約{max(r_['screw'] for r_ in res.values()):.1f}kg/本と小さい\n　（ポリ合板 t25 に木ねじ φ4 以上）。\n"
             f"・棚板は受桟（3方）に載り、荷重は下向きで浮き上がりなし。\n"
             f"・バーを奥壁から{HOOK3-130-30:.0f}より手前に出すと、\n　3番フックの吊り物（右壁際）と当たる。",
             fontsize=10, transform=ax3.transAxes, va="top")
    pdf.savefig(fig); plt.close(fig)
    # 2-4) 図面
    for title, lim in (("B案 棚下持出しバー ― 東WWC", (300, 950, 3700, 6900)),
                       ("B案 棚下持出しバー ― 東MWC", (3800, 950, 7500, 6900)),
                       ("FAMF-K1211-INO 全体（B案追記入り）", (790, -50, 11250, 7900))):
        fig = plt.figure(figsize=(16.54, 11.69))
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.9])
        Frontend(RenderContext(rd), MatplotlibBackend(ax),
                 config=Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)).draw_layout(rd.modelspace(), finalize=False)
        ax.set_xlim(lim[0], lim[2]); ax.set_ylim(lim[1], lim[3]); ax.set_aspect("equal"); ax.axis("off")
        fig.text(0.03, 0.95, title, fontsize=18)
        fig.text(0.03, 0.925, f"水色線＝追記。バー：奥壁から{BAR_FROM_BACK:.0f}・FL+{BAR_FL:.0f}・φ25、棚板下面のブラケット2か所から持出し", fontsize=10, color="#555")
        pdf.savefig(fig); plt.close(fig)
for k, v in res.items(): print(k, {a: round(b, 1) for a, b in v.items()})
