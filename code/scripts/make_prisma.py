#!/usr/bin/env python3
"""Reproducible PRISMA 2020-style flow diagram for the guideline evidence-gap study.

Single structured identification search (June 2026). Counts are derived live from
the consolidated atlas so the figure never drifts from the data. Layout follows the
PRISMA 2020 flow-diagram template (Page et al., BMJ 2021): a left phase sidebar
(Identification / Screening / Included), a single main flow column, and an
exclusions box branching to the right. Names are spelled out in full.

Outputs pdf/png/svg to data/figures/. Run with /usr/bin/python3 (has matplotlib).
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

matplotlib.rcParams["font.family"] = "Arial"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "data/figures")


def live_counts():
    db = json.load(open(os.path.join(ROOT, "data/evidence_atlas.json")))
    gls, recs = db["guidelines"], db["recommendations"]
    a = json.load(open(os.path.join(ROOT, "data/analysis/comprehensive_analysis.json")))
    sg = a["primary_analysis"]["specialty_gaps"]  # specialties with >=5 guidelines
    return {
        "guidelines": len(gls),
        "societies": len({g["society"] for g in gls}),
        "specialties": len({g["specialty"] for g in gls}),
        "recs": len(recs),
        "prim_recs": sum(s["n_recommendations"] for s in sg),
        "prim_soc": len({soc for s in sg for soc in s["societies"]}),
        "prim_spec": len(sg),
    }


C = live_counts()

# Society-level identification (the defensible, itemizable denominator).
# Guideline-level screened/excluded counts are NOT asserted: the excluded-record
# set is de-duplication/extraction churn (failed-extraction stubs, list-only
# entries, and out-of-frame societies), so a hard "n retrieved / n excluded"
# does not hold up. Only the included count (536, from the atlas) is reported at
# the guideline level; exclusion reasons are listed qualitatively.
CANDIDATE_SOCIETIES = 84  # candidate societies identified by the structured search
SOC_NOT_OBTAINED = 7      # societies excluded: paywalled or non-English only (eTable 2)
INCLUDED_SOCIETIES = CANDIDATE_SOCIETIES - SOC_NOT_OBTAINED   # 77

# ----------------------------------------------------------------------------- #
fig, ax = plt.subplots(figsize=(11, 9))
ax.set_xlim(0, 100)
ax.set_ylim(15, 100)   # content spans y 18-99; trims the empty lower canvas
ax.axis("off")

WHITE, GREEN, GREY = "#ffffff", "#e6f0dc", "#f2f2f2"
BAND_BLUE, BAND_GREEN = "#dbe6f4", "#e0eed4"
EDGE = "#3d3d3d"

SB_X, SB_W = 1.0, 7.0          # left phase sidebar
MAIN_X, MAIN_W = 11.0, 52.0    # main flow column
MX = MAIN_X + MAIN_W / 2       # main column centre
EXC_X, EXC_W = 65.0, 34.0      # exclusions column


def box(x, y, w, h, text, fc=WHITE, ha="center", fs=10.0, ec=EDGE):
    ax.add_patch(Rectangle((x, y), w, h, linewidth=1.1, edgecolor=ec,
                           facecolor=fc, zorder=2))
    tx = x + 2.2 if ha == "left" else x + w / 2
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs,
            color="#111111", linespacing=1.5, zorder=3)


def band(y, h, label, fc):
    ax.add_patch(Rectangle((SB_X, y), SB_W, h, linewidth=0, facecolor=fc, zorder=1))
    ax.text(SB_X + SB_W / 2, y + h / 2, label, ha="center", va="center",
            rotation=90, fontsize=13, fontweight="bold", color="#1f3864", zorder=2)


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=18, linewidth=1.3,
                                 color="#333333", zorder=2))


# ----- phase sidebar -----
band(60.0, 40.0, "Identification", BAND_BLUE)
band(46.0, 13.0, "Screening", BAND_BLUE)
band(18.0, 27.0, "Included", BAND_GREEN)

# ----- identification -----
box(MAIN_X, 89.0, MAIN_W, 10.0,
    "Medical specialties defined using the American Board of\n"
    "Medical Specialties (24 boards, 38 specialties) and the\n"
    "European Union of Medical Specialists (43 sections)",
    ha="left", fs=10.0)

box(MAIN_X, 70.0, MAIN_W, 15.0,
    "Guideline-issuing professional societies identified through\n"
    "guideline registries (ECRI, Guidelines International Network),\n"
    "PubMed (Practice Guideline type), society websites, and an\n"
    "audit of graded guidance in societies' own journals (June 2026).\n"
    f"{CANDIDATE_SOCIETIES} candidate societies; {SOC_NOT_OBTAINED} not obtained (paywalled or\n"
    f"non-English only), yielding {INCLUDED_SOCIETIES} included societies",
    ha="left", fs=10.0)

box(MAIN_X, 61.0, MAIN_W, 6.5,
    f"Current guidelines of the {INCLUDED_SOCIETIES} included societies\n"
    "retrieved (PubMed Central, publisher open access)",
    ha="left", fs=10.0)

# ----- screening -----
box(MAIN_X, 49.0, MAIN_W, 6.5,
    "Guidelines screened against the prespecified\n"
    "eligibility criteria",
    ha="left", fs=10.0)

box(EXC_X, 38.0, EXC_W, 25.0,
    "Guidelines excluded:\n\n"
    "•  Superseded or duplicate edition (de-\n"
    "    duplicated to the most recent version)\n\n"
    "•  Graded by strength of recommendation\n"
    "    only, with no level of evidence\n\n"
    "•  No per-recommendation evidence grading\n\n"
    "•  Not a clinical practice guideline (review,\n"
    "    commentary, methods, or letter)",
    fc=GREY, ha="left", fs=8.5, ec="#8a8a8a")

# ----- included -----
box(MAIN_X, 38.0, MAIN_W, 7.0,
    f"Clinical practice guidelines included and extracted\n"
    f"(n = {C['guidelines']}; {C['societies']} professional societies, "
    f"{C['specialties']} specialties)",
    fc=GREEN, ha="left", fs=10.0)

box(MAIN_X, 28.0, MAIN_W, 7.0,
    f"Graded recommendations extracted (n = {C['recs']:,}); every\n"
    "evidence level mapped to the normalized scale (none unmappable)",
    fc=GREEN, ha="left", fs=10.0)

box(MAIN_X, 18.0, MAIN_W, 7.0,
    "Primary analysis — specialties with at least 5 guidelines\n"
    f"(n = {C['prim_recs']:,} recommendations; {C['prim_spec']} specialties; "
    f"{C['prim_soc']} societies)",
    fc=GREEN, ha="left", fs=10.0)

# ----- arrows -----
arrow(MX, 89.0, MX, 85.0)      # i1 -> i2
arrow(MX, 70.0, MX, 67.5)      # i2 -> i3
arrow(MX, 61.0, MX, 55.5)      # i3 -> s1
arrow(MX, 49.0, MX, 45.0)      # s1 -> inc1
arrow(MX, 38.0, MX, 35.0)      # inc1 -> inc2
arrow(MX, 28.0, MX, 25.0)      # inc2 -> inc3
arrow(MAIN_X + MAIN_W, 52.25, EXC_X, 52.25)   # screening -> excluded

for ext in ("pdf", "png", "svg"):
    out = os.path.join(FIG, f"efigure1_prisma_flow.{ext}")
    fig.savefig(out, bbox_inches="tight", dpi=300, pad_inches=0.05)
    print("wrote", out)
plt.close(fig)
print("counts:",C,"| societies:",CANDIDATE_SOCIETIES,"->",INCLUDED_SOCIETIES)
