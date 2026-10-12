"""固定バー（φ25 SUS）の荷重想定と検討図（A3横 PDF/PNG）
使い方: python load.py <出力フォルダ>
"""
import sys, math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "WenQuanYi Zen Hei"
G = 9.81

# ---- 掛け物 1本あたりの想定（濡れた状態）
ITEMS = [("雑巾（濡れ・軽く絞り）", 0.25), ("マイクロファイバークロス（濡れ）", 0.15),
         ("ゴム手袋 1双（濡れ）", 0.12), ("ハンガー本体（ピンチ付き含む）", 0.05)]
PER_HANGER = 0.35          # kg/本 = 雑巾0.25＋予備0.05＋ハンガー0.05（重い側で丸め）
PITCH = 70                 # mm（現況写真：約800mmに10〜11本）
FACTOR = 1.5               # 水が垂れるほど濡れている・詰めて掛ける余裕
P_POINT = 20.0             # kg 集中荷重（バケツを掛ける・手をつく等の誤使用）

# ---- バー断面: SUS304 φ25 t1.2（想定）
D, T, E, FY = 25.0, 1.2, 193000.0, 205.0
d = D - 2 * T
I = math.pi / 64 * (D**4 - d**4); Z = I / (D / 2)

ROOMS = {"東WWC": 816.0, "東MWC": 1210.0}   # 壁内法
FL_T = 12.0                                   # フランジ厚
EDGE = 60.0                                   # フランジ際は掛けない

def check(W):
    L = W - 2 * FL_T                          # 支点間（安全側に単純支持）
    n = int((W - 2 * EDGE) // PITCH) + 1
    wkg = n * PER_HANGER * FACTOR
    w = wkg * G / L                           # N/mm 等分布
    M1 = w * L**2 / 8; d1 = 5 * w * L**4 / (384 * E * I)
    P = P_POINT * G
    M2 = P * L / 4;   d2 = P * L**3 / (48 * E * I)
    return dict(L=L, n=n, wkg=wkg, base=n * PER_HANGER,
                s1=M1 / Z, d1=d1, R1=wkg * G / 2,
                s2=M2 / Z, d2=d2, R2=P / 2)

res = {k: check(v) for k, v in ROOMS.items()}

fig = plt.figure(figsize=(16.54, 11.69))
fig.text(0.04, 0.95, "固定バー 荷重想定図（濡れ雑巾などを干す）", fontsize=22, weight="bold")
fig.text(0.04, 0.925, f"バー：SUS304 φ{D:.0f} t{T}（想定）／FL+1775・奥壁から325／両端フランジ ビス留め（既存下地補強内）　単位：mm, kg",
         fontsize=11, color="#444")

def draw_room(ax, name, W, r):
    ax.set_xlim(-200, 1400); ax.set_ylim(-560, 330); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"{name}（内法 {W:.0f}）", fontsize=14, loc="left")
    # 壁・フランジ・バー
    for x0 in (-60, W):
        ax.add_patch(Rectangle((x0, -480), 60, 760, hatch="///", fill=False, lw=0.8, color="#888"))
    for x0 in (0, W - FL_T):
        ax.add_patch(Rectangle((x0, -30), FL_T, 60, color="#2a7"))
    ax.add_patch(Rectangle((FL_T, -12.5), W - 2 * FL_T, 25, color="#2a7"))
    # ハンガー＋雑巾
    xs = [EDGE + i * PITCH for i in range(r["n"])]
    for x in xs:
        ax.plot([x, x], [12, 40], color="#333", lw=1)
        ax.add_patch(Polygon([(x - 28, -40), (x, 0), (x + 28, -40)], closed=False, fill=False, lw=1, color="#333"))
        ax.add_patch(Rectangle((x - 26, -260), 52, 220, color="#7ab6e8", alpha=0.6, lw=0))
        ax.add_patch(FancyArrowPatch((x, -270), (x, -340), arrowstyle="-|>", mutation_scale=10, color="#c33"))
    ax.text(xs[0] - 10, -370, f"{PER_HANGER} kg/本 × {r['n']}本（@{PITCH}）", fontsize=11, color="#c33", va="top")
    ax.text(xs[0] - 10, -410, f"= {r['base']:.1f} kg → ×{FACTOR} 余裕 = {r['wkg']:.1f} kg（等分布）",
            fontsize=11, color="#c33", va="top")
    # 集中荷重
    ax.add_patch(FancyArrowPatch((W / 2, 230), (W / 2, 20), arrowstyle="-|>", mutation_scale=18, lw=2, color="#a40"))
    ax.text(W / 2 + 15, 200, f"誤使用 {P_POINT:.0f} kg（中央集中）\n※等分布とは別に検討", fontsize=11, color="#a40")
    ax.text(-60, -515, f"支点反力（片側）：常時 {r['R1']/G:.1f} kg　誤使用 {r['R2']/G:.0f} kg", fontsize=11)

axes = [fig.add_axes([0.03, 0.47, 0.46, 0.43]), fig.add_axes([0.51, 0.47, 0.46, 0.43])]
for ax, (k, W) in zip(axes, ROOMS.items()):
    draw_room(ax, k, W, res[k])

# ---- 想定重量表
ax = fig.add_axes([0.04, 0.08, 0.36, 0.33]); ax.axis("off")
ax.set_title("掛け物1本あたりの想定（濡れた状態）", fontsize=13, loc="left")
rows = [[n, f"{w:.2f}"] for n, w in ITEMS] + [["1本あたり設計値（重い側で丸め）", f"{PER_HANGER:.2f}"]]
t = ax.table(cellText=rows, colLabels=["掛け物", "重さ kg"], colWidths=[0.75, 0.25], loc="upper left", cellLoc="left")
t.auto_set_font_size(False); t.set_fontsize(11); t.scale(1, 1.7)
for (i, j), c in t.get_celld().items():
    if i == 0: c.set_facecolor("#e8e8e8")
    if i == len(rows): c.set_text_props(weight="bold")
ax.text(0, 0.42, f"掛けピッチ {PITCH}mm は現況写真（約800mmに10〜11本）から。\nフランジ際 {EDGE:.0f}mm は掛けない想定。",
        fontsize=10, transform=ax.transAxes, va="top")

# ---- 検討結果表
ax = fig.add_axes([0.44, 0.08, 0.53, 0.33]); ax.axis("off")
ax.set_title(f"検討結果（単純支持で安全側／φ{D:.0f} t{T}: I={I:.0f}mm⁴, Z={Z:.0f}mm³, 許容 {FY:.0f}N/mm²）", fontsize=13, loc="left")
rows = []
for k, r in res.items():
    rows.append([k, f"常時 {r['wkg']:.1f}kg 等分布", f"{r['s1']:.0f}", f"{r['d1']:.1f}", "OK"])
    rows.append([k, f"誤使用 {P_POINT:.0f}kg 中央", f"{r['s2']:.0f}", f"{r['d2']:.1f}",
                 "OK" if r["s2"] < FY else "NG"])
t = ax.table(cellText=rows, colLabels=["室", "荷重ケース", "曲げ応力 N/mm²", "たわみ mm", "判定"],
             colWidths=[0.14, 0.32, 0.2, 0.17, 0.12], loc="upper left", cellLoc="center")
t.auto_set_font_size(False); t.set_fontsize(11); t.scale(1, 1.7)
for (i, j), c in t.get_celld().items():
    if i == 0: c.set_facecolor("#e8e8e8")
r = res["東MWC"]
ax.text(0, 0.5, f"・常時荷重はどちらの室も余裕大。厳しいのは東MWC（スパン {r['L']:.0f}）の誤使用時で、\n"
        f"　応力 {r['s2']:.0f}/{FY:.0f}（安全率 {FY/r['s2']:.1f}）・たわみ {r['d2']:.1f}mm。t1.5以上にするか、中間サポートで余裕が増える。\n"
        f"・フランジ1か所あたりの荷重は最大 約{r['R2']/G:.0f}kg（せん断）。ビス3本以上で下地補強に留めれば十分。",
        fontsize=10.5, transform=ax.transAxes, va="top")

fig.savefig(OUT / "固定バー_荷重想定図.pdf"); fig.savefig(OUT / "固定バー_荷重想定図.png", dpi=80)
for k, r in res.items(): print(k, {a: round(b, 2) for a, b in r.items()})
