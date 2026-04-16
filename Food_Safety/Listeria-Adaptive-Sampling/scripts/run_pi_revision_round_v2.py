#!/usr/bin/env python3
"""PI revision round v2: same pipeline as v1, but into a fresh output root.

Use this after Francis sends the new Excel from the cluster rerun (minimap2
with the expanded reference: 4 Lm strains + L. innocua + L. ivanovii +
L. welshimeri + background species references for Bacillus etc.).

Usage:
    python scripts/run_pi_revision_round_v2.py \\
        --input /path/to/new_listeria_cluster_rerun.xlsx \\
        --sheet Data \\
        --output-root outputs/pi_revision_v2

Defaults assume the file is at ~/Downloads/listeria_final_corrected_v2.xlsx;
override with --input if it lives somewhere else.

The pipeline is column-name tolerant: extra background-species columns in the
new Excel (e.g. `Bacillus cereus Reads`) are ignored by the plots, which only
use the hard-coded `LM_STRAINS` and `OTHER_STRAINS` lists from
`listeria_pipeline_common.py`. The following columns MUST still be present
for everything to work:

    Sample Type, Condition, Treatment, Swab Type, Lab ID,
    Total Reads, Total Bases, Mean Read Length, Mean Read Quality,
    EGDe Reads, LL195 Reads, LMNC326 Reads, N13-0119 Reads,
    L. innocua J5051 Reads, L. ivanovii Nr26 Reads, L. welshimeri Nr14 Reads,
    Lm Total Reads (4 strains), Lm Total Bases, Lm Mean Read Length,
    Lm % Reads, Lm % Bases,
    # Lm Strains Detected, Detected Strains, Dominant Lm Strain,
    L. ivanovii Nr26 Proportion,
    Extraction Kit, DNA Conc. (ng/uL)

If Francis renames any of those, the pipeline will break early and tell you
which column is missing.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from listeria_pipeline_common import ROOT

DEFAULT_INPUT = ROOT / "data" / "listeria_final_corrected_v2.xlsx"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "pi_revision_v2"
DEFAULT_SHEET = "Data"


def run_step(command: list[str]) -> None:
    print(f"[run] {' '.join(str(part) for part in command)}")
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(
            f"Input file not found: {args.input}\n"
            "Drop the new cluster Excel at that path or pass --input /other/path.xlsx"
        )

    common = [
        "--input",
        str(args.input),
        "--sheet",
        args.sheet,
        "--output-root",
        str(args.output_root),
    ]

    run_step([sys.executable, str(ROOT / "scripts" / "analyze_listeria.py"), *common])
    run_step([sys.executable, str(ROOT / "scripts" / "plot_listeria_publication_v4.py"), *common])
    run_step(
        [
            sys.executable,
            str(ROOT / "scripts" / "export_all_stats_tables.py"),
            "--output-root",
            str(args.output_root),
            "--source-input",
            str(args.input),
            "--source-sheet",
            args.sheet,
        ]
    )
    run_step(
        [
            sys.executable,
            str(ROOT / "scripts" / "export_mwu_docx.py"),
            "--output-root",
            str(args.output_root),
            "--source-input",
            str(args.input),
            "--source-sheet",
            args.sheet,
        ]
    )
    run_step(
        [
            sys.executable,
            str(ROOT / "scripts" / "export_results_summary_sheet.py"),
            "--output-root",
            str(args.output_root),
        ]
    )
    run_step(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mwu_excel.py"),
            "--output-root",
            str(args.output_root),
        ]
    )
    print(f"\nCompleted PI revision round v2 at {args.output_root}")
    print(f"New per-strain timecourse figure: {args.output_root / 'fig_strain_timecourse_per_strain.pdf'}")


if __name__ == "__main__":
    main()
