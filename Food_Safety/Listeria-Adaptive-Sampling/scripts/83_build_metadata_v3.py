#!/usr/bin/env python3
"""
Step 83: Build sample_metadata_v3.csv from listeria_wrong_order_but_barcodes_and_sample_ids.xlsx.

Replaces the legacy sample_metadata.csv (which had r1+r2-only / D4-T61 collisions /
missing background Lab IDs) with a clean sheet derived from the authoritative Excel
whose `Sample ID` column already encodes the pipeline basename.

Outputs:
  - downloaded_results/samplesheets/sample_metadata.csv  (read by script 82)
  - sample_metadata_v3.csv                              (project-root backup)

Usage:
  python scripts/83_build_metadata_v3.py
"""

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
EXCEL = PROJECT_DIR / "listeria_wrong_order_but_barcodes_and_sample_ids.xlsx"
CORRECT_TABLE = PROJECT_DIR / "listeria_correct_table.csv"
STRAIN_MASTER = PROJECT_DIR / "listeria_final_final_strain" / "strain_proportions_master_5.csv"
OUT_CLUSTER = PROJECT_DIR / "downloaded_results" / "samplesheets" / "sample_metadata.csv"
OUT_BACKUP = PROJECT_DIR / "sample_metadata_v3.csv"

SAMPLE_TYPE_TO_ROUND = {
    "metagenomics": 1,
    "quasimeta_24h_1": 2,
    "quasimeta_4h": 3,
    "quasimeta_24h_2": 4,
    "quasimeta_12h": 5,
}

BASENAME_RE = re.compile(r"^r(\d+)_barcode(\d+)_(AS|N)$")


def main() -> int:
    xl = pd.read_excel(EXCEL, sheet_name="Data")
    print(f"Loaded {len(xl)} rows from {EXCEL.name}")

    # Excel has NaN Treatment for all r1 metagenomics rows; fall back to
    # listeria_correct_table.csv where (Sample Type, Lab ID) -> Treatment is
    # 1:1 within a round.
    if xl["Treatment"].isna().any():
        ct = pd.read_csv(CORRECT_TABLE)
        treatment_lookup = (
            ct.dropna(subset=["Treatment"])
            .drop_duplicates(subset=["Sample Type", "Lab ID"])
            .set_index(["Sample Type", "Lab ID"])["Treatment"]
        )
        missing_mask = xl["Treatment"].isna()
        keys = list(zip(xl.loc[missing_mask, "Sample Type"], xl.loc[missing_mask, "Lab ID"]))
        filled = pd.Series(
            [treatment_lookup.get(k) for k in keys],
            index=xl.index[missing_mask],
        )
        xl.loc[missing_mask, "Treatment"] = filled
        still_missing = xl["Treatment"].isna().sum()
        print(f"Filled {missing_mask.sum() - still_missing} missing Treatment values from {CORRECT_TABLE.name}")
        if still_missing:
            print(f"ERROR: {still_missing} rows still have missing Treatment after fallback lookup")
            return 1

    if xl["Sample ID"].isna().any():
        missing = xl[xl["Sample ID"].isna()]
        print(f"ERROR: {len(missing)} rows have blank Sample ID:")
        print(missing[["Sample Type", "Lab ID", "Condition"]].to_string(index=False))
        return 1

    parsed = xl["Sample ID"].str.extract(BASENAME_RE)
    if parsed.isna().any().any():
        bad = xl.loc[parsed.isna().any(axis=1), "Sample ID"].tolist()
        print(f"ERROR: malformed Sample ID values: {bad[:10]}")
        return 1

    round_from_id = parsed[0].astype(int)
    round_from_type = xl["Sample Type"].map(SAMPLE_TYPE_TO_ROUND)
    mismatch = round_from_id != round_from_type
    if mismatch.any():
        print(f"ERROR: round mismatch between Sample Type and Sample ID in {mismatch.sum()} rows:")
        print(xl.loc[mismatch, ["Sample Type", "Lab ID", "Condition", "Sample ID"]].to_string(index=False))
        return 1

    barcode = parsed[1].astype(int)
    condition = parsed[2]

    meta = pd.DataFrame({
        "sample_id": xl["Lab ID"],
        "original_sample_id": xl["Lab ID"],
        "round": round_from_type,
        "barcode": barcode,
        "barcode_label": barcode.map(lambda b: f"barcode{b:02d}"),
        "condition": condition,
        "cohort": xl["Sample Type"],
        "group": xl["Treatment"],
        "swab_type": xl["Swab Type"],
        "kit": xl["Extraction Kit"],
        "dna_concentration_ng_ul": xl["DNA Conc. (ng/uL)"],
        "bam_path": [f"listeria_{r}/barcode{b:02d}_{c}.bam"
                     for r, b, c in zip(round_from_type, barcode, condition)],
        "basename": xl["Sample ID"],
        "comment": "",
    })

    dup = meta[meta.duplicated("basename", keep=False)]
    if not dup.empty:
        print(f"ERROR: duplicate basenames in built metadata:")
        print(dup.sort_values("basename").to_string(index=False))
        return 1

    OUT_CLUSTER.parent.mkdir(parents=True, exist_ok=True)
    meta.to_csv(OUT_CLUSTER, index=False)
    meta.to_csv(OUT_BACKUP, index=False)
    print(f"Wrote {OUT_CLUSTER} ({len(meta)} rows)")
    print(f"Wrote {OUT_BACKUP} ({len(meta)} rows)")

    # ---- Orphans: basenames in pipeline output with no metadata row ----
    if STRAIN_MASTER.exists():
        pipe = pd.read_csv(STRAIN_MASTER)
        pipe_names = set(pipe["basename"].dropna().unique())
        meta_names = set(meta["basename"])
        orphans = sorted(pipe_names - meta_names)
        ghosts = sorted(meta_names - pipe_names)
        print()
        print(f"Pipeline basenames:        {len(pipe_names)}")
        print(f"Metadata basenames:        {len(meta_names)}")
        print(f"Both (will join cleanly):  {len(pipe_names & meta_names)}")
        print(f"Orphans (dropped in join): {len(orphans)}")
        if orphans:
            for o in orphans:
                print(f"  - {o}")
        print(f"Ghosts  (metadata-only):   {len(ghosts)}")
        if ghosts:
            for g in ghosts:
                print(f"  - {g}")

    # ---- Coverage by round × treatment ----
    print()
    print("Coverage by round × group:")
    cov = meta.groupby(["round", "cohort", "group"]).size().reset_index(name="n")
    print(cov.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
