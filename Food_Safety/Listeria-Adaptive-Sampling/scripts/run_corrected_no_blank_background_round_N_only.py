#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

from listeria_pipeline_common import ROOT

DEFAULT_INPUT = ROOT / "data" / "listeria_final_corrected.xlsx"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "corrected_no_blank_background_N_only"
DEFAULT_SHEET = "Data"


def run_step(command: list[str]) -> None:
    print(f"[run] {' '.join(str(part) for part in command)}")
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the corrected Listeria analysis round on the Native-only (Condition == 'N') "
            "subset, without touching the existing corrected_no_blank_background outputs."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def write_n_only_xlsx(input_path: Path, sheet: str, output_root: Path) -> tuple[Path, str]:
    df = pd.read_excel(input_path, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    if "Condition" not in df.columns:
        raise SystemExit(f"Expected 'Condition' column in {input_path} (sheet {sheet!r}).")

    condition_norm = df["Condition"].apply(lambda v: v.strip() if isinstance(v, str) else v)
    mask = condition_norm == "N"
    n_rows = int(mask.sum())
    if n_rows == 0:
        raise SystemExit("No rows with Condition == 'N' found; nothing to process.")

    filtered = df.loc[mask].copy()
    output_root.mkdir(parents=True, exist_ok=True)
    filtered_sheet = "Data"
    filtered_path = output_root / "listeria_final_corrected_N_only.xlsx"
    with pd.ExcelWriter(filtered_path, engine="openpyxl") as writer:
        filtered.to_excel(writer, sheet_name=filtered_sheet, index=False)

    print(
        f"[filter] Kept {n_rows} of {len(df)} rows (Condition == 'N') -> {filtered_path}"
    )
    return filtered_path, filtered_sheet


def main() -> None:
    args = parse_args()

    if args.output_root.exists() and any(args.output_root.iterdir()):
        print(
            f"[warn] Output root {args.output_root} already contains files; "
            "individual scripts may overwrite them. Pass a different --output-root to stay safe."
        )

    filtered_input, filtered_sheet = write_n_only_xlsx(
        args.input, args.sheet, args.output_root
    )

    common = [
        "--input",
        str(filtered_input),
        "--sheet",
        filtered_sheet,
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
            str(filtered_input),
            "--source-sheet",
            filtered_sheet,
        ]
    )
    run_step(
        [
            sys.executable,
            str(ROOT / "scripts" / "export_mwu_docx.py"),
            "--output-root",
            str(args.output_root),
            "--source-input",
            str(filtered_input),
            "--source-sheet",
            filtered_sheet,
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
    print(f"\nCompleted N-only corrected rerun at {args.output_root}")


if __name__ == "__main__":
    main()
