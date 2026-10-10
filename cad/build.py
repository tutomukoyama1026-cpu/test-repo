"""ホウキ・モップの3Dモデル生成スクリプト (CadQuery)
単位: mm / 写真の実測値 + 想定値(モップ柄)
実行: python build.py  -> out/ に STEP / STL を出力
"""
import math
from pathlib import Path
import cadquery as cq

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# ===================== ホウキ (写真1・2 実測) =====================
# 座標: XY=ホウキ平面, Y=柄の軸方向(グリップ端 y=0), Z=厚み方向
B = dict(
    grip_len=85,        # グリップ(フック付)長さ
    grip_d=24,
    pipe_d=18,          # 白パイプ径
    neck_y=675,         # 柄とヘッドの接続位置
    head_angle=15,      # ヘッドの傾き(斜めカット) [deg]
    holder_h=80,        # 黄色ホルダー高さ(首〜毛の付け根)
    holder_w=225,       # 毛の付け根幅
    holder_t=20,        # ホルダー厚み
    neck_offset=-44,    # 首位置のホルダー中心からのずれ
    bristle_len=75,     # 毛の長さ
    bristle_tip_w=260,  # 毛先の広がり幅
    bristle_t0=24, bristle_t1=32,
)

def broom():
    b = B
    # --- グリップ(フック+吊り穴)
    grip = (cq.Workplane("XZ").workplane(offset=-20).circle(b["grip_d"]/2)
            .extrude(-(b["grip_len"]-20)))                    # y=20..85
    grip = grip.union(cq.Workplane("XY").sphere(b["grip_d"]/2).translate((0, 20, 0)))
    hook = (cq.Workplane("XY").center(10, 12).circle(17).circle(6)
            .extrude(12).translate((0, 0, -6)))
    grip = grip.union(hook)
    # --- パイプ
    pipe = (cq.Workplane("XZ").workplane(offset=-b["grip_len"]).circle(b["pipe_d"]/2)
            .extrude(-(b["neck_y"] - b["grip_len"] + 30)))

    # --- ヘッド(ローカル座標: 首=原点, +y が毛先方向)
    cx = -b["neck_offset"]                 # ホルダー中心のx
    xl, xr = cx - b["holder_w"]/2, cx + b["holder_w"]/2
    h = b["holder_h"]
    prof = [(-13, 0), (13, 0), (xr - 12, h - 20), (xr, h - 12), (xr, h),
            (xl, h), (xl, h - 18), (-30, 6)]
    holder = (cq.Workplane("XY").polyline(prof).close().extrude(b["holder_t"])
              .translate((0, 0, -b["holder_t"]/2)).edges("|Z").fillet(3))
    for sx in (cx - 70, cx + 60):           # 表面の長穴(2箇所)
        slot = cq.Workplane("XY").center(sx, h - 9).slot2D(22, 6).extrude(3).translate((0, 0, b["holder_t"]/2 - 2))
        holder = holder.cut(slot)
    socket = (cq.Workplane("XZ").circle(13).extrude(45).translate((0, 8, 0)))  # 首ソケット y=-37..8
    ferrule = cq.Workplane("XY").box(b["holder_w"], 6, 26).translate((cx, h + 3, 0))
    bristle = (cq.Workplane("XZ").workplane(offset=-(h + 6)).center(cx, 0)
               .rect(b["holder_w"] - 4, b["bristle_t0"])
               .workplane(offset=-b["bristle_len"]).rect(b["bristle_tip_w"], b["bristle_t1"])
               .loft())
    head_plastic = holder.union(socket)
    rot = lambda s: s.rotate((0, 0, 0), (0, 0, 1), b["head_angle"]).translate((0, b["neck_y"], 0))

    asm = cq.Assembly(name="broom")
    asm.add(grip, name="grip", color=cq.Color(0.85, 0.9, 0.3))
    asm.add(pipe, name="pipe", color=cq.Color(0.95, 0.95, 0.95))
    asm.add(rot(head_plastic), name="head_holder", color=cq.Color(0.85, 0.9, 0.3))
    asm.add(rot(ferrule), name="ferrule", color=cq.Color(0.1, 0.1, 0.1))
    asm.add(rot(bristle), name="bristle", color=cq.Color(0.15, 0.15, 0.2))
    return asm

# ===================== モップ (写真4 実測 + 柄は想定) =====================
# 座標: Z=上方向, 糸の下端 z=0, X=幅方向, Y=奥行
M = dict(
    yarn_w=190, yarn_t=35, yarn_len=280,   # 糸(房)  ※長さは想定
    band_h=25,                             # 縫製テープ
    holder_w=210, holder_d=40, holder_h=17,# 赤ホルダー(クリップ式)
    hump_w=85, hump_h=10,                  # 中央の山形リブ
    joint_h=45,                            # 首振りジョイント(想定)
    pipe_d=25, pipe_len=1200,              # 柄パイプ(想定)
    grip_d=29, grip_len=220,               # 柄グリップ(想定)
)

def mop():
    m = M
    z_holder = m["yarn_len"]                # ホルダー下面
    # --- 糸: φ4.5 の撚り糸を 40列×5行で表現
    strands = cq.Workplane("XY")
    nx, ny = 40, 5
    for i in range(nx):
        for j in range(ny):
            x = -m["yarn_w"]/2 + 2.4 + i * (m["yarn_w"] - 4.8) / (nx - 1)
            y = -m["yarn_t"]/2 + 2.4 + j * (m["yarn_t"] - 4.8) / (ny - 1) + (1.2 if i % 2 else 0)
            L = m["yarn_len"] - 8 * ((i * 7 + j * 3) % 5) / 4     # 長さバラつき
            strands = strands.add(cq.Solid.makeCylinder(2.25, L, cq.Vector(x, y, z_holder - L)))
    yarn = cq.Workplane("XY").add(cq.Compound.makeCompound(strands.vals()))
    band = cq.Workplane("XY").box(m["yarn_w"] + 4, 8, m["band_h"]).translate((0, 0, z_holder - m["band_h"]/2 + 6))

    # --- 赤ホルダー: 前後2枚のあご + 上板 (テープを挟み込む)
    W, D, H = m["holder_w"], m["holder_d"], m["holder_h"]
    holder = cq.Workplane("XY").box(W, D, H).translate((0, 0, z_holder + H/2)).edges("|Z").fillet(4)
    slot = cq.Workplane("XY").box(W + 2, 9, H - 5).translate((0, 0, z_holder + (H - 5)/2))
    holder = holder.cut(slot)
    hump = (cq.Workplane("XZ").center(0, z_holder + H)
            .moveTo(-m["hump_w"]/2, 0).threePointArc((0, m["hump_h"]), (m["hump_w"]/2, 0)).close()
            .extrude(D/2, both=True))
    holder = holder.union(hump)
    for k in (-1, 1):                      # 山形部のリブ穴(意匠)
        holder = holder.cut(cq.Workplane("XY").box(22, D + 2, 4).translate((k * 18, 0, z_holder + H + 3)))

    # --- ジョイント (想定: Y軸ピン回りに首振り)
    zj = z_holder + H + m["hump_h"]
    yoke = (cq.Workplane("XY").box(30, 24, 22).translate((0, 0, zj + 11)).edges("|Y").fillet(5)
            .cut(cq.Workplane("XY").box(12, 26, 16).translate((0, 0, zj + 16))))
    pin = cq.Workplane("XZ").circle(4).extrude(15, both=True).translate((0, 0, zj + 16))
    knuckle = (cq.Workplane("XY").circle(14).extrude(m["joint_h"] - 16).translate((0, 0, zj + 22))
               .union(cq.Workplane("XY").box(11, 16, 14).translate((0, 0, zj + 20))))
    joint = yoke.union(knuckle)

    # --- 柄 (想定)
    zp = zj + m["joint_h"] + 6
    pipe = cq.Workplane("XY").circle(m["pipe_d"]/2).circle(m["pipe_d"]/2 - 1.2).extrude(m["pipe_len"]).translate((0, 0, zp - 30))
    zg = zp - 30 + m["pipe_len"] - m["grip_len"]
    grip = (cq.Workplane("XY").circle(m["grip_d"]/2).extrude(m["grip_len"]).translate((0, 0, zg))
            .faces(">Z").edges().fillet(5))
    cap = (cq.Workplane("XY").box(30, 12, 40).translate((0, 0, zg + m["grip_len"] + 15)).edges("|Y").fillet(8)
           .cut(cq.Workplane("XZ").circle(6).extrude(10, both=True).translate((0, 0, zg + m["grip_len"] + 22))))

    asm = cq.Assembly(name="mop")
    asm.add(yarn, name="yarn", color=cq.Color(0.6, 0.6, 0.62))
    asm.add(band, name="band", color=cq.Color(0.5, 0.5, 0.55))
    asm.add(holder, name="holder", color=cq.Color(0.8, 0.15, 0.15))
    asm.add(joint, name="joint", color=cq.Color(0.2, 0.2, 0.2))
    asm.add(pin, name="pin", color=cq.Color(0.7, 0.7, 0.7))
    asm.add(pipe, name="handle_pipe", color=cq.Color(0.75, 0.78, 0.8))
    asm.add(grip, name="handle_grip", color=cq.Color(0.2, 0.3, 0.7))
    asm.add(cap, name="handle_cap", color=cq.Color(0.2, 0.3, 0.7))
    return asm

if __name__ == "__main__":
    for name, fn in (("broom", broom), ("mop", mop)):
        asm = fn()
        asm.save(str(OUT / f"{name}.step"))
        cq.exporters.export(asm.toCompound(), str(OUT / f"{name}.stl"), tolerance=0.3, angularTolerance=0.3)
        bb = asm.toCompound().BoundingBox()
        print(f"{name}: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm")
