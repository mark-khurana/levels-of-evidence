"""
Extract recommendations from unstructured guideline text using Claude API.
This handles guidelines that don't have clean HTML tables (PDFs, journal articles).
"""

import json
import os
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Install anthropic: pip install anthropic")
    exit(1)


EXTRACTION_PROMPT = """You are a medical guideline data extraction system. Your task is to extract ALL clinical recommendations from the following guideline text, along with their evidence classifications.

For EACH recommendation, extract:
1. **recommendation_text**: The exact recommendation statement
2. **class_of_recommendation**: The recommendation class/strength (e.g., Class I, IIa, IIb, III for ESC/AHA; Strong/Conditional for GRADE; Grade A/B/C for USPSTF)
3. **level_of_evidence**: The evidence level (e.g., A, B, C for ESC; A, B-R, B-NR, C-LD, C-EO for AHA/ACC; High/Moderate/Low/Very Low for GRADE)
4. **condition**: The disease or clinical condition being addressed
5. **intervention**: The intervention or action being recommended
6. **population**: The target population (if specified)

Output your results as a JSON array. Each element should be:
```json
{
  "recommendation_text": "...",
  "class_of_recommendation": "...",
  "level_of_evidence": "...",
  "condition": "...",
  "intervention": "...",
  "population": "..."
}
```

IMPORTANT:
- Extract EVERY recommendation, not just a sample
- Use the EXACT evidence classifications as stated in the guideline
- If a recommendation table has rows, each row is typically one recommendation
- If evidence level or class is not explicitly stated, use "Not stated"
- Do not invent or infer evidence levels — only extract what is explicitly written

GUIDELINE TEXT:
"""


def extract_recommendations_from_text(
    guideline_text: str,
    guideline_title: str,
    grading_system: str,
    source: str = "Unknown",
    api_key: str | None = None,
) -> list[dict]:
    """
    Use Claude to extract structured recommendations from guideline text.

    Args:
        guideline_text: The raw text of the guideline
        guideline_title: Title of the guideline
        grading_system: Which grading system the guideline uses
        source: Source organization (e.g., "ESC", "AHA/ACC")
        api_key: Anthropic API key (or reads ANTHROPIC_API_KEY env var)
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter"
        )

    client = anthropic.Anthropic(api_key=key)

    # Truncate if very long (Claude has limits)
    max_chars = 180_000  # Leave room for prompt + response
    if len(guideline_text) > max_chars:
        print(f"Warning: Truncating text from {len(guideline_text)} to {max_chars} chars")
        guideline_text = guideline_text[:max_chars]

    full_prompt = (
        EXTRACTION_PROMPT
        + f"\n\nGuideline: {guideline_title}\n"
        + f"Grading System: {grading_system}\n"
        + f"Source Organization: {source}\n\n"
        + guideline_text
    )

    print(f"Sending {len(full_prompt)} chars to Claude for extraction...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": full_prompt}],
    )

    response_text = response.content[0].text

    # Parse JSON from response
    # Try to find JSON array in the response
    import re
    json_match = re.search(r'\[[\s\S]*\]', response_text)
    if not json_match:
        print("Warning: Could not find JSON array in response")
        print("Response:", response_text[:500])
        return []

    try:
        extracted = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print("Response:", response_text[:500])
        return []

    # Enrich with metadata
    results = []
    for item in extracted:
        rec = {
            "source": source,
            "grading_system": grading_system,
            "guideline_title": guideline_title,
            "topic": item.get("condition", ""),
            "condition": item.get("condition", ""),
            "population": item.get("population", ""),
            "intervention": item.get("intervention", ""),
            "recommendation_text": item.get("recommendation_text", ""),
            "grade": item.get("class_of_recommendation", ""),
            "level_of_evidence": item.get("level_of_evidence", ""),
            "recommendation_strength": item.get("class_of_recommendation", ""),
        }
        results.append(rec)

    return results


def extract_from_pdf(pdf_path: str, guideline_title: str, grading_system: str,
                     source: str, api_key: str | None = None) -> list[dict]:
    """Extract recommendations from a PDF guideline using Claude's PDF support."""
    import base64

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("Set ANTHROPIC_API_KEY environment variable")

    client = anthropic.Anthropic(api_key=key)

    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    print(f"Sending PDF ({Path(pdf_path).stat().st_size / 1024:.0f} KB) to Claude...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        EXTRACTION_PROMPT
                        + f"\n\nGuideline: {guideline_title}\n"
                        + f"Grading System: {grading_system}\n"
                        + f"Source Organization: {source}\n"
                    ),
                },
            ],
        }],
    )

    response_text = response.content[0].text

    import re
    json_match = re.search(r'\[[\s\S]*\]', response_text)
    if not json_match:
        print("Warning: Could not find JSON array in response")
        return []

    try:
        extracted = json.loads(json_match.group())
    except json.JSONDecodeError:
        print("JSON parse error")
        return []

    results = []
    for item in extracted:
        rec = {
            "source": source,
            "grading_system": grading_system,
            "guideline_title": guideline_title,
            "topic": item.get("condition", ""),
            "condition": item.get("condition", ""),
            "population": item.get("population", ""),
            "intervention": item.get("intervention", ""),
            "recommendation_text": item.get("recommendation_text", ""),
            "grade": item.get("class_of_recommendation", ""),
            "level_of_evidence": item.get("level_of_evidence", ""),
            "recommendation_strength": item.get("class_of_recommendation", ""),
        }
        results.append(rec)

    return results


if __name__ == "__main__":
    # Demo: extract from a sample text
    sample_text = """
    Table of Recommendations for Management of Atrial Fibrillation

    Recommendation | Class | Level
    ---|---|---
    Oral anticoagulation is recommended in AF patients with CHA2DS2-VASc score ≥2 (men) or ≥3 (women) | I | A
    NOACs are recommended in preference to VKAs in NOAC-eligible patients | I | A
    Screening for AF by pulse palpation or ECG rhythm strip is recommended in patients ≥65 years | I | B
    Catheter ablation for PVI is recommended as first-line rhythm control in selected patients with paroxysmal AF | I | A
    Rate control with beta-blockers or non-dihydropyridine calcium channel blockers is recommended as first-line | I | B
    Assessment of stroke risk using CHA2DS2-VASc score is recommended | I | C
    Echocardiography is recommended in all AF patients | I | C
    Thyroid function testing is recommended at diagnosis | I | C
    Amiodarone should be considered for rhythm control when other drugs fail | IIa | B
    Catheter ablation should be considered after failure of one antiarrhythmic drug | IIa | A
    Dronedarone should be considered for maintenance of sinus rhythm | IIa | B
    Weight reduction is recommended in obese AF patients | I | B
    Regular physical exercise should be considered | IIa | C
    Anticoagulation may be considered in patients with CHA2DS2-VASc score of 1 (men) or 2 (women) | IIb | B
    Surgical ablation may be considered in patients undergoing cardiac surgery | IIb | B
    Flecainide or propafenone are not recommended in patients with structural heart disease | III | A
    """

    print("=== Demo: Extracting from sample ESC-style guideline text ===\n")

    # Without Claude API, we can parse this structured text directly
    import re
    lines = sample_text.strip().split("\n")
    recs = []
    for line in lines:
        # Match "text | Class | Level" pattern
        match = re.match(r'\s*(.+?)\s*\|\s*(I{1,3}[ab]?)\s*\|\s*([A-C])\s*$', line)
        if match:
            recs.append({
                "source": "ESC",
                "grading_system": "ESC",
                "guideline_title": "ESC AF Guidelines (Demo)",
                "recommendation_text": match.group(1).strip(),
                "grade": match.group(2),
                "level_of_evidence": match.group(3),
                "recommendation_strength": match.group(2),
                "condition": "Atrial Fibrillation",
                "population": "",
                "topic": "Atrial Fibrillation",
            })

    print(f"Extracted {len(recs)} recommendations from demo text\n")
    for r in recs:
        print(f"  COR: {r['grade']:4s}  LOE: {r['level_of_evidence']}  |  {r['recommendation_text'][:80]}")

    # Save demo output
    output_path = Path(__file__).parent.parent / "data" / "raw" / "esc_af_demo.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(recs, f, indent=2)
    print(f"\nSaved to {output_path}")
