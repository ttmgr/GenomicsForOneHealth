# Kraken2 Confidence: When Default Thresholds Are Not Enough

## The Problem

Kraken2 assigns taxonomy using exact k-mer matching against a pre-built database. It is fast—often the fastest option available—but its default output is deceptively confident. Every classified read gets a taxon label, and without explicit thresholding, all labels carry equal weight regardless of how much evidence supports them.

The built-in `--confidence` flag helps by requiring a minimum fraction of k-mers to agree with the assigned taxon before emitting a classification. But this is a single gate applied at classification time, and it has two limitations worth understanding.

## Limitation 1: The Threshold Is Applied Globally

A single confidence value is applied identically across all reads and all taxa. But different taxonomic levels and different organisms have different baseline levels of k-mer ambiguity. A confidence threshold of 0.2 might be appropriate for well-represented species but too permissive for taxa with close relatives in the database—or too strict for genuinely divergent environmental organisms.

There is no built-in mechanism for taxon-specific thresholding.

## Limitation 2: Thresholding Is Destructive

When Kraken2 applies its confidence threshold, reads that fail are either left unclassified or reclassified at a higher taxonomic rank. The underlying score information—how much support existed, at what taxonomic level—is discarded from the perspective of the downstream user.

This means you cannot retrospectively ask: "How confident was this species-level call?" once the threshold has already been applied. You would need to re-run Kraken2 with different thresholds to explore the sensitivity-specificity tradeoff.

## Post Hoc Scoring as an Alternative

Tools like [Conifer](../tools/conifer.md) take a different approach. Instead of gating at classification time, they re-examine the k-mer evidence from standard Kraken2 output after the fact, computing read-level and taxon-level confidence statistics that the user can then threshold, filter, or inspect as needed.

This has several practical advantages:

- You run Kraken2 once and explore threshold options afterward.
- You can compute multiple score types (confidence, RTL) and compare them.
- You can inspect *distributions* of scores at the taxon level, not just binary pass/fail.
- You preserve the raw classification data for reproducibility.

## When Does This Actually Matter?

In practice, default Kraken2 thresholds are often good enough for well-characterized clinical samples or deeply sequenced isolates. The confidence question becomes important when:

- **Environmental metagenomes** contain high novelty and many taxa near the database's edge.
- **Low-abundance organisms** are of interest and might be discarded by aggressive thresholds.
- **Species-level calls** are being used for epidemiological or surveillance purposes where false positives carry real-world consequences.
- **Long-read data** interacts with k-mer classification in ways that differ from short reads, and the appropriate threshold may need recalibration.

## What I Would Validate Before Trusting Any Threshold

1. Run Kraken2 with no threshold (or a very permissive one).
2. Use Conifer or a similar post hoc tool to inspect score distributions for key taxa.
3. Compare the taxa that survive different threshold choices.
4. Cross-reference with an independent method (BLAST, minimap2 alignment, assembly-based classification) for at least a subset.
5. Accept that the "right" threshold is sample-dependent, not universal.

## Related Notes

- [Conifer](../tools/conifer.md) — the post-classification scoring utility
- [From Classification to Calibration](../pipelines/from-classification-to-calibration.md) — where confidence scoring fits in the broader pipeline
