#!/usr/bin/env python3
"""
Consolidate all extracted guideline JSONs into a single database.

Reads all data/guidelines/*.json files and produces:
  - data/evidence_atlas.json  (full database for the website)
  - data/evidence_atlas.csv   (flat CSV for analysis)

Usage:
  python consolidate.py              # Consolidate all
  python consolidate.py --stats      # Print statistics only
"""

from __future__ import annotations
import json
import csv
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"
GL_DIR = DATA_DIR / "guidelines"
OUT_JSON = DATA_DIR / "evidence_atlas.json"
OUT_CSV = DATA_DIR / "evidence_atlas.csv"

# Normalization: map all grading systems to N1-N5 (1.0 = highest evidence)
NORMALIZE = {
    # ESC / AHA/ACC: LOE
    "A": 1.0, "B-R": 0.75, "B": 0.5, "B-NR": 0.5, "C": 0.25, "C-LD": 0.25, "C-EO": 0.125,
    # GRADE quality
    "High": 1.0, "Moderate": 0.75, "Low": 0.5, "Very Low": 0.25,
    # ASCO evidence quality/type
    "Intermediate": 0.75, "Insufficient": 0.125,
    # ADA evidence grades
    "ADA_A": 1.0, "ADA_B": 0.75, "ADA_C": 0.5, "ADA_E": 0.125,
    # CANMAT evidence levels
    "Level 1": 1.0, "Level 2": 0.75, "Level 3": 0.5, "Level 4": 0.25,
    # ESMO LoE (Roman)
    "I": 1.0, "II": 0.75, "III": 0.5, "IV": 0.25, "V": 0.125,
    # ADA
    "High (multiple well-conducted RCTs)": 1.0,
    "Moderate (well-conducted cohort studies)": 0.75,
    "Low (poorly controlled or uncontrolled studies)": 0.5,
    "Expert consensus or clinical experience": 0.125,
    "Expert consensus": 0.125,
    "Expert opinion": 0.125,
    "X": 0.125,
    # Oxford CEBM levels (EAU, EULAR, etc.)
    "1a": 1.0, "1b": 1.0, "1A": 1.0, "1B": 1.0, "1": 1.0,
    "2a": 0.75, "2b": 0.75, "2A": 0.75, "2B": 0.75, "2": 0.75,
    "3": 0.5, "3a": 0.5, "3b": 0.5, "3A": 0.5, "3B": 0.5,
    "4": 0.25,
    "5": 0.125,
    # Oxford CEBM split-level ranges (e.g. EULAR "Level of evidence: 3/4")
    "1/2": 0.875, "2/3": 0.625, "3/4": 0.375, "4/5": 0.1875,
    # GRADE certainty ranges (e.g. AGA "Low to Moderate") and AAO-HNS aggregate grade ranges
    "Low to Moderate": 0.625, "Moderate to High": 0.875, "Very Low to Low": 0.375,
    "Very Low to Moderate": 0.5,
    "A/B": 0.875, "B/C": 0.625, "C/D": 0.375,
    # Compound Roman numeral ranges (AAD, some EULAR)
    "I": 1.0, "II": 0.75, "III": 0.5, "IV": 0.25, "V": 0.125,
    "I-II": 0.75, "II-III": 0.5, "I-III": 0.5, "III-IV": 0.25,
    # GINA Evidence levels (A-D)
    # A = RCTs, rich body of data; B = RCTs, limited data; C = non-randomized; D = panel consensus
    "GINA_A": 1.0, "GINA_B": 0.75, "GINA_C": 0.5, "GINA_D": 0.125,
    # GOLD Evidence levels (same as GINA)
    "GOLD_A": 1.0, "GOLD_B": 0.75, "GOLD_C": 0.5, "GOLD_D": 0.125,
    # ESPEN/SIGN grades
    "GPP": 0.125, "BM": 0.25, "0": 0.125,
    # EAU: Strong/Weak integrates evidence quality per EAU methodology
    # Strong = supported by high-quality evidence; Weak = lower quality or uncertain
    "EAU_Strong": 0.75, "EAU_Weak": 0.375,
    # EAN: Strong/Weak recommendation (GRADE-based, integrates evidence quality)
    "EAN_Strong": 0.75, "EAN_Weak": 0.375,
    # Case variant for "Very Low"
    "Very low": 0.25,
    # Generic strength-based (AUA, AAO-HNS)
    # NOT normalizable without separate LoE
    "Strong": None, "Weak": None,
    # AAOS: Strength IS evidence-based (Strong = High quality studies, etc.)
    # Unlike EAU/AUA where strength is just direction confidence
    "Limited": 0.5,
    "Consensus": 0.125, "Expert Opinion": 0.25, "Option": 0.5,
    "Inconclusive": None, "Clinical Principle": None,
    # AAOS "Moderate" already mapped above in GRADE quality section
    # Oxford CEBM "Level X" format
    "Level 1": 1.0, "Level 2": 0.75, "Level 3": 0.5, "Level 4": 0.25, "Level 5": 0.125,
    # ACEP
    "Level A": 1.0, "Level B": 0.5, "Level C": 0.25,
    # AAN
    "Level A": 1.0, "Level B": 0.75, "Level C": 0.5, "Level U": 0.25,
    # RCOG
    "Grade A": 1.0, "Grade B": 0.75, "Grade C": 0.5, "Grade D": 0.25, "Grade GPP": 0.125,
    # AACAP
    "Clinical Standard (high confidence)": 1.0,
    "Clinical Guideline (moderate confidence)": 0.75,
    "Option (acceptable but uncertain)": 0.5,
    "Not Endorsable (insufficient evidence)": 0.25,
    # ADA letter grades
    "Grade A": 1.0, "Grade B": 0.75, "Grade C": 0.5, "Grade E": 0.125,
    # ESMO GoR
    "Grade A": 1.0, "Grade B": 0.75, "Grade C": 0.5, "Grade D": 0.25, "Grade E": 0.125,
    # NICE (reference)
    "NICE": None,  # NICE has no per-rec LoE
    # CANMAT evidence levels (1-4)
    "Level 1": 1.0, "Level 2": 0.75, "Level 3": 0.5, "Level 4": 0.25,
    # CANMAT treatment lines (used as COR, not LoE)
    "First-line": None, "Second-line": None, "Third-line": None, "Not Recommended": None,
    # ACR Appropriateness Criteria (1-9 scale mapped to categories)
    "Appropriate (7-9)": 1.0, "May Be Appropriate (4-6)": 0.5, "Not Appropriate (1-3)": 0.125,
    "Usually Appropriate": 1.0, "May Be Appropriate": 0.5, "Usually Not Appropriate": 0.125,
    # RCOG grades (same as generic Grade A-D already mapped above)
    "Grade GPP": 0.125,
}


    # KDIGO/GRADE letter-grade systems: A=High(1.0), B=Moderate(0.75), C=Low(0.5), D=Very Low(0.25)
    # These differ from ESC where B=0.5, C=0.25
KDIGO_MAP = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}
SIGN_MAP = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "GPP": 0.125, "0": 0.125}
# WFSBP: A = full RCT evidence, B = limited positive RCT evidence, C = uncontrolled/observational,
# D = expert opinion, E = negative evidence. Maps to GRADE-like semantics.
WFSBP_MAP = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "E": 0.125}
# AAN evidence levels: A=established(1.0), B=probably(0.75), C=possibly(0.5), U=insufficient(0.25)
AAN_MAP = {"A": 1.0, "B": 0.75, "C": 0.5, "U": 0.25}
# AAO-HNS when using letter grades: A=high(1.0), B=moderate(0.75), C=low(0.5), D=expert(0.25)
AAOHNS_MAP = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}

# Systems where A/B/C/D follow GRADE semantics (not ESC semantics)
GRADE_LETTER_SYSTEMS = {"KDIGO", "SIGN", "GRADE_AACE", "GRADE_AGA", "GRADE_ESCMID", "GRADE_ESGE"}


import re as _re

# 2026-06 society expansion: agents preserved each society's verbatim grade
# vocabulary. This maps those families to the 0-1 evidence-gap scale, using the
# SAME tier anchors as the base dataset (High/A/Level1=1.0, Moderate/B=0.75,
# Low/C/Level3=0.5, Very low/D/Level4=0.25, expert/consensus/GPP=0.125). Where a
# guideline's summary recommendation table reported only STRENGTH of
# recommendation (BAD ↑↑/↑ arrows, BSAC/ESE/ESICM strong/conditional, ESE
# recommend/suggest), strength is mapped as an evidence proxy exactly as EAU/EAN
# are handled in the base pipeline (strong->0.75, weak/conditional->0.375).
_WORD_Q = [("very low", 0.25), ("very-low", 0.25), ("high", 1.0),
           ("moderate", 0.75), ("low", 0.5)]
_LETTER_Q = {"a": 1.0, "b": 0.75, "c": 0.5, "d": 0.25, "e": 0.125}
_ROMAN_Q = {"i": 1.0, "ii": 0.75, "iii": 0.5, "iv": 0.25, "v": 0.125}
_OXFORD_Q = {"1": 1.0, "2": 0.75, "3": 0.5, "4": 0.25, "5": 0.125}
_SIGN_Q = {"1++": 1.0, "1+": 1.0, "1-": 0.75, "1−": 0.75,
           "2++": 0.75, "2+": 0.5, "2-": 0.375, "2−": 0.375, "3": 0.5, "4": 0.25}


def _normalize_expansion(loe: str, cor: str = "", grading_system: str = "") -> float | None:
    if not loe:
        return None
    s = str(loe).strip()
    low = s.lower()

    # 1. Ungraded / good practice / consensus / expert / no-evidence -> tier E
    UNGRADED = ["not graded", "ungraded", "good practice", "good-practice",
                "good clinical practice",
                "gpp", "expert opinion", "expert consensus", "consensus recommendation",
                "consensus statement", "consensus-based", "consensus based",
                "informal consensus", "formal consensus",
                "best practice", "no recommendation", "insufficient evidence",
                "research only", "recommendation for research", "recommendations for research",
                "no new evidence", "no sufficient level", "not labelled",
                "level of agreement", "agreement", "strong consensus", "not stated",
                "evidence varies", "see evidence to decision", "quadas",
                "no evidence", "not assessed", "u cons",
                "no studies met eligibility", "no studies", "not applicable", "n/a",
                "see later evidence", "see evidence"]
    if any(k in low for k in UNGRADED):
        return 0.125
    # EASL / USPSTF level-of-evidence format "Grade II-2, B1" (level = I / II-1 / II-2 / II-3 / III)
    m = _re.search(r'\bii-([123])\b', low)
    if m:
        return {"1": 0.75, "2": 0.5, "3": 0.375}[m.group(1)]
    if _re.match(r'^grade\s+iii\b', low) or s.strip() in ("III", "Grade III"):
        return 0.125  # USPSTF level III = expert opinion
    if _re.match(r'^grade\s+i\b', low) or _re.search(r'\bgrade i,', low):
        return 1.0    # USPSTF level I = RCT
    if s.strip() == "II-IV":
        return 0.4    # Roman range II..IV (ESMO)
    # lowercase ASCO quality words
    if low.strip() == "insufficient":
        return 0.125
    if low.strip() == "intermediate":
        return 0.75
    if s == "S":            # BAP/Shekelle: consensus tier
        return 0.125
    # ILAE adaptation classes: A/B/C established->possible; U undetermined
    m = _re.match(r'^ilae\s*=\s*([abcu])\b', low)
    if m:
        return {"a": 1.0, "b": 0.75, "c": 0.5, "u": 0.25}[m.group(1)]
    if "*" in s and any(a in s for a in ["↑", "↓", "⇈"]):  # BAD asterisked = consensus
        return 0.125

    # 2. SIGN evidence levels (1++/1+/1-/2++/2+/2-)
    m = _re.match(r'^([12])(\+\+|\+|--|-|−|‐)$', s)
    if m:
        return _SIGN_Q.get(m.group(0))
    # ESPID combined leading-Roman+letter like IIA / IA / IIIB  -> use Roman
    m = _re.match(r'^(I{1,3}|IV|V)([A-D])$', s)
    if m:
        return _ROMAN_Q.get(m.group(1).lower())
    # ESGO/IDSA "V, B" / "III, A" -> leading Roman governs quality
    m = _re.match(r'^(I{1,3}|IV|V)\s*[,.]', s)
    if m:
        return _ROMAN_Q.get(m.group(1).lower())
    # "Level V" / "Level IV-V" (ESE Roman)
    m = _re.match(r'^level\s+(i{1,3}|iv|v)\b', low)
    if m:
        return _ROMAN_Q.get(m.group(1))

    # 3. Oxford "Level X[a/b]" / "LE:X" (numeric)
    m = _re.search(r'(?:^|\b)(?:level|le)\s*[:\s]?\s*([1-5])', low)
    if m:
        return _OXFORD_Q.get(m.group(1))

    # 4. GRADE strength+quality letter combos: 1A/2C/Grade 1A/GRADE 2C/1D...
    #    (number=strength, letter=quality). Use the LETTER as quality.
    m = _re.match(r'^(?:grade[s]?\s*)?[012]\s*([a-e])\b', low)
    if m:
        return _LETTER_Q.get(m.group(1))
    # 4b. Bare GRADE letter(s): "GRADE D", "GRADES C and D", "GRADES B-D" (ESPID)
    m = _re.match(r'^grade[s]?\s+([a-e])(?:\s*(?:and|[-–—to]+)\s*([a-e]))?', low)
    if m:
        v1 = _LETTER_Q.get(m.group(1))
        if m.group(2):
            v2 = _LETTER_Q.get(m.group(2))
            return round((v1 + v2) / 2, 4)
        return v1
    # 4c. Leading bare Oxford digit followed by non-letter: "2 (extrapolated/cohort)"
    m = _re.match(r'^([1-5])\s*[(\s]', s)
    if m:
        return _OXFORD_Q.get(m.group(1))
    # 4d. Multiple Oxford levels "2; 3" / "1; 5" -> average
    nums = _re.findall(r'\b([1-5])\b', s)
    if nums and _re.match(r'^[1-5][\s;,/]+[1-5]', s):
        vs = [_OXFORD_Q[n] for n in nums if n in _OXFORD_Q]
        if vs:
            return round(sum(vs) / len(vs), 4)

    # 5. GRADE circle/symbol notation: count filled vs empty (out of ~4)
    filled = sum(s.count(c) for c in "⊕⨁ØΘ●")  # Θ handled as filled? no -> see below
    # Θ alone is "no recommendation" (caught as ungraded only if labelled); treat as consensus
    if s.strip() in ("Θ", "⇈"):
        return 0.125 if s.strip() == "Θ" else 0.75
    filled = sum(s.count(c) for c in "⊕⨁Ø●") + (s.count('+') if _re.search(r'[+][O0o◯○]', s) or _re.search(r'[+]{2,}', s) else 0)
    empty = sum(s.count(c) for c in "◯○⊝⊘") + len(_re.findall(r'(?<![0-9])[O](?![a-zA-Z])', s)) + (s.count('0'))
    if filled and (empty or filled <= 4):
        n = min(filled, 4)
        return {1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}[n]

    # 6. Quality words (incl. composites/ranges) -> average all occurrences
    vals = []
    tmp = low
    for w, v in [("very low", 0.25)]:
        cnt = tmp.count(w)
        vals += [v] * cnt
        tmp = tmp.replace(w, "")
    for w, v in [("high", 1.0), ("moderate", 0.75), ("low", 0.5)]:
        cnt = tmp.count(w)
        vals += [v] * cnt
    if vals:
        return round(sum(vals) / len(vals), 4)

    # 6b. Composite / range AHA-LOE tokens (e.g. "B-NR/C-LD", "B-R/C-EO")
    aha_parts = _re.findall(r'\b(?:A|B-R|B-NR|C-LD|C-EO|B|C)\b', s)
    if "/" in s and len(aha_parts) >= 2 and all(p in NORMALIZE for p in aha_parts):
        vals = [NORMALIZE[p] for p in aha_parts if NORMALIZE.get(p) is not None]
        if vals:
            return round(sum(vals) / len(vals), 4)
    # 6c. Generic letter-grade composites/ranges ("B and C", "D/B", "0D", "0C", "D/C")
    LETMAP = {"a": 1.0, "b": 0.75, "c": 0.5, "d": 0.25, "e": 0.125}
    letters = [c for c in _re.findall(r'(?<![a-z])([a-e])(?![a-z])', low) if c in LETMAP]
    if letters and _re.search(r'[/ ]|and', low) and not _re.search(r'⊕|⨁|Ø|level|grade [12]', low):
        vals = [LETMAP[c] for c in letters]
        return round(sum(vals) / len(vals), 4)

    # 7. "limited evidence" is an evidence-quality descriptor (~low) -> keep.
    if "limited" in low and "evidence" in low:
        return 0.5
    # NOTE: pure strength-of-recommendation tokens (↑↑/↑/↓↓, recommend/suggest,
    # strong/weak/conditional recommendation) are NOT mapped. In GRADE and related
    # systems strength is a separate axis from evidence certainty and does not
    # define a level of evidence, so such recommendations are left unmapped
    # (excluded from the evidence-level analysis). Guidelines that grade ONLY by
    # strength were excluded entirely (data/expansion/excluded_strength_only.json).
    return None


def normalize_loe(loe: str, cor: str = "", grading_system: str = "") -> float | None:
    """Normalize any evidence level to 0-1 scale."""
    if not loe:
        # No evidence grade recorded. If the recommendation carries ONLY a
        # strength-of-recommendation label it is left unmapped (strength is not
        # an evidence level); otherwise it is an ungraded/good-practice
        # statement -> tier E.
        if str(cor).strip().lower() in ("strong", "weak", "conditional", "1", "2"):
            return None
        return 0.125

    # GPS / Good Practice Statements -> tier E consensus
    if loe in ("GPS", "Good Practice Statement", "Ungraded Good Practice Statement"):
        return 0.125

    # Ungraded / Not stated / Not graded -> tier E consensus
    if loe in ("Not stated", "Not Graded", "Ungraded", "Not applicable",
               "Knowledge gap", "Knowledge Gap",
               "Best practice statement", "Best Practice Statement", "Best Practice",
               "No data", "Research only", "Research Only",
               "Indirect evidence, not assessed with GRADE"):
        return 0.125

    # WFSBP subcategories: A-/B- (slightly weaker), C1/C2/C3
    if grading_system == "WFSBP":
        if loe == "A-":
            return 0.875  # between A(1.0) and B(0.75)
        if loe == "B-":
            return 0.625  # between B(0.75) and C(0.5)
        if loe.startswith("C") and len(loe) == 2 and loe[1].isdigit():
            return 0.5  # C subcategories = C

    # Compound GRADE quality levels
    if loe == "Moderate-to-high":
        return 0.875
    if loe == "Intermediate-Low":
        return 0.375
    # WFSBP: A/B/C/D/E evidence categories (different from ESC A/B/C)
    if grading_system == "WFSBP" and loe in WFSBP_MAP:
        return WFSBP_MAP[loe]
    # KDIGO: A/B/C/D = GRADE High/Moderate/Low/Very Low
    if grading_system == "KDIGO" and loe in KDIGO_MAP:
        return KDIGO_MAP[loe]
    # AAN evidence levels (A/B/C/U follow GRADE-like semantics, not ESC)
    if grading_system == "AAN" and loe in AAN_MAP:
        return AAN_MAP[loe]
    # AAO-HNS letter grades (A/B/C/D follow GRADE-like semantics, not ESC)
    if grading_system == "AAO-HNS" and loe in AAOHNS_MAP:
        return AAOHNS_MAP[loe]
    # GRADE with letter grades (A=High, B=Moderate, C=Low, D=Very Low)
    if grading_system == "GRADE" and loe in ("A", "B", "C", "D"):
        return KDIGO_MAP[loe]  # Same mapping as KDIGO: A=1.0, B=0.75, C=0.5, D=0.25
    # AAP evidence quality: A=well-designed RCTs, B=moderate quality, C=observational, D=expert
    if grading_system.startswith("AAP") and loe in ("A", "B", "C", "D"):
        return KDIGO_MAP[loe]
    # AASLD evidence quality: A=high, B=moderate, C=low (GRADE-based)
    if grading_system == "AASLD" and loe in ("A", "B", "C"):
        return KDIGO_MAP[loe]
    # ACOG levels: A=good/consistent, B=limited/inconsistent, C=consensus
    if grading_system == "ACOG" and loe in ("A", "B", "C"):
        return KDIGO_MAP[loe]
    # ESHRE evidence levels: A=meta-analysis, B=RCT, C=observational, D=expert
    if grading_system == "ESHRE" and loe in ("A", "B", "C", "D"):
        return KDIGO_MAP[loe]
    # SORT (AAFP): A=consistent good quality, B=inconsistent/limited, C=consensus
    if grading_system in ("SORT", "Letter-grade") and loe in ("A", "B", "C"):
        return KDIGO_MAP[loe]
    # SIGN grades (used by ESPEN, BSR, BTS)
    if grading_system in ("SIGN", "BSR") and loe in SIGN_MAP:
        return SIGN_MAP[loe]
    # Society-specific prefix for ambiguous single-letter grades
    if grading_system in ("GINA", "GOLD") and loe in "ABCD":
        key = f"{grading_system}_{loe}"
        if key in NORMALIZE:
            return NORMALIZE[key]
    # ADA: A/B/C/E evidence grades (handles both "ADA" and "ADA (A/B/C/E)" variants)
    if grading_system.startswith("ADA") and loe in "ABCE":
        key = f"ADA_{loe}"
        if key in NORMALIZE:
            return NORMALIZE[key]
    # EAU: Strong/Weak is evidence-informed per their methodology
    if grading_system == "EAU" and loe in ("Strong", "Weak"):
        return NORMALIZE.get(f"EAU_{loe}")
    # BSG AIH 2025 rec 41 labels its evidence grade "weak" (non-standard for this
    # GRADE-based guideline, whose scale is High/Moderate/Low/Very Low); the adjacent
    # relapse recommendations are all graded "Low", so normalize as low certainty.
    if grading_system == "BSG" and loe == "Weak":
        return 0.5
    # AAOS: strength IS evidence-based
    if grading_system == "AAOS":
        if loe == "Strong":
            return 1.0
        if loe == "Moderate":
            return 0.75
    # CANMAT: numeric levels 1-4
    if grading_system == "CANMAT" and loe in ("1", "2", "3", "4"):
        canmat_map = {"1": 1.0, "2": 0.75, "3": 0.5, "4": 0.25}
        return canmat_map[loe]
    # ACR Appropriateness Criteria
    if grading_system == "ACR_AC":
        acr_map = {
            "Appropriate (7-9)": 1.0, "May Be Appropriate (4-6)": 0.5,
            "Not Appropriate (1-3)": 0.125,
            "Usually Appropriate": 1.0, "May Be Appropriate": 0.5,
            "Usually Not Appropriate": 0.125,
        }
        if loe in acr_map:
            return acr_map[loe]
    # RCOG: Grade A-D + GPP (SIGN-based system)
    if grading_system == "RCOG":
        rcog_map = {"Grade A": 1.0, "Grade B": 0.75, "Grade C": 0.5, "Grade D": 0.25, "Grade GPP": 0.125,
                    "A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "GPP": 0.125,
                    "High": 1.0, "Moderate": 0.75, "Low": 0.5, "Very Low": 0.25}
        if loe in rcog_map:
            return rcog_map[loe]
    # AASLD Oxford CEBM levels (used for HCC 2023, Transplant 2025)
    if grading_system == "Oxford_CEBM" and loe in ("1", "1a", "1b", "2", "2a", "2b", "3", "4", "5"):
        return NORMALIZE.get(loe)
    # EASL LoE with Roman numerals (decompensated cirrhosis, nutrition)
    # Only apply EASL-specific mapping for compound Roman numerals (II-1, II-2, etc.)
    # Simple Roman numerals (I, II, III, IV, V) are handled by the main NORMALIZE map
    easl_roman_map = {"II-1": 0.75, "II-2": 0.5, "II-3": 0.375,
                      "Level I": 1.0, "Level II-1": 0.75, "Level II-2": 0.5, "Level II-3": 0.375, "Level III": 0.25, "Level IV": 0.125}
    if loe in easl_roman_map:
        return easl_roman_map[loe]
    # EASL/AASLD numeric LoE (1-5) used in newer EASL guidelines (MASLD 2024)
    if grading_system in ("EASL_GRADE", "GRADE_EASL") and loe in ("1", "2", "3", "4", "5"):
        return NORMALIZE.get(loe)
    # EASL nutrition: Grade codes like C1, C2, B1, B2 (letter = LoE grade, number = strength)
    # These are mapped via the LoE field which holds the Roman numeral
    # ESHRE/GRADE quality — GPP = no direct evidence = expert opinion tier
    if grading_system == "GRADE" and loe in ("GPP",):
        return 0.125
    # Direct match
    if loe in NORMALIZE:
        return NORMALIZE[loe]
    # Try with "Grade " prefix
    if f"Grade {loe}" in NORMALIZE:
        return NORMALIZE[f"Grade {loe}"]
    # Try with "Level " prefix
    if f"Level {loe}" in NORMALIZE:
        return NORMALIZE[f"Level {loe}"]
    # Try COR as evidence proxy (only for systems where COR encodes evidence)
    if grading_system in ("AAOS",) and cor in NORMALIZE:
        return NORMALIZE[cor]
    # 2026-06 expansion: society-specific verbatim grade vocabularies
    return _normalize_expansion(loe, cor, grading_system)


ALLOWED_SOCIETIES = {
    "AAAAI", "AACE", "AAD", "AAFP", "AAN", "AAO-HNS", "AAOS", "AAP",
    "AASLD", "ACG", "ACOG", "ACP", "ACR", "ADA", "AGA", "AGS",
    "AHA/ACC", "APA", "ASCO", "ASCO/IDSA", "ASH", "ATS",
    "BSG", "BSR", "BTS",
    "CANMAT",
    "EAACI", "EAN", "EASL", "EAST", "ERS", "ESC", "ESCMID", "ESGE",
    "ESHRE", "ESMO", "ESPEN", "EULAR", "Endocrine Society",
    "GINA", "GOLD",
    "IDSA", "ISTH", "Italian Society of Arterial Hypertension",
    "KDIGO",
    "RCOG",
    "SAGES", "SCCM", "SHEA",
    "WAO", "WFSBP",
    # --- 2026-06 society expansion ---
    "ASCRS", "ASRM", "ASTRO", "AES",
    "BAD", "BAP", "BHIVA", "BSAC", "BSH",
    "CSN",
    "EHA", "EPA", "ERA (ERBP)", "ERAS Society", "ESE", "ESGO", "ESICM", "ESO",
    "ESPGHAN/NASPGHAN", "ESPID", "ESTES", "ETA", "EuroGuiDerm (EDF/EADV)",
    "ILAE",
    "OTA",
    "SITC", "SMFM",
    "ATA", "WSES",
}


# Canonical specialty taxonomy — collapse fragmented / duplicate-spelling specialties
# (introduced by the 2026-06 society expansion) into the established buckets.
SPECIALTY_CANON = {
    "Haematology": "Hematology",
    "Critical Care": "Critical Care Medicine",
    "HIV Medicine": "Infectious Disease",
    "Pediatric Infectious Disease": "Infectious Disease",
    "Pediatric Gastroenterology": "Gastroenterology",
    "Maternal-Fetal Medicine": "Obstetrics & Gynaecology",
    "Surgery": "General Surgery",
    "Emergency Surgery": "General Surgery",
    "Colorectal Surgery": "General Surgery",
    "Trauma Surgery": "General Surgery",
    "Radiation Oncology": "Oncology",
    "Gynaecological Oncology": "Oncology",
}


def canon_specialty(s):
    return SPECIALTY_CANON.get(s, s)


def consolidate():
    """Read all guideline JSONs and produce consolidated database."""
    all_guidelines = []
    all_recs = []
    errors = []

    json_files = sorted(GL_DIR.glob("*.json"))
    print(f"Found {len(json_files)} guideline files")

    for f in json_files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"  JSON error in {f.name}: {e}")
            continue

        gl = data.get("guideline", {})
        recs = data.get("recommendations", [])

        # Canonicalize specialty taxonomy (collapse fragments/duplicate spellings)
        if gl.get("specialty"):
            gl["specialty"] = canon_specialty(gl["specialty"])

        # Validate society affiliation
        society = gl.get("society", "")
        if society not in ALLOWED_SOCIETIES:
            errors.append(f"  BLOCKED {f.name}: society '{society}' not in allowed list")
            continue

        # A guideline must contain more than one recommendation to be included;
        # single-recommendation documents are not treated as practice guidelines.
        if len(recs) <= 1:
            continue

        # Skip NICE from primary analysis (no per-rec LoE)
        if gl.get("society") == "NICE":
            gl["in_primary_analysis"] = False
        else:
            gl["in_primary_analysis"] = True

        # Count how many recs will be normalizable
        gs = gl.get("grading_system", "")
        n_normalizable = sum(1 for r in recs
            if normalize_loe(r.get("loe_oxford") or r.get("loe", ""), r.get("cor", ""), gs) is not None)
        # Exclude guidelines with fewer than 3 normalizable recs — not meaningful
        if n_normalizable < 3:
            gl["in_primary_analysis"] = False

        gl["rec_count"] = len(recs)
        gl["source_file"] = f.name
        all_guidelines.append(gl)

        society = gl.get("society", "")
        is_strength_based = society in ("EAU", "AAOS")
        # AHA/ACC has COR (strength) + LOE (evidence) — use LOE for normalization
        # ASCO has strength + quality — use quality for normalization

        for r in recs:
            # Normalize non-standard field names (e.g. some ESMO extractions)
            if "recommendation_text" in r and "text" not in r:
                r["text"] = r.pop("recommendation_text")
            if "evidence_level" in r and "loe" not in r:
                r["loe"] = r.pop("evidence_level")
            if "recommendation_grade" in r and "cor" not in r:
                r["cor"] = r.pop("recommendation_grade")
            # Try loe_oxford first (EAU), then loe, then quality (ASCO), then cor
            loe_val = r.get("loe_oxford") or r.get("loe", "") or r.get("quality", "")
            norm = normalize_loe(loe_val, r.get("cor", ""), gs)
            # For display, use the oxford LoE if available
            display_loe = r.get("loe_oxford") or r.get("loe", "")
            all_recs.append({
                "guideline_id": gl.get("id", ""),
                "society": society,
                "specialty": gl.get("specialty", ""),
                "year": gl.get("year", 0),
                "grading_system": gl.get("grading_system", ""),
                "text": r.get("text", ""),
                "cor": r.get("cor", ""),
                "loe": display_loe,
                "loe_normalized": norm,
                "evidence_gap": round(1.0 - norm, 3) if norm is not None else None,
                "strength_based": is_strength_based,
                "section": r.get("section", ""),
                "rec_number": r.get("rec_number", ""),
            })

    # Build summary statistics — only from guidelines that pass primary analysis filter
    primary_gl_ids = set(g.get("id") for g in all_guidelines if g.get("in_primary_analysis"))
    primary_recs = [r for r in all_recs
                    if r.get("loe_normalized") is not None and r["guideline_id"] in primary_gl_ids]
    primary_guidelines = [g for g in all_guidelines if g.get("in_primary_analysis")]

    by_society = Counter(r["society"] for r in primary_recs)
    by_specialty = Counter(r["specialty"] for r in primary_recs)

    # Specialty-level evidence gap
    specialty_gaps = {}
    for spec in by_specialty:
        spec_recs = [r for r in primary_recs if r["specialty"] == spec]
        norms = [r["loe_normalized"] for r in spec_recs if r["loe_normalized"] is not None]
        if norms:
            mean_loe = sum(norms) / len(norms)
            specialty_gaps[spec] = {
                "specialty": spec,
                "n_recommendations": len(spec_recs),
                "n_guidelines": len(set(r["guideline_id"] for r in spec_recs)),
                "societies": sorted(set(r["society"] for r in spec_recs)),
                "mean_loe_normalized": round(mean_loe, 3),
                "evidence_gap": round(1.0 - mean_loe, 3),
                "pct_highest_evidence": round(sum(1 for n in norms if n >= 0.9) / len(norms) * 100, 1),
            }

    output = {
        "meta": {
            "generated": "auto",
            "total_guidelines": len(all_guidelines),
            "primary_guidelines": len(primary_guidelines),
            "total_recommendations": len(all_recs),
            "primary_recommendations": len(primary_recs),
            "societies": len(by_society),
            "specialties": len(by_specialty),
        },
        "guidelines": all_guidelines,
        "recommendations": all_recs,
        "specialty_gaps": sorted(specialty_gaps.values(), key=lambda x: x["evidence_gap"], reverse=True),
        "by_society": dict(by_society.most_common()),
    }

    # Save JSON
    OUT_JSON.write_text(json.dumps(output, indent=2))
    print(f"Saved {OUT_JSON} ({len(all_recs)} recs, {len(all_guidelines)} guidelines)")

    # Save CSV
    if all_recs:
        fields = list(all_recs[0].keys())
        with open(OUT_CSV, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(all_recs)
        print(f"Saved {OUT_CSV}")

    if errors:
        print(f"\nErrors:")
        for e in errors:
            print(e)

    return output


def print_stats():
    """Print statistics from the consolidated database."""
    if not OUT_JSON.exists():
        print("No consolidated database found. Run without --stats first.")
        return

    data = json.loads(OUT_JSON.read_text())
    meta = data["meta"]

    print(f"\n{'='*60}")
    print(f"EVIDENCE GAP ATLAS — Database Statistics")
    print(f"{'='*60}")
    print(f"\n  Guidelines:       {meta['primary_guidelines']} (primary) / {meta['total_guidelines']} (total)")
    print(f"  Recommendations:  {meta['primary_recommendations']} (primary) / {meta['total_recommendations']} (total)")
    print(f"  Societies:        {meta['societies']}")
    print(f"  Specialties:      {meta['specialties']}")

    print(f"\n{'─'*60}")
    print(f"{'Society':<15} {'Recs':>6}")
    print(f"{'─'*60}")
    for soc, n in sorted(data["by_society"].items(), key=lambda x: -x[1]):
        print(f"  {soc:<13} {n:>6}")

    print(f"\n{'─'*60}")
    print(f"{'Specialty':<30} {'Recs':>6} {'Gap':>6} {'% High LoE':>10}")
    print(f"{'─'*60}")
    for sg in data["specialty_gaps"]:
        print(f"  {sg['specialty']:<28} {sg['n_recommendations']:>6} {sg['evidence_gap']:>6.3f} {sg['pct_highest_evidence']:>9.1f}%")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        consolidate()
        print_stats()
