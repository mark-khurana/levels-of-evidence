#!/usr/bin/env python3
"""Reproducible study-design schematic (Figure 1) for the guideline evidence-gap study.

Flat, JAMA-style recreation of the conceptual overview: medical specialties ->
guidelines -> recommendations -> normalized evidence level per recommendation ->
cross-specialty evidence comparison. Outputs pdf/png/svg to data/figures/.
Run with /usr/bin/python3 (has matplotlib).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon
from matplotlib.lines import Line2D

matplotlib.rcParams["font.family"] = "Arial"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "data/figures")

# Primary-analysis counts (manuscript denominator)
N_SPEC, N_GL, N_REC = 21, 522, 22693

# Normalized evidence tiers (green -> red), label and fill + text colour
# Normalized evidence tiers, matched to Figure 2 (pipeline/figures.py palette)
EV = [
    ("Multiple RCTs", "#1b4f72", "white"),
    ("Single RCT",    "#2980b9", "white"),
    ("Observational", "#85c1e9", "#333333"),
    ("Case series",   "#eb984e", "#333333"),
    ("Expert opinion","#c0392b", "white"),
]
# Example per-specialty A-E distributions (Table 1 values), for the summary bars
DIST = {
    "Cardiology":    [11.9, 9.1, 36.3, 37.2, 5.5],
    "Endocrinology": [11.6, 22.4, 24.1, 15.9, 26.0],
    "...":           [20.0, 25.0, 30.0, 15.0, 10.0],  # illustrative placeholder
}

NAVY = "#274a6d"
PANEL = "#eef3f8"
BOX = "#d9d9d9"
BOXEDGE = "#4d4d4d"
ARROW = "#333333"

fig, ax = plt.subplots(figsize=(13, 7.6))
ax.set_xlim(0, 170)
ax.set_ylim(0, 100)
ax.axis("off")


def rect(x, y, w, h, fc, ec=None, lw=1.0, z=2):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec or "none",
                           linewidth=lw, zorder=z))


def label(x, y, s, fs, color="#111111", bold=False, ha="center", va="center", z=4):
    ax.text(x, y, s, fontsize=fs, color=color, ha=ha, va=va, zorder=z,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def gbox(cx, cy, w, h, s, fs=9.5):
    rect(cx - w / 2, cy - h / 2, w, h, BOX, BOXEDGE, 1.0, z=3)
    label(cx, cy, s, fs, z=4)


def darrow(x1, y1, x2, y2, color=ARROW, lw=1.2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=11, linewidth=lw, color=color, zorder=3))


def bus(px, py_bot, child_cx, child_top):
    """Orthogonal parent->children connector with arrowheads into each child."""
    mid = (py_bot + child_top) / 2
    ax.add_line(Line2D([px, px], [py_bot, mid], color=ARROW, lw=1.1, zorder=3))
    ax.add_line(Line2D([min(child_cx + [px]), max(child_cx + [px])], [mid, mid],
                       color=ARROW, lw=1.1, zorder=3))
    for c in child_cx:
        darrow(c, mid, c, child_top)


# ----------------------------------------------------------------- panel + bg
rect(27, 1.5, 141.5, 97, PANEL, "#9fb4c9", 1.2, z=0)

# ----------------------------------------------------------------- sidebar
SB_X, SB_W = 1.5, 24.5
bands = [
    (83, 15, "Medical\nspecialties\n(n = 21)"),
    (69.5, 11, "Guidelines\n(n = 522)"),
    (56, 11, "Recommendations\n(n = 22,693)"),
    (37, 15, "Evidence level\nper\nrecommendation"),
    (5, 26, "Cross-specialty\nevidence\ncomparison"),
]
for y, h, txt in bands:
    rect(SB_X, y, SB_W, h, NAVY, z=1)
    label(SB_X + SB_W / 2, y + h / 2, txt, 10.5, "white", bold=True)

# ----------------------------------------------------------------- specialty groups
# container x-ranges and their (name, [guideline names]) ; "..." group is compact
GROUPS = [
    (30, 74, "Cardiology", ["Endocarditis", "Heart failure", "…"]),
    (77, 121, "Endocrinology", ["Thyroiditis", "Type 2 diabetes", "…"]),
    (124, 168, "…", ["…", "…", "…"]),
]
REC_LABELS = ["1", "2", "…"]


def specialty_tree_top(x0, x1, spec, gls):
    rect(x0, 55, x1 - x0, 43, "none", "#6f6f6f", 0.8, z=1)  # group container (top within panel)
    cx = (x0 + x1) / 2
    gbox(cx, 94.5, (x1 - x0) - 5, 5.5, spec, fs=10.5)        # specialty box
    n = len(gls)
    span = (x1 - x0) - 6
    step = span / n
    gl_cx = [x0 + 3 + step * (i + 0.5) for i in range(n)]
    gw = min(step - 1.0, 18)
    rec_centers_all = []
    for gx, name in zip(gl_cx, gls):
        gbox(gx, 83, gw, 5, name, fs=8.0 if len(name) <= 12 else 7.0)
        # recommendation boxes under this guideline
        rcs = [gx - gw / 2 + gw * (j + 0.5) / 3 for j in range(3)]
        for rc, rl in zip(rcs, REC_LABELS):
            gbox(rc, 71.5, gw / 3 - 0.8, 4.2, rl, fs=8.0)
        bus(gx, 80.5, rcs, 73.6)
        rec_centers_all += rcs
    bus(cx, 91.7, gl_cx, 85.5)
    return rec_centers_all


top_recs = []
for x0, x1, spec, gls in GROUPS:
    top_recs += specialty_tree_top(x0, x1, spec, gls)

# rec "stems" feeding the funnel
for rc in top_recs:
    rect(rc - 0.6, 66.5, 1.2, 3.0, "#c9c9c9", z=2)

# ----------------------------------------------------------------- funnel 1 (down to scale)
ax.add_patch(Polygon([(30, 66.5), (168, 66.5), (150, 54.5), (48, 54.5)],
                     closed=True, facecolor=NAVY, edgecolor="none", zorder=2))

# ----------------------------------------------------------------- evidence scale
SC_X0, SC_X1, SC_Y, SC_H = 34, 162, 45.5, 6.5
seg_w = (SC_X1 - SC_X0) / len(EV)
seg_centers = []
for i, (name, fc, tc) in enumerate(EV):
    sx = SC_X0 + i * seg_w
    rect(sx, SC_Y, seg_w, SC_H, fc, "white", 1.2, z=3)
    label(sx + seg_w / 2, SC_Y + SC_H / 2, name, 11.5, tc, bold=True)
    seg_centers.append(sx + seg_w / 2)

# colored fan arrows from funnel apex into each segment
apex = (98, 54.0)
for c, (name, fc, tc) in zip(seg_centers, EV):
    darrow(apex[0], apex[1], c, SC_Y + SC_H + 0.3, color=fc, lw=1.6)

# ----------------------------------------------------------------- funnel 2 (down to comparison)
ax.add_patch(Polygon([(48, 45.0), (150, 45.0), (168, 33.0), (30, 33.0)],
                     closed=True, facecolor=NAVY, edgecolor="none", zorder=2))

# ----------------------------------------------------------------- cross-specialty comparison
def specialty_tree_bottom(x0, x1, spec, gls, dist):
    cx = (x0 + x1) / 2
    n = len(gls)
    span = (x1 - x0) - 6
    step = span / n
    gl_cx = [x0 + 3 + step * (i + 0.5) for i in range(n)]
    gw = min(step - 1.0, 18)
    # recommendation boxes (top of the bottom block)
    for gx, name in zip(gl_cx, gls):
        rcs = [gx - gw / 2 + gw * (j + 0.5) / 3 for j in range(3)]
        for rc, rl in zip(rcs, REC_LABELS):
            gbox(rc, 29.5, gw / 3 - 0.8, 4.0, rl, fs=8.0)
        gbox(gx, 24, gw, 4.6, name, fs=8.0 if len(name) <= 12 else 7.0)
    # specialty bar
    gbox(cx, 18.5, (x1 - x0) - 5, 4.6, spec, fs=10.5)
    # bracket converging to the summary stacked bar
    by = 13.5
    ax.add_patch(Polygon([(x0 + 4, 16), (x1 - 4, 16), (cx + 9, by), (cx - 9, by)],
                         closed=True, facecolor="none", edgecolor="#6f6f6f", lw=0.9, zorder=2))
    # stacked evidence bar (real distribution)
    bw = min(40, (x1 - x0) - 6)
    bx0, byy, bh = cx - bw / 2, 5.5, 4.5
    left = bx0
    for pct, (name, fc, tc) in zip(dist, EV):
        w = bw * pct / 100.0
        rect(left, byy, w, bh, fc, "white", 0.6, z=3)
        left += w
    rect(bx0, byy, bw, bh, "none", BOXEDGE, 0.8, z=4)


for (x0, x1, spec, gls) in GROUPS:
    specialty_tree_bottom(x0, x1, spec, gls, DIST[spec if spec in DIST else "..."])

for ext in ("pdf", "png", "svg"):
    out = os.path.join(FIG, f"figure1_study_design.{ext}")
    fig.savefig(out, bbox_inches="tight", dpi=300, pad_inches=0.06)
    print("wrote", out)
plt.close(fig)
