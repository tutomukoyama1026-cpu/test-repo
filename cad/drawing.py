"""2D図面(DXF)生成: 断面外形 + 主要寸法"""
import cadquery as cq, ezdxf
import build

def section_dxf(asm, plane_rot, fname, dims, txt=8):
    shape = asm.toCompound()
    if plane_rot:  # XZ平面の外形が欲しい場合は X 軸回りに回して XY に寝かせる
        shape = shape.rotate((0, 0, 0), (1, 0, 0), plane_rot)
    sec = cq.Workplane("XY").add(shape).section(0)
    tmp = fname + ".tmp.dxf"
    cq.exporters.export(sec, tmp)
    doc = ezdxf.readfile(tmp)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    doc.dimstyles.get("Standard").dxf.dimtxt = txt
    doc.dimstyles.get("Standard").dxf.dimasz = txt * 0.6
    for p1, p2, base, ang, *loc in dims:
        msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang,
                           location=loc[0] if loc else None).render()
    doc.saveas(fname)
    import os; os.remove(tmp)

b, m = build.B, build.M
section_dxf(build.broom(), 0, "out/broom.dxf", [
    ((0, 0), (0, 876), (-170, 0), 90),          # 全長
    ((0, 0), (0, b["neck_y"]), (-120, 0), 90),  # グリップ端〜首
    ((-125, 876), (127, 876), (0, 910), 0),     # 毛先幅
])
zt = m["yarn_len"]
section_dxf(build.mop(), -90, "out/mop.dxf", [
    ((0, 0), (0, 1563), (-160, 0), 90),          # 全高
    ((0, 0), (0, zt), (-120, 0), 90),            # 糸長さ
    ((-105, zt + 17), (105, zt + 17), (0, zt + 60), 0, (-160, zt + 72)),   # ホルダー幅
    ((-95, 0), (95, 0), (0, -40), 0),            # 糸幅
], txt=20)
print("ok")
