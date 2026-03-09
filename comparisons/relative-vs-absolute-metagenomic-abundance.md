# Relative vs Absolute Metagenomic Abundance

## Two Different Questions

Relative abundance asks: *What fraction of this community is this organism?*

Absolute abundance asks: *How much of this organism is present?*

They sound similar but answer fundamentally different biological questions, and conflating them is one of the most common sources of misinterpretation in metagenomics.

## Why the Distinction Matters

Consider a wastewater monitoring scenario with two timepoints:

| Pathogen | Timepoint 1 (relative) | Timepoint 2 (relative) | Interpretation |
|---|---|---|---|
| Taxon A | 5% | 5% | Stable? |

If total microbial load doubled between timepoints, taxon A's **absolute** abundance also doubled—even though its relative abundance did not change. The relative profile says "nothing changed." The absolute profile says "the pathogen load doubled." These lead to very different public health decisions.

## Approaches Compared

| Method | What it measures | Pros | Cons |
|---|---|---|---|
| **Relative profiling** | Proportional composition | Simple, no extra data needed | Compositional bias, no load information |
| **qPCR anchoring** | Total/targeted copies via qPCR | Widely established, target-specific | Primer bias, separate assay required |
| **Spike-in standards** | Ratio to known spike quantity | Conceptually clean | Spike calibration, contamination risk |
| **DNA mass calibration** | Coverage scaled by total DNA mass | Uses routine measurements | Does not correct extraction bias |
| **Flow cytometry** | Total cell count | Independent measurement | Only for liquid samples, extra equipment |

No single method is fully satisfying. Each trades different biases for different types of information.

## Where [MGCalibrator](../tools/mgcalibrator.md) Fits

MGCalibrator implements the **DNA mass calibration** approach. It is appealing because:

- DNA mass measurement (e.g., Qubit) is already part of most library prep protocols.
- No additional wet-lab assays are required.
- The calibration is sample-specific, accounting for differences in extraction yield and sequencing depth.
- Uncertainty is propagated via Monte Carlo, so you know how much to trust the calibrated values.

It does not fix extraction bias or reference incompleteness. It is a scaling correction, not a debiasing step.

## When Relative Abundance Is Enough

Relative profiles are sufficient when:

- The question is about community structure or diversity, not about load.
- Total microbial load is assumed to be approximately constant across samples.
- You are comparing samples from the same experimental batch under controlled conditions.
- You are performing beta-diversity or ordination analyses where the compositional nature of the data is accounted for.

## When Absolute Quantification Is Needed

Absolute quantification becomes necessary when:

- The biological question involves changes in load (e.g., pathogen abundance in wastewater over time).
- Total microbial biomass varies across samples (e.g., different environments, different time points).
- You need to report quantities with units for clinical or regulatory purposes.
- You are modeling dose-response relationships where exposure levels matter.

## What Remains Unresolved

- How well do different calibration approaches agree when applied to the same samples?
- At what point does calibration uncertainty become too large to be useful?
- Can compositional data analysis methods (e.g., CLR transformation) serve as a middle ground between raw relative abundance and full absolute quantification?

## Related Notes

- [MGCalibrator](../tools/mgcalibrator.md) — DNA mass calibration tool
- [Absolute Abundance in Metagenomics](../notes/absolute-abundance.md) — broader concept discussion
- [MGCalibrator Implementation Notes](../reading-notes/mgcalibrator-implementation-notes.md) — design-level details
