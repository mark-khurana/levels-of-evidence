# Levels of Evidence Supporting Clinical Practice Guideline Recommendations Across Medical Specialties

Code, data, and an interactive atlas for a cross-specialty analysis of the level of
evidence (LoE) supporting clinical practice guideline recommendations.

**Interactive atlas:** https://mark-khurana.github.io/levels-of-evidence/

## Summary

We analyzed 22,693 recommendations across 522 guidelines and 21 medical specialties
(primary analysis) from 75 professional medical societies, mapping each society's
heterogeneous grading system onto a common 5-tier evidence scale (A–E). Only 12.0% of
recommendations were supported by the highest level of evidence (Level A), and the
majority rested on observational-level evidence or below.

## Repository structure

```
docs/                     Interactive atlas (GitHub Pages site)
  index.html, app.js, style.css
  evidence_atlas.json     Atlas data (recommendation text truncated; see note below)

data/
  recommendations_truncated.csv   All 22,877 extracted recommendations (truncated text)
                                   with society, specialty, guideline, year, source link,
                                   evidence level, grading system, normalized score, gap
  comprehensive_analysis.json     Aggregate results (tier proportions, per-specialty gaps,
                                   sensitivity, benchmarks)
  eTable1_included_guidelines.md  Included guidelines
  eTable2_included_societies.md   Included societies + access/extraction notes
  eTable3_normalization_crosswalk.md  Grading-system → 5-tier crosswalk
  eTable4_all_specialties.md      All specialties (incl. those below the primary threshold)

figures/                  Manuscript figures (Figure 1–3, eFigure 1–2; PNG + PDF)

code/
  pipeline/
    config.py             Evidence-level normalization crosswalk + paths
    consolidate.py        Build the consolidated evidence atlas from extracted guidelines
    normalize.py          Normalize heterogeneous LoE labels to the 5-tier scale
    analysis.py           Compute comprehensive_analysis.json (all reported statistics)
    figures.py            Generate Figure 2–3 and eFigure 2
    extract_with_llm.py   LLM-based recommendation extraction (Claude; reads ANTHROPIC_API_KEY)
  scripts/
    make_figure1_schematic.py  Figure 1 (study-design schematic)
    make_prisma.py             eFigure 1 (PRISMA 2020 flow diagram)
    regenerate_tables.py       Regenerate eTables
  confidence_intervals.R       Wilson 95% CIs for tier proportions and validation accuracy
```

## Data and copyright

Guideline full text is copyrighted by the issuing societies and is **not** redistributed
here. Accordingly:

- **No original guideline PDFs or full recommendation text are included.**
- Recommendation text in `recommendations_truncated.csv` and in the atlas is **truncated
  to 50 characters** — enough to identify a recommendation, not to reproduce it.
- Each recommendation links to its source guideline (DOI/URL) so the original can be
  consulted at the issuing society.

Normalized evidence levels, scores, and all aggregate statistics are released in full.

## Reproducing the analysis

The extraction → normalization → analysis → figures pipeline is in `code/`. Given the
consolidated atlas, the reported statistics and figures regenerate with:

```bash
python code/pipeline/analysis.py     # -> comprehensive_analysis.json
python code/pipeline/figures.py      # -> figures
Rscript code/confidence_intervals.R  # -> 95% confidence intervals
```

Python 3.12+ (matplotlib, numpy for figures); R for the confidence-interval script.

## Citation

If you use this work, please cite the accompanying article (citation to be added on
publication).

## License

[MIT](LICENSE) for code, data, and figures in this repository.
