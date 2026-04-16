#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SECTION_CONFIG = {
    "Direct metagenomics": {
        "sample_type": "metagenomics",
        "approach": "Metagenomics",
        "batch": "",
        "timepoint": "0h",
        "time_hours": 0,
    },
    "Quasimetagenomics HFB 4h": {
        "sample_type": "quasimeta_4h",
        "approach": "Quasimetagenomics",
        "batch": "HFB",
        "timepoint": "4h",
        "time_hours": 4,
    },
    "Quasimetagenomics HFB 12h": {
        "sample_type": "quasimeta_12h",
        "approach": "Quasimetagenomics",
        "batch": "HFB",
        "timepoint": "12h",
        "time_hours": 12,
    },
    "Quasimetagenomics HFB 24h": {
        "sample_type": "quasimeta_24h_1",
        "approach": "Quasimetagenomics",
        "batch": "HFB",
        "timepoint": "24h",
        "time_hours": 24,
    },
    "Quasimetagenomics FFB 24h": {
        "sample_type": "quasimeta_24h_2",
        "approach": "Quasimetagenomics",
        "batch": "FFB",
        "timepoint": "24h",
        "time_hours": 24,
    },
    "Quasimetagenomics FFB 48h": {
        "sample_type": "quasimeta_48h",
        "approach": "Quasimetagenomics",
        "batch": "FFB",
        "timepoint": "48h",
        "time_hours": 48,
    },
}

KIT_MAP = {
    "Power soil": "PowerSoil",
}

SWAB_MAP = {
    "-": "",
}


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_workbook(workbook_path: Path) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    source_order = 0

    for sheet_name in ["Direct metagenomics", "Quasimeta"]:
        raw = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
        current_section = ""
        header: list[str] | None = None

        for row_index, row in raw.iterrows():
            row_values = row.tolist()
            non_empty = [value for value in row_values if pd.notna(value)]
            if not non_empty:
                continue

            first_cell = clean_text(non_empty[0])
            if first_cell in SECTION_CONFIG:
                current_section = first_cell
                header = None
                continue

            if first_cell == "Time":
                header = [clean_text(value) for value in row_values]
                continue

            if not current_section or header is None:
                continue

            raw_record = {
                column: value
                for column, value in zip(header, row_values)
                if column
            }
            if clean_text(raw_record.get("Time", "")) == "Time":
                continue

            config = SECTION_CONFIG[current_section]
            source_order += 1

            sample_id = clean_text(raw_record.get("Sample ID", ""))
            lab_id = clean_text(raw_record.get("Lab. ID", "")) or sample_id
            kit_used = KIT_MAP.get(clean_text(raw_record.get("Kit used", "")), clean_text(raw_record.get("Kit used", "")))
            swab_type = SWAB_MAP.get(clean_text(raw_record.get("Swab type", "")), clean_text(raw_record.get("Swab type", "")))
            time_entry = clean_text(raw_record.get("Time", ""))

            records.append(
                {
                    "source_order": source_order,
                    "source_sheet": sheet_name,
                    "section_title": current_section,
                    "workbook_row": row_index + 1,
                    "sample_type": config["sample_type"],
                    "approach": config["approach"],
                    "batch": config["batch"],
                    "timepoint": config["timepoint"],
                    "time_hours": config["time_hours"],
                    "time_entry": time_entry,
                    "is_control_row": time_entry == "Control",
                    "swab_type": swab_type,
                    "sample_id": sample_id,
                    "lab_id": lab_id,
                    "treatment": clean_text(raw_record.get("Treatment", "")),
                    "replicate": clean_text(raw_record.get("Replicate", "")),
                    "bar_code": clean_text(raw_record.get("Bar code", "")),
                    "quantifluor_ng_ul": clean_text(raw_record.get("QuantiFluor (ng/uL)", "")),
                    "volume_ul": clean_text(raw_record.get("Volume (ul)", "")),
                    "label_colour": clean_text(raw_record.get("Label colour", "")),
                    "extraction_kit": kit_used,
                    "comment": clean_text(raw_record.get("Comment", "")),
                }
            )

    return pd.DataFrame(records)


def add_match_status(notes_df: pd.DataFrame, listeria_path: Path) -> pd.DataFrame:
    if not listeria_path.exists():
        notes_df["sequencing_match_status"] = "listeria_reads.csv not found"
        return notes_df

    seq = pd.read_csv(listeria_path)
    exact = set(
        seq[["Sample Type", "Lab ID", "Swab Type", "Extraction Kit", "Treatment"]]
        .fillna("")
        .astype(str)
        .apply(tuple, axis=1)
    )
    no_treatment = set(
        seq[["Sample Type", "Lab ID", "Swab Type", "Extraction Kit"]]
        .fillna("")
        .astype(str)
        .apply(tuple, axis=1)
    )

    statuses: list[str] = []
    for row in notes_df.itertuples(index=False):
        exact_key = (
            row.sample_type,
            row.lab_id,
            row.swab_type,
            row.extraction_kit,
            row.treatment,
        )
        fallback_key = (
            row.sample_type,
            row.lab_id,
            row.swab_type,
            row.extraction_kit,
        )
        if exact_key in exact:
            statuses.append("exact_match_in_listeria_reads")
        elif fallback_key in no_treatment and row.sample_type == "metagenomics":
            statuses.append("metagenomics_treatment_missing_in_listeria_reads")
        elif row.sample_type == "metagenomics" and clean_text(row.swab_type) == "":
            statuses.append("direct_no_swab_row_only_in_workbook")
        elif row.sample_type == "quasimeta_48h":
            statuses.append("48h_row_only_in_workbook")
        elif row.is_control_row:
            statuses.append("control_row_only_in_workbook")
        else:
            statuses.append("no_match_found")

    notes_df["sequencing_match_status"] = statuses
    return notes_df


def expand_conditions(notes_df: pd.DataFrame) -> pd.DataFrame:
    expanded_rows: list[dict[str, object]] = []

    for row in notes_df.to_dict("records"):
        for condition_order, condition in enumerate(["AS", "N"], start=1):
            expanded = dict(row)
            expanded["condition_order"] = condition_order
            expanded["condition"] = condition
            expanded_rows.append(expanded)

    expanded_df = pd.DataFrame(expanded_rows)
    expanded_df["output_order"] = range(1, len(expanded_df) + 1)
    return expanded_df


def build_combined_csv(workbook_path: Path, output_path: Path, listeria_path: Path) -> pd.DataFrame:
    notes_df = parse_workbook(workbook_path)
    notes_df = add_match_status(notes_df, listeria_path)
    combined_df = expand_conditions(notes_df)

    column_order = [
        "output_order",
        "source_order",
        "condition_order",
        "source_sheet",
        "section_title",
        "workbook_row",
        "sample_type",
        "approach",
        "batch",
        "timepoint",
        "time_hours",
        "time_entry",
        "is_control_row",
        "swab_type",
        "sample_id",
        "lab_id",
        "treatment",
        "replicate",
        "condition",
        "bar_code",
        "quantifluor_ng_ul",
        "volume_ul",
        "label_colour",
        "extraction_kit",
        "comment",
        "sequencing_match_status",
    ]
    combined_df = combined_df[column_order]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)
    return combined_df


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Clean the metagenomics master workbook into one combined CSV with explicit AS/N rows."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/metagenomics_master_file_v2.xlsx"),
        help="Path to the original workbook.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "outputs" / "metagenomics_master_file_v2_combined.csv",
        help="Where to write the cleaned combined CSV.",
    )
    parser.add_argument(
        "--listeria-csv",
        type=Path,
        default=root / "listeria_reads.csv",
        help="Optional existing sequencing CSV used for Lab ID/Treatment audit columns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    combined_df = build_combined_csv(args.input, args.output, args.listeria_csv)
    print(f"Saved {len(combined_df)} rows to {args.output}")
    print("Rows by sample type:")
    print(combined_df.groupby('sample_type').size().to_string())


if __name__ == "__main__":
    main()
