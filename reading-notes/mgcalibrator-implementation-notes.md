# Reading Notes: MGCalibrator Implementation

These are implementation-level notes on [MGCalibrator](https://github.com/NimroddeWit/MGCalibrator), focusing on design choices visible in the source that matter for understanding what the tool actually does and where it might behave unexpectedly.

## Package Layout

The codebase is a small Python package with four main modules:

- **`cli.py`** — The entry point. Orchestrates the pipeline: BAM discovery → optional filtering → depth extraction → scaling factor computation → error propagation → output writing.
- **`fileutils.py`** — File path handling and I/O utilities. Straightforward.
- **`parser.py`** — Sample identification from filenames. This is where naming conventions become critical (see below).
- **`processor.py`** — The computational core: depth computation, scaling factor calculation, and Monte Carlo simulation for uncertainty estimation.

## Design Choice: Filename-Coupled Sample Identity

The parser infers sample identity from BAM filenames rather than from a separate metadata file. This is a pragmatic choice—it avoids requiring an explicit sample sheet—but it creates a hard coupling between file naming conventions and analytical correctness.

If your BAM files are named inconsistently, or if the naming pattern changes between batches, the parser will silently produce incorrect sample groupings. There is no validation step that catches this.

**Practical implication:** Any workflow that uses MGCalibrator needs a strict naming convention established before sequencing, not after. This is a metadata hygiene issue, not a software bug.

## Design Choice: `samtools depth -a`

The tool uses `samtools depth -a` to extract coverage, which includes positions with zero coverage in the output. This is important because without the `-a` flag, zero-coverage positions are omitted, and mean depth calculations would be inflated (averaging only over covered positions, not over the full reference length).

This is a correct design choice that some similar tools get wrong.

## Design Choice: Optional Identity Filtering via CoverM

Before quantification, MGCalibrator can optionally filter reads by minimum percent identity using CoverM. This is a quality gate: it removes poorly aligned reads that contribute to coverage but do not represent genuine mapping.

The trade-off is that setting the identity threshold too high discards reads from divergent organisms (which are real signal), while setting it too low lets misaligned reads inflate coverage estimates (which is noise). There is no universally correct setting.

## Design Choice: Monte Carlo Uncertainty

Rather than reporting calibrated depth as a point estimate, the processor module propagates uncertainty through Monte Carlo simulation. This means the tool acknowledges that both the raw depth measurement and the DNA mass measurement carry error, and it estimates how much that error affects the final calibrated output.

This is the most technically interesting part of the implementation. It means the output is not just a number but a number with a credible interval—something most metagenomic quantification tools do not provide.

## Design Choice: Clustering and Binning Aggregation

MGCalibrator supports three levels of analysis:

1. **Individual references** — each reference sequence gets its own depth and calibration.
2. **Clusters** — references grouped by similarity, with depth anchored to the shortest reference in the cluster.
3. **Bins** — references grouped by binning results, with positional displacement used for aggregation.

The choice of shortest reference as the size anchor for clusters is a conservative design choice: it avoids inflating depth estimates when cluster members vary substantially in length.

## Scaling Factor Reuse

Computed scaling factors can be cached and reused across analyses. This is practical for large studies where recomputing scaling factors for every analysis run would be wasteful, and it supports reproducibility by ensuring that the same scaling factor is applied consistently.

## What I Would Check Before Trusting Results

1. Verify that BAM filenames parse correctly by inspecting the parser's sample-to-file mapping output.
2. Spot-check a few coverage values against manual `samtools depth` runs.
3. Compare Monte Carlo confidence intervals across samples—if intervals are extremely wide, the DNA mass measurement or sequencing depth may be insufficient.
4. Test sensitivity to the identity filtering threshold by running with and without it.

## Related Notes

- [MGCalibrator](../tools/mgcalibrator.md) — tool overview
- [Absolute Abundance in Metagenomics](../notes/absolute-abundance.md) — broader context on the problem MGCalibrator addresses
