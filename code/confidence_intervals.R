# =====================================================================
# 95% Confidence Intervals for "Levels of Evidence Supporting Clinical
# Practice Guideline Recommendations Across Medical Specialties"
#
# Self-contained: all counts are hard-coded from the primary analysis
# (22,693 recommendations / 522 guidelines / 75 societies / 21 specialties).
# No working directory or external files needed.
#
# Run:  Rscript ~/Desktop/evidence_gap_CIs.R
#   or open in RStudio and Source.
#
# Uses Wilson score CIs for proportions (good for small and large n,
# stays within 0-100%). Base R only - no packages required.
# =====================================================================

## ---- Wilson score interval for a single proportion ----
wilson <- function(x, n, conf = 0.95) {
  z  <- qnorm(1 - (1 - conf) / 2)
  p  <- x / n
  den <- 1 + z^2 / n
  ctr <- (p + z^2 / (2 * n)) / den
  hw  <- (z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2))) / den
  c(pct = 100 * p, lo = 100 * (ctr - hw), hi = 100 * (ctr + hw))
}

fmt <- function(w) sprintf("%.1f%% (95%% CI, %.1f%%-%.1f%%)", w["pct"], w["lo"], w["hi"])

cat("=====================================================================\n")
cat(" OVERALL EVIDENCE-TIER PROPORTIONS  (n = 22,693 recommendations)\n")
cat("=====================================================================\n")

N <- 22693
tiers <- c(A = 2727, B = 4361, C = 6821, D = 5662, E = 3122)
for (t in names(tiers)) {
  cat(sprintf("  Level %s : %s\n", t, fmt(wilson(tiers[[t]], N))))
}

cat("\n  Pooled tiers:\n")
cat(sprintf("  C-E (15,605): %s\n", fmt(wilson(15605, N))))   # observational or below
cat(sprintf("  D-E ( 8,784): %s\n", fmt(wilson(8784,  N))))   # case series / expert opinion

## ---- Secondary analysis: A-D only (Level E excluded) ----
cat("\n  Secondary analysis, Level E excluded (n = 19,571):\n")
N2 <- 19571
cat(sprintf("  Level A : %s\n", fmt(wilson(2727, N2))))       # rises to ~13.9%
cat(sprintf("  Level D : %s\n", fmt(wilson(5662, N2))))       # lowest tier retained
cat(sprintf("  C-D (12,483): %s\n", fmt(wilson(6821 + 5662, N2))))

cat("\n=====================================================================\n")
cat(" PER-SPECIALTY  % LEVEL A  (ordered by evidence gap, largest first)\n")
cat("=====================================================================\n")

# specialty, n recommendations, n Level A, n Level D-E  (from primary analysis)
spec <- data.frame(
  specialty = c("Obstetrics & Gynaecology","Reproductive Medicine","Hematology",
                "Critical Care Medicine","Gastroenterology","Rheumatology",
                "Infectious Disease","Neurology","Pediatrics","Endocrinology",
                "Cardiology","Nephrology","Oncology","Hepatology","Pulmonology",
                "Dermatology","Otolaryngology","Allergy & Immunology",
                "General Surgery","Orthopaedic Surgery","Psychiatry"),
  n  = c(734,837,551,406,1986,1004,1280,435,216,2327,5524,444,2338,956,1088,
         670,113,222,495,351,716),
  A  = c(40,4,26,23,139,89,118,41,24,270,656,54,296,144,175,109,23,49,128,93,226),
  DE = c(496,496,300,161,529,339,387,148,38,974,2361,143,933,280,622,198,5,95,51,67,161),
  stringsAsFactors = FALSE
)

cat(sprintf("  %-26s %5s  %s\n", "Specialty", "n", "% Level A (95% CI)"))
for (i in seq_len(nrow(spec))) {
  w <- wilson(spec$A[i], spec$n[i])
  cat(sprintf("  %-26s %5d  %s\n", spec$specialty[i], spec$n[i], fmt(w)))
}

cat("\n  Range of % Level A across specialties: ",
    sprintf("%.1f%% to %.1f%%\n",
            min(100 * spec$A / spec$n), max(100 * spec$A / spec$n)))

cat("\n=====================================================================\n")
cat(" SPECIALTY-WEIGHTED MEAN EVIDENCE GAP  (mean across 21 specialties)\n")
cat("=====================================================================\n")

gaps <- c(0.664,0.656,0.577,0.543,0.542,0.532,0.523,0.504,0.497,0.490,
          0.483,0.480,0.473,0.458,0.458,0.451,0.394,0.371,0.330,0.327,0.308)
m  <- mean(gaps); s <- sd(gaps); ng <- length(gaps)
tcrit <- qt(0.975, df = ng - 1)
ci <- m + c(-1, 1) * tcrit * s / sqrt(ng)
cat(sprintf("  Mean evidence gap = %.3f (SD %.3f); 95%% CI, %.3f-%.3f  (n = %d specialties)\n",
            m, s, ci[1], ci[2], ng))

cat("\n=====================================================================\n")
cat(" EXTRACTION-VALIDATION ACCURACY  (stratified 5% recommendation sample)\n")
cat("=====================================================================\n")

# Evidence-level accuracy: 97.1% of 1,179 sampled recommendations.
# Adjust 'correct' to the exact numerator from your validation file if it differs.
val_n <- 1179
val_correct <- round(0.971 * val_n)   # = 1145
cat(sprintf("  Evidence-level accuracy: %s  [%d / %d correct]\n",
            fmt(wilson(val_correct, val_n)), val_correct, val_n))

cat("\nDone.\n")
