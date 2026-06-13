# Defer cross-pipeline consolidation of analysis-script parsing and figures

The Python analysis scripts across pipeline domains reimplement Kraken2 parsing and matplotlib
figure styling, which looks like duplication ripe for a shared module. We inspected it and
decided **not** to consolidate now, and to record why so future architecture reviews don't
re-suggest it without this context.

## Why not

- **The Kraken2 taxon field is parsed with materially different semantics at each site.**
  Greedy `^(.*)\s+\(taxid\s+(\d+)\)\s*$` keeping name + taxid in
  `21_kraken2_to_spreadsheets.py`; lazy `^(.*?)\s*\(taxid\s+\d+\)\s*$` stripping the suffix in
  `22_kraken2_classification_csv.py`; and `\(taxid\s+(\d+)\)` plus a strip-all-parens
  `clean_taxon` with an "Unclassified" fallback in `amr_host_association.py`. Unifying these
  would silently change at least one script's output.
- **Each plotting script defines its own rcParams and palette constants.** A shared style module
  risks altering already-published figures.
- **These scripts are publication-adjacent and cannot be re-run against the original data in this
  environment**, so behavior-preserving extraction cannot be verified here.
- **There is no cross-pipeline Python package today.** Scripts import same-directory siblings
  (e.g. `listeria_pipeline_common.py`); sharing across pipeline directories would require
  introducing packaging.

## If consolidated later

Pick one canonical Kraken2 taxon-parsing semantics; pin each script's current behavior with
characterization tests; verify outputs against the original data; and introduce a small
installable shared package as the home before migrating call sites.

_Status: accepted (consolidation deferred, not rejected)._
