# Conifer: The Confidence Layer

[Conifer](https://github.com/Ivarz/Conifer) is a post-classification scoring utility for Kraken2 output. It is *not* a general classifier, but a dedicated filter that addresses the inherent noise and false-positive rates of rapid k-mer based classification.

## Core Features
- Uses standard Kraken2 output alongside the `taxo.k2d` database.
- Computes **confidence** and **read-to-length (RTL)** scores per classified read.
- Supports paired-end averaging to reduce mate-pair classification discrepancies.
- Summarizes taxon-level score distributions using quartile statistics, allowing for threshold-based filtering of entire taxonomic groups.

## Licensing and Implementation
Conifer is released under the **BSD-2-Clause license**. It is built on a small, narrow C codebase. This makes the tool highly inspectable and reusable as a source of ideas for performance-critical metagenomic parsing. We do not vendor Conifer, but we rely on its principles to ensure data quality before downstream analysis.

## Role in the Pipeline Stack
Conifer forms the **Confidence Layer** of our metagenomic stack. Raw read counts from classifiers like Kraken2 often contain low-abundance false positives that can skew ecological interpretations. By placing Conifer immediately after classification, we discard noise and pass only high-confidence taxonomic assignments to the Calibration Layer.

### Assumptions and Caveats
- Conifer fundamentally assumes you are integrating it downstream of Kraken2. It relies directly on Kraken2's specific output format.
- It requires the explicit `taxo.k2d` index to resolve taxonomy paths efficiently.
- Threshold decisions (e.g., minimum RTL score) require judgment; overly aggressive filtering can suppress rare but real taxa.
