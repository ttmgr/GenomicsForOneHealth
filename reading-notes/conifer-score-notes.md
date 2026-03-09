# Reading Notes: Conifer Score Mechanics

These are working notes on how [Conifer](https://github.com/Ivarz/Conifer) computes its scores, drawn from the source code and README. The goal is to understand the scoring mechanics well enough to make informed threshold decisions, not to reproduce the implementation.

## The Two Score Families

Conifer produces two distinct types of scores. They are complementary, not interchangeable.

### Confidence Score

The confidence score asks: *Of all the k-mers in this read that hit the taxonomy tree, what fraction supports the assigned taxon or its descendants?*

A high confidence score means the k-mer evidence is internally consistent with the classification. A low score means the k-mers are scattered across multiple branches, and the assigned taxon was chosen despite ambiguity.

**What it tells you:** How much agreement exists within the evidence for this specific classification.

**What it does not tell you:** Whether the classification is actually correct. A read can have high confidence for the wrong taxon if the true source organism is absent from the database.

### RTL Score (Root-to-Leaf)

The RTL score takes a broader perspective. Instead of looking only at support for the assigned node and its descendants, it considers the full path from the root of the taxonomy tree to the assigned leaf.

This matters because a read might have strong genus-level support but weak species-level support. The confidence score would still reflect the species-level assignment, while the RTL score would capture the uneven distribution of evidence along the path.

**What it tells you:** How uniformly the evidence supports the entire taxonomic path, not just the terminal node.

**When to prefer it:** When species-level calls are important and you want to distinguish between reads with deep, path-consistent support and reads with shallow, node-specific support.

## Paired-End Score Handling

For paired-end data, Conifer computes scores for each mate separately, then optionally reports the **average** across the pair. This is useful because mates often receive different classifications or different levels of support.

In practice, the average provides a more stable signal per fragment. Reads where both mates agree tend to have higher average scores; reads where mates disagree tend to have lower average scores. This natural behavior makes paired-end averaging a useful filter for ambiguous fragments.

## Taxon-Level Summaries

Beyond per-read scores, Conifer can aggregate scores by assigned taxon and report **P25, P50, and P75 quartiles**. This transforms read-level QC into taxon-level quality profiling.

The practical questions this answers:

- **Is this taxon's classification consistently well-supported?** Look at the median (P50) and the spread (P25–P75 range).
- **Are there taxa propped up by a few high-scoring reads but dragged down by many low-scoring ones?** A low P25 with a high P75 indicates inconsistent support.
- **Where should I set thresholds?** If most reads for a taxon have scores below 0.3, that taxon probably should not survive filtering—even if a few reads score well.

## Combining Both Scores

Running both confidence and RTL scores simultaneously on the same data gives you a two-dimensional view of classification quality. Taxa where both scores are high are well-supported. Taxa where confidence is high but RTL is low might be confidently assigned at the wrong taxonomic level. Taxa where both are low are noise candidates.

This two-score approach is more informative than any single threshold, and it is one of the main reasons Conifer adds value over Kraken2's built-in confidence flag.

## What I Want to Explore Further

- How do Conifer score distributions change with database composition? Adding or removing reference genomes changes the k-mer landscape, which should shift score distributions in predictable ways.
- Is there a meaningful relationship between read length (relevant for long reads) and Conifer scores? Longer reads have more k-mers, which could either stabilize or destabilize scores depending on the organism.
- Can Conifer scores be used to set taxon-specific thresholds empirically—e.g., filtering at the P25 of each taxon rather than applying a global cutoff?

## Related Notes

- [Conifer](../tools/conifer.md) — tool overview
- [Kraken2 Confidence Thresholds](../notes/kraken-confidence.md) — broader threshold discussion
