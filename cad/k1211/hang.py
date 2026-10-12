"""K1211（SK棚板）のモップ掛け 1番フック（扉側）に、ホウキ／モップを吊るした図を追記する。
入力: FAMF-K1211-INO.dxf（DWGを LibreDWG の dwg2dxf で変換したもの）
出力: out/ に DXF（全図面＋追記）と PDF（拡大図＋全体図）
使い方: python hang.py <FAMF-K1211-INO.dxf>
"""
import sys
from pathlib import Path
import numpy as np
import cadquery as cq
import ezdxf, ezdxf.bbox
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build  # ホウキ・モップの3Dモデル/寸法

SRC = Path(sys.argv[1])
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# ---- 図面上の基準（K1211 の 1/20 展開図・平面図から読み取り、図面座標 = 実寸mm）
FL_Y = 1114.0          # 展開図の床(FL)
HOOK_FL = 1756.0       # フック受け位置（フック下端の内側）  ※フック中心 FL1775 の約19mm下
WALL_GAP = 32.0        # 壁仕上面〜フック受け位置（モップ掛 t20 + フック出 約12）
ROOMS = {
    # side_x: 側面展開図の1番フックX / booth_x: 扉側ブース面 / front_x: 正面展開図の壁面X
    # plan_y: 平面図の1番フックY / plan_x: 平面図の壁面X
    "東WWC": dict(side_x=2970.1, booth_x=3220.0, front_x=1678.4, plan_y=5494.0, plan_x=1678.4),
    "東MWC": dict(side_x=6699.4, booth_x=6929.0, front_x=5296.6, plan_y=5514.0, plan_x=5296.6),
}
HOOK_Y = FL_Y + HOOK_FL

def edges_from_section(shape, plane_rot=None):
    """3D形状を z=0 で切断し、断面の輪郭を [(x,y),...] のリストで返す"""
    if plane_rot:
        shape = shape.rotate((0, 0, 0), *plane_rot)
    sec = cq.Workplane("XY").add(shape).section(0)
    out = []
    for e in sec.edges().vals():
        n = 2 if e.geomType() == "LINE" else 24
        out.append([(p.x, p.y) for p in (e.positionAt(t) for t in np.linspace(0, 1, n))])
    return out

# ===================== 吊り下げ形状（2D） =====================
# いずれも (u, h) で返す: u = 扉側を+とする水平方向, h = フック受け位置からの高さ(下が-)
def broom_shapes():
    """ホウキ: グリップ先端の吊り穴（中心(10,12) r6）の上端をフックに掛ける"""
    comp = build.broom().toCompound()
    hx, hy = 10.0, 6.0                                  # 吊り穴上端（モデル座標）
    face = [[(x - hx, -(y - hy)) for x, y in pl] for pl in edges_from_section(comp)]
    edge = [[(-z, -(y - hy)) for z, y in pl]              # x=0 断面（側面から見た厚み）
            for pl in edges_from_section(comp, ((0, 1, 0), 90))]
    return face, edge

def rect(u0, u1, h0, h1):
    return [(u0, h0), (u1, h0), (u1, h1), (u0, h1), (u0, h0)]

def mop_shapes():
    """モップ: 柄キャップの吊り穴上端をフックに掛ける（build.mop と同寸法）"""
    m = build.M
    zh = m["yarn_len"]; H = m["holder_h"]; zj = zh + H + m["hump_h"]
    zp = zj + m["joint_h"] + 6; p0 = zp - 30; p1 = p0 + m["pipe_len"]; zg = p1 - m["grip_len"]
    cap0, cap1 = zg + m["grip_len"], zg + m["grip_len"] + 40
    hole_c = zg + m["grip_len"] + 22; zb = hole_c + 6          # 吊り穴上端
    W, D = m["holder_w"] / 2, m["holder_d"] / 2
    f = lambda pl: [(u, z - zb) for u, z in pl]
    a, hh = m["hump_w"] / 2, m["hump_h"]
    R = (a * a + hh * hh) / (2 * hh)                     # 山形（円弧）の半径
    arc = [(x, zh + H + hh - R + np.sqrt(R * R - x * x)) for x in np.linspace(-a, a, 21)]
    yw = m["yarn_w"] / 2
    face = [rect(-yw, yw, 0, zh - 19)]                                   # 糸
    face += [[(x, 4), (x, zh - 19)] for x in np.linspace(-yw + 9.5, yw - 9.5, 19)]  # 糸の筋
    face += [rect(-yw - 2, yw + 2, zh - 19, zh)]                         # 縫製テープ
    face += [rect(-W, W, zh, zh + H), arc]                               # ホルダー＋山形
    face += [rect(-15, 15, zj, zj + 22), rect(-14, 14, zj + 22, zp - 6)] # ジョイント
    face += [rect(-m["pipe_d"]/2, m["pipe_d"]/2, zp - 6, zg)]            # パイプ
    face += [rect(-m["grip_d"]/2, m["grip_d"]/2, zg, cap0)]              # グリップ
    face += [rect(-15, 15, cap0, cap1)]                                  # キャップ
    face += [[(6*np.cos(t), hole_c + 6*np.sin(t)) for t in np.linspace(0, 2*np.pi, 25)]]
    face += [[(4*np.cos(t), zj + 16 + 4*np.sin(t)) for t in np.linspace(0, 2*np.pi, 17)]]
    t = m["yarn_t"] / 2
    edge = [rect(-t, t, 0, zh - 19), rect(-4, 4, zh - 19, zh), rect(-D, D, zh, zj),
            rect(-12, 12, zj, zj + 22), rect(-14, 14, zj + 22, zp - 6),
            rect(-m["pipe_d"]/2, m["pipe_d"]/2, zp - 6, zg),
            rect(-m["grip_d"]/2, m["grip_d"]/2, zg, cap0), rect(-6, 6, cap0, cap1)]
    return [f(p) for p in face], [f(p) for p in edge]

ITEMS = {
    "ホウキ": dict(fn=broom_shapes, color=1),
    "モップ": dict(fn=mop_shapes, color=5),
}

# ===================== 図面への追記 =====================
def add_pl(msp, pts, attribs):
    msp.add_lwpolyline([(float(x), float(y)) for x, y in pts], dxfattribs=attribs)

def annotate(doc, name, color):
    msp = doc.modelspace()
    lay = f"追記_{name}"
    doc.layers.add(lay, color=color)
    if "追記文字" not in doc.styles:
        doc.styles.add("追記文字", font="msgothic.ttc")
    A = dict(layer=lay, color=256)
    face, edge = ITEMS[name]["fn"]()
    allh = [h for pl in face for _, h in pl]
    allu = [u for pl in face for u, _ in pl]
    hmin, umin, umax = min(allh), min(allu), max(allu)
    dims = []
    for room, r in ROOMS.items():
        # 側面展開図（壁を正面に見る）: u=+ が扉側（右）
        for pl in face:
            add_pl(msp, [(r["side_x"] + u, HOOK_Y + h) for u, h in pl], A)
        # 正面展開図（壁を真横から見る）: 壁面から WALL_GAP の位置に中心
        cx = r["front_x"] - WALL_GAP
        for pl in edge:
            add_pl(msp, [(cx + u, HOOK_Y + h) for u, h in pl], A)
        # 平面図: 投影範囲を破線で
        px = r["plan_x"] - WALL_GAP
        tmax = max(abs(u) for pl in edge for u, _ in pl)
        add_pl(msp, rect(px - tmax, px + tmax, r["plan_y"] - umax, r["plan_y"] - umin),
               dict(A, linetype="DASHED") if "DASHED" in doc.linetypes else A)
        # 寸法: FL〜下端 / 扉側ブース面〜端部
        bot = HOOK_Y + hmin
        d1 = msp.add_linear_dim(base=(r["side_x"] - 330, 0), p1=(r["side_x"], FL_Y), p2=(r["side_x"], bot),
                                angle=90, dimstyle="GMM011", override={"dimdec": 0}, dxfattribs=A)
        d1.render()
        yb = HOOK_Y + hmin - 70
        d2 = msp.add_linear_dim(base=(0, yb), p1=(r["side_x"] + umax, yb), p2=(r["booth_x"], yb),
                                dimstyle="GMM011", override={"dimdec": 0}, dxfattribs=A)
        d2.render()
        dims.append((room, round(bot - FL_Y), round(r["booth_x"] - (r["side_x"] + umax))))
        txt = (f"{name}（モップ掛 1番フック・扉側）\\P"
               f"下端 FL+{round(bot - FL_Y)}　扉側ブース面まで {round(r['booth_x'] - (r['side_x'] + umax))}")
        msp.add_mtext(txt, dxfattribs=dict(A, style="追記文字", char_height=55,
                      insert=(r["side_x"] - 700, HOOK_Y + 780), attachment_point=7))
        msp.add_line((r["side_x"] - 400, HOOK_Y + 640), (r["side_x"], HOOK_Y + 10), dxfattribs=A)
    return dims

# ===================== 出力 =====================
def render_doc(doc):
    """表示用: SHXフォントを日本語TTFに差し替えたコピーを返す"""
    d = doc
    for s in d.styles:
        s.dxf.font = "wqy-zenhei.ttc"
        s.dxf.discard("bigfont")
    return d

def draw(ax, doc, lim=None):
    Frontend(RenderContext(doc), MatplotlibBackend(ax),
             config=Configuration(color_policy=ColorPolicy.COLOR_SWAP_BW)).draw_layout(doc.modelspace(), finalize=False)
    ext = ezdxf.bbox.extents(doc.modelspace())
    x0, y0, x1, y1 = lim or (ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")

plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
summary = {}
for name, it in ITEMS.items():
    doc, _ = recover.readfile(SRC)
    summary[name] = annotate(doc, name, it["color"])
    stem = f"FAMF-K1211-INO_{name}吊り下げ"
    doc.saveas(OUT / f"{stem}.dxf")
    rdoc = render_doc(recover.readfile(OUT / f"{stem}.dxf")[0])
    with PdfPages(OUT / f"{stem}.pdf") as pdf:
        for title, lim in ((f"{name}を1番フック（扉側）に掛けた場合 ― 東WWC", (300, 950, 3700, 4200)),
                           (f"{name}を1番フック（扉側）に掛けた場合 ― 東MWC", (3800, 950, 7500, 4200)),
                           ("FAMF-K1211-INO 全体（追記入り）", None)):
            fig = plt.figure(figsize=(16.54, 11.69))   # A3横
            ax = fig.add_axes([0.02, 0.02, 0.96, 0.9])
            draw(ax, rdoc, lim if lim else (790, -50, 11250, 7900))
            fig.text(0.03, 0.95, title, fontsize=18)
            fig.text(0.03, 0.925, "赤/青線＝追記（ホウキ・モップは build.py のモデル寸法。吊り下げ時は鉛直に垂れる想定）", fontsize=10, color="#555")
            pdf.savefig(fig); plt.close(fig)
print(summary)
