#!/usr/bin/env python3
"""Run the PI-revision round: same pipeline as the corrected round, but into
a separate output root so nothing existing is touched."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from listeria_pipeline_common import ROOT

DEFAULT_INPUT = ROOT / "data" / "listeria_final_corrected.xlsx"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "pi_revision_v1"
DEFAULT_SHEET = "Data"


def run_step(command: list[str]) -> None:
    print(f"[run] {' '.join(str(part) for part in command)}")
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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
    print(f"\nCompleted PI revision round at {args.output_root}")


if __name__ == "__main__":
    main()
