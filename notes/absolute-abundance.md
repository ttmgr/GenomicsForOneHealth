# Absolute Abundance in Metagenomics

## The Compositionality Problem

Standard metagenomic profiling produces relative abundances: each taxon is reported as a fraction of the total classified reads. This is useful for comparing community structure, but it fails at a deceptively simple question: *Is there more or less of this organism than before?*

The problem is mathematical. Relative abundances are constrained to sum to one. If a single taxon increases in absolute terms, every other taxon's relative abundance necessarily decreases, even if their actual load has not changed. Conversely, a taxon can appear to increase in relative terms simply because something else decreased.

This is not a software bug; it is a property of compositional data. And it means that any inference about changes in biological load from relative profiles alone is fundamentally ambiguous.

## Why It Matters in Practice

The compositionality problem becomes operationally important in several settings:

**Wastewater and environmental surveillance.** When monitoring ARG loads or pathogen levels over time, the public health question is usually "Is there more?" not "Is the proportion higher?" A spike in ARG copies per liter matters regardless of what the rest of the community is doing.

**Clinical metagenomics.** Tracking pathogen load during treatment requires absolute quantification. A pathogen that drops from 10⁶ to 10⁴ copies/mL is clinically significant even if its relative abundance has not moved because the commensal flora was also affected by antibiotics.

**Time-series studies.** Any longitudinal analysis where the total microbial load changes between timepoints will produce misleading results from relative profiles alone.

## Approaches to Absolute Quantification

There is no single standard method for absolute metagenomic quantification. The main approaches, each with trade-offs:

### Spike-in Standards

Add a known quantity of synthetic or non-native DNA before extraction. The spike-in's sequencing depth serves as a scaling reference. This is conceptually clean but requires careful calibration of the spike-in amount, and contamination of the spike-in itself can introduce bias.

### qPCR Anchoring

Use quantitative PCR targeting universal markers (e.g., 16S rRNA gene) or specific targets to establish total or target-specific copy numbers, then use metagenomic relative abundances to partition that total.

This is widely used but couples the strengths and weaknesses of both methods. The qPCR estimate has its own biases (primer specificity, amplification efficiency), and errors in the anchor propagate into all downstream estimates.

### DNA Mass Calibration

Measure total extracted DNA mass (e.g., via Qubit) and use this, together with sequencing depth, to compute a scaling factor that converts coverage into absolute units. This is the approach taken by [MGCalibrator](../tools/mgcalibrator.md).

The advantage is that DNA mass measurement is simple and routinely available. The disadvantage is that it does not account for extraction bias—organisms that lyse poorly will still be underrepresented, and the DNA mass measurement cannot distinguish which organisms contributed how much to the total.

### Flow Cytometry

Count total cells before extraction and use this as the denominator. Most relevant for water and liquid samples. Adds a step but provides an independent measurement of total abundance.

## What Calibration Does and Does Not Fix

Calibration methods like MGCalibrator address the **scaling problem**: they make samples comparable in absolute terms rather than only in relative terms. But they do not fix:

- **Extraction bias** — differential lysis means some organisms contribute less DNA than their true abundance warrants.
- **Reference bias** — organisms without close database matches will be under-mapped and under-counted.
- **PCR and library prep bias** — amplification-based protocols can distort abundance profiles before sequencing even begins.
- **Incomplete reference databases** — reads from unknown organisms are unmapped and therefore invisible to coverage-based quantification.

The honest framing is: calibration moves you from a dimensionless ratio to a quantity with units, but that quantity still inherits every upstream bias in the measurement chain.

## Where This Fits in My Workflow

In my own work with environmental and wastewater metagenomes, absolute abundance estimation is most valuable at two moments:

1. **Before ecological analysis** — when I need to determine whether a compositional shift reflects a genuine change in load or just a redistribution of the same total signal.
2. **When communicating results to non-specialists** — because "10⁵ copies per gram" is more actionable than "4.2% relative abundance" for public health or environmental management decisions.

The tooling is still maturing, and no method is fully satisfying yet. But ignoring the problem—treating relative profiles as if they were absolute—is worse than using an imperfect calibration.

## What I Would Test Next

- How sensitive are calibrated abundance estimates to variation in DNA extraction protocol?
- At what sequencing depth does calibration uncertainty become dominated by biological variability rather than technical noise?
- Can spike-in and DNA-mass calibration be cross-validated on the same samples to assess concordance?

## Related Notes

- [MGCalibrator](../tools/mgcalibrator.md) — a practical tool for DNA-mass-based calibration
- [From Classification to Calibration](../pipelines/from-classification-to-calibration.md) — how absolute quantification fits in the analytical pipeline
