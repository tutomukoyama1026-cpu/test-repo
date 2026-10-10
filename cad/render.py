"""プレビュー画像生成 (matplotlib)"""
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import build

def tris(asm):
    out = []
    for c in asm.children:
        shape = c.obj.val() if hasattr(c.obj, "val") else c.obj
        v, t = shape.tessellate(1.0, 0.5)
        v = np.array([[p.x, p.y, p.z] for p in v])
        col = c.color.toTuple()[:3] if c.color else (0.7, 0.7, 0.7)
        out.append((v[np.array(t)], col))
    return out

def shade(tri, col):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    k = 0.45 + 0.55 * np.abs(n @ np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8]))
    return np.clip(np.array(col)[None] * k[:, None], 0, 1)

def render(asm, fname, views):
    data = tris(asm)
    allv = np.concatenate([d[0].reshape(-1, 3) for d in data])
    lo, hi = allv.min(0), allv.max(0); mid = (lo + hi) / 2; r = (hi - lo).max() / 2
    fig = plt.figure(figsize=(6 * len(views), 7))
    for i, (el, az, title) in enumerate(views):
        ax = fig.add_subplot(1, len(views), i + 1, projection="3d")
        for tri, col in data:
            ax.add_collection3d(Poly3DCollection(tri, facecolors=shade(tri, col), linewidths=0))
        for f, m in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), mid):
            f(m - r, m + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(el, az); ax.set_axis_off(); ax.set_title(title)
    fig.tight_layout(); fig.savefig(fname, dpi=110); plt.close(fig)

render(build.broom(), "out/broom_preview.png", [(90, -90, "Top (XY)"), (25, -60, "Iso")])
render(build.mop(), "out/mop_preview.png", [(0, -90, "Front"), (15, -55, "Iso"), (10, 0, "Side")])
