# Confidence Thresholds vs Post Hoc Scoring

## The Two Strategies

When working with Kraken2, there are two distinct strategies for managing classification quality:

**Strategy A: Threshold at classification time.** Use Kraken2's `--confidence` flag to set a minimum support fraction. Reads that fail are either unclassified or promoted to a higher taxonomic rank. This is simple, fast, and irreversible.

**Strategy B: Classify permissively, score afterward.** Run Kraken2 with a low or zero confidence threshold, then use a post hoc tool like [Conifer](../tools/conifer.md) to compute detailed scores and filter based on richer information. This preserves the raw classification data and allows exploration.

## How They Differ

| Aspect | At-classification threshold | Post hoc scoring |
|---|---|---|
| **When filtering happens** | During Kraken2 run | After Kraken2 run |
| **Reversibility** | No—failed reads must be reclassified | Yes—raw data preserved |
| **Score types available** | One (built-in confidence) | Multiple (confidence, RTL, quartiles) |
| **Taxon-specific thresholds** | Not supported | Possible via quartile inspection |
| **Computational cost** | None beyond initial classification | Small additional step |
| **Paired-end awareness** | Limited | Per-mate and averaged scores |

## When Thresholding Is Sufficient

For many analyses, the built-in threshold works fine:

- When the database is high-quality and well-matched to the sample.
- When you care about community-level patterns, not individual taxon presence.
- When a moderate false-positive rate is acceptable.
- When speed matters and adding another tool is unwanted overhead.

## When Post Hoc Scoring Is Worth the Extra Step

Post hoc scoring adds value when:

- You need to justify species-level calls for surveillance or clinical reporting.
- The sample is ecologically complex (environmental, wastewater) and false positives are likely.
- You want to explore multiple thresholds without re-running classification.
- You want taxon-specific quality assessment, not a single global gate.
- You are working with long reads where the relationship between read length and k-mer support may differ from short-read assumptions.

## What I Would Do in Practice

My default approach for environmental metagenomes: run Kraken2 with `--confidence 0.0` (or `0.05`), then use Conifer to inspect score distributions for the taxa I actually care about. Set taxon-specific thresholds based on quartile summaries rather than a global cutoff.

For clinical or food safety samples where false positives carry real consequences: use both strategies—apply a moderate Kraken2 threshold *and* validate surviving calls with post hoc scoring.

## Related Notes

- [Conifer](../tools/conifer.md) — the post hoc scoring tool
- [Kraken2 Confidence Thresholds](../notes/kraken-confidence.md) — deeper discussion of threshold limitations
- [Conifer Score Notes](../reading-notes/conifer-score-notes.md) — scoring mechanics
