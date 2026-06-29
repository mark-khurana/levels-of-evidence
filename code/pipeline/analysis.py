#!/usr/bin/env python3
"""
Comprehensive analysis for JAMA submission.

Produces:
  1. Primary analysis (LoE-only societies, no strength-based proxies)
  2. Extended analysis (including strength-based societies EAU/AAOS)
  3. Sensitivity analysis (normalization +/- 1 tier)
  4. Specialty-weighted analysis
  5. Temporal analysis (last 5 years vs older)
  6. Fanaroff 2019 benchmark comparison
  7. Validation sample (random 10%)
  8. Normalization confidence table

Usage:
  python analysis.py
"""

import json
import csv
import random
import statistics
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"
ATLAS = DATA_DIR / "evidence_atlas.json"
OUT_DIR = DATA_DIR / "analysis"
OUT_DIR.mkdir(exist_ok=True)

# Societies that use actual Level of Evidence (not strength-as-proxy)
LOE_SOCIETIES = {"ESC", "KDIGO", "ESGE", "ACR", "AGA", "AACE", "ESCMID", "IDSA",
                 "GINA", "ESMO", "EULAR", "ESPEN", "EAST", "SVS", "SCCM", "ACOG", "ASCRS",
                 "AHA/ACC", "ASCO", "ASH", "AAN", "Endocrine Society", "ACG", "ACEP",
                 "ADA", "GOLD", "ATS", "ERS", "BTS", "BSR", "AASLD", "EASL", "EAN",
                 "CANMAT", "ESHRE", "ISTH", "ATS/ERS", "ATS/ERS/IDSA/CDC", "ATS/ERS/JRS/ALAT",
                 "AAP", "WAO", "AAFP", "SAGES", "AAO-HNS", "ACP", "AGS",
                 "ATS/ERS/IDSA/ESCMID", "BSG", "SHEA", "RCOG", "AAOS"}
# Societies that use strength-of-recommendation as evidence proxy
# Note: AAOS embeds evidence quality in strength (Strong=high, Moderate=moderate,
# Limited=low, Consensus=expert opinion) and is retained in the primary analysis.
STRENGTH_SOCIETIES = {"EAU"}

# Minimum guidelines per specialty for inclusion in primary analysis
MIN_RECS_PER_SPECIALTY = 0  # No minimum rec count; >=5 GL is sufficient
MIN_GUIDELINES_PER_SPECIALTY = 5

# Normalization confidence: how defensible is each mapping?
NORM_CONFIDENCE = {
    # LoE-based (high confidence)
    "ESC_A": "High", "ESC_B": "Moderate", "ESC_C": "Moderate",
    "GRADE_High": "High", "GRADE_Moderate": "High", "GRADE_Low": "High", "GRADE_Very Low": "High",
    "ESMO_I": "High", "ESMO_II": "High", "ESMO_III": "High", "ESMO_IV": "High", "ESMO_V": "High",
    "Oxford_1a": "High", "Oxford_1b": "High", "Oxford_2a": "High", "Oxford_2b": "High",
    "Oxford_3": "High", "Oxford_4": "High", "Oxford_5": "High",
    "GINA_A": "High", "GINA_B": "High", "GINA_C": "Moderate", "GINA_D": "High",
    "SIGN_A": "High", "SIGN_B": "High", "SIGN_C": "Moderate", "SIGN_GPP": "Moderate",
    # AHA/ACC LOE (high confidence -- well-defined tiers)
    "AHA_A": "High", "AHA_B-R": "High", "AHA_B-NR": "Moderate", "AHA_C-LD": "Moderate", "AHA_C-EO": "Moderate",
    # ASCO evidence quality
    "ASCO_High": "High", "ASCO_Intermediate": "High", "ASCO_Moderate": "High", "ASCO_Low": "High",
    # Strength-based (low confidence -- proxy mapping)
    "EAU_Strong": "Low", "EAU_Weak": "Low",
    "AAOS_Strong": "Low", "AAOS_Moderate": "Moderate", "AAOS_Limited": "Moderate",
    "AAOS_Consensus": "Moderate",
}

# Fanaroff 2019 benchmarks (JAMA, PMID 30874755)
FANAROFF = {
    "ESC": {
        "n_guidelines": 25,
        "n_recommendations": 3399,
        "pct_A": 14.2,
        "pct_B": 31.0,
        "pct_C": 54.8,
    },
    "ACC_AHA": {
        "n_guidelines": 26,
        "n_recommendations": 2930,
        "pct_A": 8.5,
        "pct_B": 50.0,
        "pct_C": 41.5,
    },
}


def load_data():
    return json.loads(ATLAS.read_text())


def primary_recs(db, loe_only=True, min_year=None):
    """Get primary recs, optionally filtering to LoE-only societies and min year."""
    primary_gl_ids = {g["id"] for g in db["guidelines"] if g.get("in_primary_analysis")}
    recs = []
    for r in db["recommendations"]:
        if r.get("loe_normalized") is None:
            continue
        if r["guideline_id"] not in primary_gl_ids:
            continue
        if loe_only and r["society"] in STRENGTH_SOCIETIES:
            continue
        if min_year and r["year"] < min_year:
            continue
        recs.append(r)
    return recs


def specialty_analysis(recs, min_n=MIN_RECS_PER_SPECIALTY, min_gl=MIN_GUIDELINES_PER_SPECIALTY):
    """Compute per-specialty evidence gap statistics."""
    by_spec = {}
    for r in recs:
        spec = r["specialty"]
        if spec not in by_spec:
            by_spec[spec] = []
        by_spec[spec].append(r)

    results = []
    for spec, spec_recs in sorted(by_spec.items()):
        norms = [r["loe_normalized"] for r in spec_recs]
        n_gl = len(set(r["guideline_id"] for r in spec_recs))
        if len(norms) < min_n or n_gl < min_gl:
            continue
        mean_loe = statistics.mean(norms)
        median_loe = statistics.median(norms)
        sd = statistics.stdev(norms) if len(norms) > 1 else 0
        iqr_low = statistics.quantiles(norms, n=4)[0] if len(norms) >= 4 else norms[0]
        iqr_high = statistics.quantiles(norms, n=4)[2] if len(norms) >= 4 else norms[-1]
        pct_a = sum(1 for n in norms if n >= 0.9) / len(norms) * 100
        pct_de = sum(1 for n in norms if n <= 0.25) / len(norms) * 100
        societies = sorted(set(r["society"] for r in spec_recs))
        n_gl = len(set(r["guideline_id"] for r in spec_recs))

        results.append({
            "specialty": spec,
            "n_recommendations": len(norms),
            "n_guidelines": n_gl,
            "societies": societies,
            "mean_loe": round(mean_loe, 3),
            "median_loe": round(median_loe, 3),
            "sd_loe": round(sd, 3),
            "iqr_low": round(iqr_low, 3),
            "iqr_high": round(iqr_high, 3),
            "evidence_gap": round(1 - mean_loe, 3),
            "pct_level_a": round(pct_a, 1),
            "pct_level_de": round(pct_de, 1),
        })
    return sorted(results, key=lambda x: x["evidence_gap"], reverse=True)


def weighted_specialty_analysis(recs, min_n=MIN_RECS_PER_SPECIALTY, min_gl=MIN_GUIDELINES_PER_SPECIALTY):
    """Each specialty contributes equally regardless of n."""
    spec_results = specialty_analysis(recs, min_n, min_gl)
    if not spec_results:
        return None
    gaps = [s["evidence_gap"] for s in spec_results]
    return {
        "n_specialties": len(spec_results),
        "weighted_mean_gap": round(statistics.mean(gaps), 3),
        "weighted_median_gap": round(statistics.median(gaps), 3),
        "weighted_sd_gap": round(statistics.stdev(gaps), 3) if len(gaps) > 1 else 0,
        "range": [round(min(gaps), 3), round(max(gaps), 3)],
    }


def sensitivity_analysis(recs):
    """Shift all normalizations +/- 1 tier and report impact."""
    base_gaps = specialty_analysis(recs)
    base_ranking = [s["specialty"] for s in base_gaps]

    shifts = {"base": base_gaps}
    for direction, delta in [("up_1_tier", 0.25), ("down_1_tier", -0.25)]:
        shifted_recs = []
        for r in recs:
            r2 = dict(r)
            n = r["loe_normalized"]
            r2["loe_normalized"] = max(0.125, min(1.0, n + delta))
            r2["evidence_gap"] = round(1.0 - r2["loe_normalized"], 3)
            shifted_recs.append(r2)
        shifted_gaps = specialty_analysis(shifted_recs)
        shifted_ranking = [s["specialty"] for s in shifted_gaps]

        # Spearman rank correlation (simplified)
        n_specs = min(len(base_ranking), len(shifted_ranking))
        common = [s for s in base_ranking if s in shifted_ranking]
        rank_changes = []
        for s in common:
            base_rank = base_ranking.index(s)
            shift_rank = shifted_ranking.index(s)
            rank_changes.append(abs(base_rank - shift_rank))
        max_change = max(rank_changes) if rank_changes else 0
        mean_change = statistics.mean(rank_changes) if rank_changes else 0

        shifts[direction] = {
            "specialty_gaps": shifted_gaps,
            "ranking": shifted_ranking,
            "max_rank_change": max_change,
            "mean_rank_change": round(mean_change, 2),
            "ranking_preserved": shifted_ranking == base_ranking[:len(shifted_ranking)],
        }

    return shifts


def fanaroff_benchmark(db):
    """Compare our ESC results to Fanaroff 2019."""
    primary_gl_ids = {g["id"] for g in db["guidelines"] if g.get("in_primary_analysis")}
    esc_recs = [r for r in db["recommendations"]
                if r["society"] == "ESC" and r.get("loe_normalized") is not None
                and r["guideline_id"] in primary_gl_ids]

    if not esc_recs:
        return None

    esc_loe = [r["loe"] for r in esc_recs]
    our_pct_a = sum(1 for l in esc_loe if l == "A") / len(esc_loe) * 100
    our_pct_b = sum(1 for l in esc_loe if l == "B") / len(esc_loe) * 100
    our_pct_c = sum(1 for l in esc_loe if l == "C") / len(esc_loe) * 100

    f = FANAROFF["ESC"]
    return {
        "our_study": {
            "n_guidelines": len(set(r["guideline_id"] for r in esc_recs)),
            "n_recommendations": len(esc_recs),
            "pct_A": round(our_pct_a, 1),
            "pct_B": round(our_pct_b, 1),
            "pct_C": round(our_pct_c, 1),
        },
        "fanaroff_2019": f,
        "interpretation": (
            f"Our ESC sample ({len(esc_recs)} recs from "
            f"{len(set(r['guideline_id'] for r in esc_recs))} guidelines) shows "
            f"{our_pct_a:.1f}% Level A vs Fanaroff's {f['pct_A']}% across {f['n_recommendations']} recs. "
            f"Distribution is {'consistent' if abs(our_pct_a - f['pct_A']) < 10 else 'divergent'} "
            f"with published benchmarks."
        ),
    }


def generate_validation_sample(db, sample_pct=5, seed=20260613):
    """Generate stratified random sample for manual validation (5% LoE accuracy)."""
    random.seed(seed)
    primary_gl_ids = {g["id"] for g in db["guidelines"] if g.get("in_primary_analysis")}
    all_recs = [r for r in db["recommendations"]
                if r.get("loe_normalized") is not None and r["guideline_id"] in primary_gl_ids]

    # Stratified by society
    by_society = {}
    for r in all_recs:
        s = r["society"]
        if s not in by_society:
            by_society[s] = []
        by_society[s].append(r)

    sample = []
    for soc, soc_recs in by_society.items():
        n_sample = max(3, round(len(soc_recs) * sample_pct / 100))
        n_sample = min(n_sample, len(soc_recs))
        chosen = random.sample(soc_recs, n_sample)
        for r in chosen:
            sample.append({
                "society": r["society"],
                "guideline_id": r["guideline_id"],
                "text": r["text"][:200],
                "extracted_cor": r["cor"],
                "extracted_loe": r["loe"],
                "extracted_normalized": r["loe_normalized"],
                "validator_is_recommendation": "",  # To be filled
                "validator_cor_correct": "",
                "validator_loe_correct": "",
                "validator_notes": "",
            })

    return sample


def temporal_analysis(db):
    """Compare recent (2021-2026) vs older guidelines."""
    recs_all = primary_recs(db, loe_only=True)
    recs_recent = [r for r in recs_all if r["year"] >= 2021]
    recs_older = [r for r in recs_all if r["year"] < 2021]

    result = {}
    for label, subset in [("all", recs_all), ("recent_2021_2026", recs_recent), ("older_pre_2021", recs_older)]:
        if not subset:
            continue
        norms = [r["loe_normalized"] for r in subset]
        result[label] = {
            "n": len(norms),
            "mean_loe": round(statistics.mean(norms), 3),
            "evidence_gap": round(1 - statistics.mean(norms), 3),
            "pct_level_a": round(sum(1 for n in norms if n >= 0.9) / len(norms) * 100, 1),
            "year_range": f"{min(r['year'] for r in subset)}-{max(r['year'] for r in subset)}",
        }
    return result


def coverage_analysis(db):
    """Quantify what we captured vs what exists.

    Identification proceeded in two waves:
      Wave 1 (original): PubMed [Practice Guideline] filter + ECRI/GIN repositories
        -> 959 guideline records, 52 societies, 27 specialties identified.
      Wave 2 (society-coverage expansion, 2026-06): a structured society-universe
        audit across all specialties identified ~33 additional eligible societies
        (per-recommendation graded, open access, English) that the wave-1 search
        had missed because they publish guidance in their own journals. Targeted
        retrieval added the expansion guidelines (society-targeted search yield
        ~117 candidate guidelines screened).
    Denominators below reflect the COMBINED identified universe across both waves.
    Coverage percentages are approximate (the identified universe is itself a
    moving target); the central evidence-quality findings do not depend on them.
    """
    n_soc = len(set(g["society"] for g in db["guidelines"]))
    n_spec = len(set(g["specialty"] for g in db["guidelines"]))
    n_gl = len(db["guidelines"])
    # Combined identified universe (wave1 + wave2 society-coverage audit)
    societies_identified = 84   # wave1 52 + ~32 net-new eligible (society-coverage audit)
    specialties_identified = max(36, n_spec)
    total_identified = 959 + 117  # wave1 records + wave2 society-targeted candidates
    return {
        "societies_identified": societies_identified,
        "societies_included": n_soc,
        "pct_societies": round(n_soc / societies_identified * 100, 1),
        "specialties_identified": specialties_identified,
        "specialties_included": n_spec,
        "pct_specialties": round(n_spec / specialties_identified * 100, 1),
        "total_guidelines_identified": total_identified,
        "guidelines_extracted": n_gl,
        "pct_guidelines": round(n_gl / total_identified * 100, 1),
        "societies_blocked": [
            {"society": "AHA/ACC", "specialty": "Cardiology", "reason": "Wolters Kluwer paywall"},
            {"society": "ASCO", "specialty": "Oncology", "reason": "Elsevier paywall"},
            {"society": "ASH", "specialty": "Hematology", "reason": "Silverchair (abstract-only in PMC)"},
            {"society": "AAN", "specialty": "Neurology", "reason": "Sage paywall"},
            {"society": "ACOG (most)", "specialty": "Obstetrics & Gynaecology", "reason": "LWW paywall"},
            {"society": "Endocrine Society", "specialty": "Endocrinology", "reason": "OUP paywall"},
            {"society": "IDSA (most)", "specialty": "Infectious Disease", "reason": "OUP paywall"},
            {"society": "AAO", "specialty": "Ophthalmology", "reason": "Login required"},
            {"society": "ADA", "specialty": "Endocrinology/Diabetes", "reason": "Playwright content block"},
            # Wave-2 identified but NOT obtained:
            {"society": "CCS", "specialty": "Cardiology", "reason": "Paywalled (identified, not obtained)"},
            {"society": "CHEST/ACCP", "specialty": "Pulmonology", "reason": "Paywalled (identified, not obtained)"},
            {"society": "ESH", "specialty": "Cardiology", "reason": "Paywalled (identified, not obtained)"},
            {"society": "NHG", "specialty": "Family Medicine", "reason": "Excluded: non-English (Dutch)"},
            {"society": "DEGAM", "specialty": "Family Medicine", "reason": "Excluded: non-English (German)"},
        ],
    }


def run_all():
    db = load_data()

    print("=" * 70)
    print("EVIDENCE GAP ATLAS -- COMPREHENSIVE ANALYSIS")
    print("=" * 70)

    # 1. Primary analysis (LoE-only, no strength-based)
    print("\n1. PRIMARY ANALYSIS (LoE-only societies, >= 5 GL per specialty)")
    recs_loe = primary_recs(db, loe_only=True)
    print(f"   Recs: {len(recs_loe)} from {len(set(r['society'] for r in recs_loe))} societies")
    spec_primary = specialty_analysis(recs_loe)
    weighted_primary = weighted_specialty_analysis(recs_loe)
    print(f"   Specialties (>= 5 GL): {len(spec_primary)}")
    for s in spec_primary:
        print(f"     {s['specialty']:<25s} n={s['n_recommendations']:>5d}  gap={s['evidence_gap']:.3f}  %A={s['pct_level_a']:5.1f}%  median={s['median_loe']:.3f}")
    if weighted_primary:
        print(f"   Weighted mean gap: {weighted_primary['weighted_mean_gap']:.3f} (SD {weighted_primary['weighted_sd_gap']:.3f})")

    # 2. Extended analysis (including EAU/AAOS)
    print("\n2. EXTENDED ANALYSIS (all societies, strength-as-proxy)")
    recs_all = primary_recs(db, loe_only=False)
    print(f"   Recs: {len(recs_all)} from {len(set(r['society'] for r in recs_all))} societies")
    spec_extended = specialty_analysis(recs_all)
    weighted_extended = weighted_specialty_analysis(recs_all)
    for s in spec_extended:
        marker = " *" if any(soc in STRENGTH_SOCIETIES for soc in s["societies"]) else ""
        print(f"     {s['specialty']:<25s} n={s['n_recommendations']:>5d}  gap={s['evidence_gap']:.3f}  %A={s['pct_level_a']:5.1f}%{marker}")
    if weighted_extended:
        print(f"   Weighted mean gap: {weighted_extended['weighted_mean_gap']:.3f}")
    print("   * = includes strength-based society (proxy mapping, lower confidence)")

    # 3. Sensitivity analysis
    print("\n3. SENSITIVITY ANALYSIS (normalization +/- 1 tier)")
    sens = sensitivity_analysis(recs_loe)
    for direction in ["up_1_tier", "down_1_tier"]:
        s = sens[direction]
        print(f"   {direction}: max rank change = {s['max_rank_change']}, mean = {s['mean_rank_change']:.1f}, ranking preserved = {s['ranking_preserved']}")

    # 4. Fanaroff benchmark
    print("\n4. FANAROFF 2019 BENCHMARK")
    bench = fanaroff_benchmark(db)
    if bench:
        print(f"   {bench['interpretation']}")

    # 5. Temporal analysis
    print("\n5. TEMPORAL ANALYSIS")
    temporal = temporal_analysis(db)
    for label, t in temporal.items():
        print(f"   {label}: n={t['n']}, gap={t['evidence_gap']:.3f}, %A={t['pct_level_a']:.1f}%, years={t['year_range']}")

    # 6. Coverage
    print("\n6. COVERAGE ANALYSIS")
    cov = coverage_analysis(db)
    print(f"   Societies: {cov['societies_included']}/{cov['societies_identified']} ({cov['pct_societies']:.1f}%)")
    print(f"   Specialties: {cov['specialties_included']}/{cov['specialties_identified']} ({cov['pct_specialties']:.1f}%)")
    print(f"   Guidelines: {cov['guidelines_extracted']}/{cov['total_guidelines_identified']} ({cov['pct_guidelines']:.1f}%)")

    # 7. Validation sample
    print("\n7. VALIDATION SAMPLE")
    sample = generate_validation_sample(db)
    print(f"   Generated {len(sample)} recs for manual validation (5% stratified)")

    # Save validation CSV
    val_path = OUT_DIR / "validation_sample.csv"
    if sample:
        fields = list(sample[0].keys())
        with open(val_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(sample)
        print(f"   Saved: {val_path}")

    # 8. Save comprehensive results JSON
    # Restrict headline counts to the specialties that actually pass the
    # >= 5 GL filter (i.e. those shown in specialty_gaps), so n_recs / n_societies
    # match the per-specialty table and the manuscript denominator.
    primary_specs = {s["specialty"] for s in spec_primary}
    recs_loe_primary = [r for r in recs_loe if r["specialty"] in primary_specs]
    extended_specs = {s["specialty"] for s in spec_extended}
    recs_all_primary = [r for r in recs_all if r["specialty"] in extended_specs]
    results = {
        "primary_analysis": {
            "description": "LoE-only societies, no strength-based proxies, >= 5 GL per specialty",
            "n_recs": len(recs_loe_primary),
            "n_societies": len(set(r["society"] for r in recs_loe_primary)),
            "specialty_gaps": spec_primary,
            "weighted": weighted_primary,
        },
        "extended_analysis": {
            "description": "All societies including EAU/AAOS strength-as-proxy",
            "n_recs": len(recs_all_primary),
            "n_societies": len(set(r["society"] for r in recs_all_primary)),
            "specialty_gaps": spec_extended,
            "weighted": weighted_extended,
        },
        "sensitivity": {
            "up_1_tier": {k: v for k, v in sens["up_1_tier"].items() if k != "specialty_gaps"},
            "down_1_tier": {k: v for k, v in sens["down_1_tier"].items() if k != "specialty_gaps"},
        },
        "fanaroff_benchmark": bench,
        "temporal": temporal,
        "coverage": cov,
        "normalization_confidence": NORM_CONFIDENCE,
        "validation_sample_n": len(sample),
    }

    results_path = OUT_DIR / "comprehensive_analysis.json"
    results_path.write_text(json.dumps(results, indent=2))
    print(f"\n   Saved: {results_path}")


if __name__ == "__main__":
    run_all()
