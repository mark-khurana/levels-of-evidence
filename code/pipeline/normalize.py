"""
Normalize extracted recommendations to a common evidence scale.
Maps raw evidence levels from various grading systems to a 1-5 normalized score.
"""

import json
import csv
from pathlib import Path
from config import EVIDENCE_NORMALIZATION, RECOMMENDATION_NORMALIZATION, EXTRACTED_DIR


def normalize_evidence(grading_system: str, raw_level: str) -> dict:
    """
    Normalize a raw evidence level to the 1-5 scale.
    Returns dict with normalized_score, evidence_gap, and metadata.
    """
    system_map = EVIDENCE_NORMALIZATION.get(grading_system, {})
    normalized = system_map.get(raw_level)

    if normalized is None:
        # Try case-insensitive match
        for key, val in system_map.items():
            if key.lower() == raw_level.lower():
                normalized = val
                break

    if normalized is None:
        return {
            "normalized_evidence_score": None,
            "evidence_gap": None,
            "normalization_status": "UNMAPPED",
            "raw_level": raw_level,
            "grading_system": grading_system,
        }

    evidence_gap = (5 - normalized) / 4  # Range 0.0 (fully evidenced) to 1.0

    return {
        "normalized_evidence_score": normalized,
        "evidence_gap": round(evidence_gap, 3),
        "normalization_status": "OK",
        "raw_level": raw_level,
        "grading_system": grading_system,
    }


def normalize_recommendation_strength(grading_system: str, raw_strength: str) -> dict:
    """Normalize recommendation strength to 0-4 scale."""
    system_map = RECOMMENDATION_NORMALIZATION.get(grading_system, {})
    normalized = system_map.get(raw_strength)

    if normalized is None:
        for key, val in system_map.items():
            if key.lower() == raw_strength.lower():
                normalized = val
                break

    return {
        "normalized_strength": normalized,
        "raw_strength": raw_strength,
        "grading_system": grading_system,
    }


def normalize_recommendations(recommendations: list[dict]) -> list[dict]:
    """
    Take a list of raw recommendation dicts and add normalized scores.
    """
    normalized = []
    for rec in recommendations:
        system = rec.get("grading_system", "")
        raw_loe = rec.get("level_of_evidence", "")
        raw_strength = rec.get("recommendation_strength", "")

        ev = normalize_evidence(system, raw_loe)
        strength = normalize_recommendation_strength(system, raw_strength)

        rec_normalized = {**rec}
        rec_normalized["normalized_evidence_score"] = ev["normalized_evidence_score"]
        rec_normalized["evidence_gap"] = ev["evidence_gap"]
        rec_normalized["normalization_status"] = ev["normalization_status"]
        rec_normalized["normalized_strength"] = strength["normalized_strength"]

        normalized.append(rec_normalized)

    return normalized


def compute_summary_stats(normalized_recs: list[dict]) -> dict:
    """Compute summary statistics for a set of normalized recommendations."""
    scored = [r for r in normalized_recs if r["normalized_evidence_score"] is not None]
    if not scored:
        return {"count": 0}

    scores = [r["normalized_evidence_score"] for r in scored]
    gaps = [r["evidence_gap"] for r in scored]

    n = len(scores)
    mean_score = sum(scores) / n
    mean_gap = sum(gaps) / n

    # Distribution
    from collections import Counter
    score_dist = Counter(scores)

    # Percentage at each level
    pct_highest = score_dist.get(5, 0) / n * 100
    pct_lowest = score_dist.get(1, 0) / n * 100

    return {
        "count": n,
        "mean_evidence_score": round(mean_score, 2),
        "mean_evidence_gap": round(mean_gap, 3),
        "pct_highest_evidence": round(pct_highest, 1),
        "pct_lowest_evidence": round(pct_lowest, 1),
        "score_distribution": dict(sorted(score_dist.items())),
    }


def save_normalized(normalized_recs: list[dict], output_name: str):
    """Save normalized recommendations as both JSON and CSV."""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = EXTRACTED_DIR / f"{output_name}.json"
    with open(json_path, "w") as f:
        json.dump(normalized_recs, f, indent=2)

    # CSV
    csv_path = EXTRACTED_DIR / f"{output_name}.csv"
    if normalized_recs:
        keys = normalized_recs[0].keys()
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(normalized_recs)

    return json_path, csv_path


if __name__ == "__main__":
    # Load raw USPSTF data
    raw_path = Path(__file__).parent.parent / "data" / "raw" / "uspstf_recommendations.json"
    if not raw_path.exists():
        print("Run fetch_guidelines.py first")
        exit(1)

    with open(raw_path) as f:
        recs = json.load(f)

    print(f"Loaded {len(recs)} recommendations")

    # Normalize
    normalized = normalize_recommendations(recs)

    # Summary
    stats = compute_summary_stats(normalized)
    print(f"\n=== USPSTF Evidence Summary ===")
    print(f"Total recommendations: {stats['count']}")
    print(f"Mean evidence score: {stats['mean_evidence_score']}/5")
    print(f"Mean evidence gap: {stats['mean_evidence_gap']}")
    print(f"% highest evidence (score=5): {stats['pct_highest_evidence']}%")
    print(f"% lowest evidence (score=1): {stats['pct_lowest_evidence']}%")
    print(f"Score distribution: {stats['score_distribution']}")

    # Save
    json_path, csv_path = save_normalized(normalized, "uspstf_normalized")
    print(f"\nSaved to:\n  {json_path}\n  {csv_path}")
