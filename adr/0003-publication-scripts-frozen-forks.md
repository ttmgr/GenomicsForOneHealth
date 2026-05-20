# Publication analysis scripts are kept as frozen variant forks

Several analysis scripts exist as near-duplicate variants — e.g. `17_generate_report.py` and
`17_generate_report_v2.py`, `plot_listeria.py` and `plot_listeria_publication_v4.py`,
`inference.py` and `inference_read_level.py`, `ResNet.py` and `ResNet4Sequence.py`. These look
like un-merged copies, but the publication-tied variants are **deliberately frozen snapshots**
that reproduce specific results and figures.

We keep them forked rather than merge them, and record this so future reviews don't try to DRY
them up. The cost of a silent change to a script that backs a published figure outweighs the
locality benefit of de-duplication.

A genuinely active pair may share most of a kernel (the two `inference*` scripts are the closest
case), but consolidating even those is scientific code that cannot be verified against real data
in this environment; defer until it can be run and diffed.

_Status: accepted._
