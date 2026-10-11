"""図面PDF生成 (A3横): 2D外形寸法図 + 3Dビュー + 寸法表"""
import datetime, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import ezdxf, ezdxf.bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import build
from render import tris, shade

plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
A3 = (420 / 25.4, 297 / 25.4)

SHEETS = [
    dict(no="CL-001", name="ホウキ（自在ほうき・斜めヘッド）", dxf="out/broom.dxf", asm=build.broom,
         views=[(90, -90, "上面図"), (25, -60, "等角図")],
         rows=[("全長（グリップ端〜毛先）", "約 876", "実測"),
               ("グリップ端〜ヘッド首", "675", "実測"),
               ("柄パイプ径", "φ18", "実測"),
               ("グリップ（フック付）", "φ24 × 85", "実測"),
               ("ヘッド傾き", "15°", "実測"),
               ("ホルダー 幅×高さ×厚み", "225 × 80 × 20", "実測"),
               ("毛 長さ", "75", "実測"),
               ("毛先 幅", "約 260", "実測"),
               ("毛 厚み（付根〜先端）", "24 〜 32", "推定")],
         note="写真1・2のメジャーから読み取り。厚み方向は写真で確認できないため推定値。"),
    dict(no="CL-002", name="モップ（クリップ式 糸モップ）", dxf="out/mop.dxf", asm=build.mop,
         views=[(15, -55, "等角図"), (10, 0, "側面図")],
         rows=[("全高", "約 1563", "—"),
               ("ホルダー 幅×奥行×高さ", "210 × 40 × 17", "実測"),
               ("ホルダー中央山形 幅×高さ", "85 × 10", "実測"),
               ("糸 幅", "190", "実測"),
               ("糸 厚み", "35", "推定"),
               ("糸 長さ", "280", "想定"),
               ("ジョイント（首振り）高さ", "45", "想定"),
               ("柄パイプ", "φ25 × 1200 (t1.2)", "想定"),
               ("グリップ", "φ29 × 220", "想定")],
         note="写真4のメジャーから読み取り。柄（パイプ・ジョイント・グリップ）は別部品のため一般的な業務用モップ柄を想定。"),
]

def draw_dxf(ax, path):
    doc = ezdxf.readfile(path)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=Configuration(color_policy=ColorPolicy.BLACK, lineweight_scaling=0.6)).draw_layout(doc.modelspace(), finalize=False)
    ext = ezdxf.bbox.extents(doc.modelspace())
    pad = 0.04 * max(ext.size.x, ext.size.y)
    ax.set_xlim(ext.extmin.x - pad, ext.extmax.x + pad); ax.set_ylim(ext.extmin.y - pad, ext.extmax.y + pad)
    ax.set_aspect("equal", adjustable="datalim"); ax.axis("off")

def draw_3d(ax, data, el, az, title):
    allv = np.concatenate([d[0].reshape(-1, 3) for d in data])
    lo, hi = allv.min(0), allv.max(0); mid = (lo + hi) / 2; r = (hi - lo).max() / 2
    for tri, col in data:
        ax.add_collection3d(Poly3DCollection(tri, facecolors=shade(tri, col), linewidths=0))
    for f, m in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), mid):
        f(m - r, m + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(el, az); ax.set_axis_off()
    ax.set_title(title, fontsize=11)

def sheet(pdf, s, page, total):
    fig = plt.figure(figsize=A3)
    # 図枠
    fig.add_artist(plt.Rectangle((0.02, 0.025), 0.96, 0.95, fill=False, lw=1.5, transform=fig.transFigure))
    fig.text(0.04, 0.94, s["name"], fontsize=20, weight="bold")
    fig.text(0.04, 0.915, "外形寸法図（正面）／ 単位: mm", fontsize=11, color="#444")
    draw_dxf(fig.add_axes([0.04, 0.07, 0.34, 0.83]), s["dxf"])
    data = tris(s["asm"]())
    for i, (el, az, t) in enumerate(s["views"]):
        draw_3d(fig.add_axes([0.40 + i * 0.29, 0.50, 0.28, 0.40], projection="3d"), data, el, az, t)
    # 寸法表
    ax = fig.add_axes([0.42, 0.20, 0.54, 0.28]); ax.axis("off")
    tb = ax.table(cellText=[list(r) for r in s["rows"]], colLabels=["項目", "寸法 (mm)", "根拠"],
                  colWidths=[0.5, 0.32, 0.18], loc="upper center", cellLoc="left")
    tb.auto_set_font_size(False); tb.set_fontsize(10.5); tb.scale(1, 1.45)
    for (r, c), cell in tb.get_celld().items():
        if r == 0: cell.set_facecolor("#e8e8e8"); cell.set_text_props(weight="bold")
        elif c == 2 and cell.get_text().get_text() in ("想定", "推定"): cell.set_text_props(color="#b03000")
    fig.text(0.42, 0.175, "注: " + s["note"], fontsize=9.5, wrap=True)
    # 表題欄
    tx = fig.add_axes([0.62, 0.035, 0.35, 0.11]); tx.axis("off")
    t = tx.table(cellText=[["図番", s["no"], "尺度", "NTS"],
                           ["品名", s["name"], "単位", "mm"],
                           ["作成日", datetime.date.today().isoformat(), "頁", f"{page}/{total}"]],
                 colWidths=[0.14, 0.56, 0.12, 0.18], loc="center", cellLoc="left")
    t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 2.0)
    pdf.savefig(fig); plt.close(fig)

with PdfPages("out/drawings.pdf") as pdf:
    for i, s in enumerate(SHEETS, 1):
        sheet(pdf, s, i, len(SHEETS))
    d = pdf.infodict(); d["Title"] = "ホウキ・モップ 図面"
print("ok")
