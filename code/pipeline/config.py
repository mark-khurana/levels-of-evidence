"""Configuration for the guideline extraction pipeline."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"

# Python interpreter (mambaforge has the right packages)
PYTHON = "/Users/bxc331/mambaforge/bin/python3"

# Evidence normalization crosswalk (5-tier scale)
# Maps (grading_system, raw_level) -> normalized_score (1-5)
EVIDENCE_NORMALIZATION = {
    "USPSTF": {
        # USPSTF grades combine evidence + net benefit, so we map differently
        # Their "certainty" levels are: High, Moderate, Low
        # Their grades are: A, B, C, D, I
        "A": 5,   # High certainty, substantial benefit
        "B": 4,   # High certainty moderate benefit OR moderate certainty moderate-substantial
        "C": 3,   # Moderate certainty, small net benefit
        "D": 2,   # Moderate-high certainty, no benefit or harms > benefits
        "I": 1,   # Insufficient evidence
    },
    "AHA_ACC": {
        "A": 5,
        "B-R": 4,
        "B-NR": 3,
        "C-LD": 2,
        "C-EO": 1,
    },
    "ESC": {
        "A": 5,
        "B": 3,   # ESC B is broad (single RCT or large non-randomized)
        "C": 1,
    },
    "GRADE": {
        "High": 5,
        "Moderate": 4,
        "Low": 2,
        "Very Low": 1,
    },
    "KDIGO": {  # Uses GRADE
        "A": 5,
        "B": 4,
        "C": 2,
        "D": 1,
    },
    "NCCN": {
        "1": 5,
        "2A": 3,
        "2B": 2,
        "3": 1,
    },
    "OCEBM": {
        "1": 5,
        "2": 4,
        "3": 3,
        "4": 2,
        "5": 1,
    },
}

# Recommendation strength normalization (0-4 scale)
RECOMMENDATION_NORMALIZATION = {
    "USPSTF": {
        "A": 4,  # Strongly recommend
        "B": 3,  # Recommend
        "C": 2,  # Selectively offer
        "D": 1,  # Recommend against
        "I": 0,  # Insufficient
    },
    "AHA_ACC": {
        "I": 4,
        "IIa": 3,
        "IIb": 2,
        "III": 1,
    },
    "ESC": {
        "I": 4,
        "IIa": 3,
        "IIb": 2,
        "III": 1,
    },
}
