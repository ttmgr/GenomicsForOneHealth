#!/usr/bin/env python3
"""
Step 82: Aggregate expanded (background-aware) competitive mapping results.

Reads strain_results_5.tsv (produced by step 81), joins with sample_metadata.csv,
and produces summary tables. Separates L. mono strains, non-mono Listeria,
and background species (e.g. Bacillus) into three tiers so that background
reads no longer inflate Listeria percentages downstream.

Usage (cluster):  sbatch scripts/82_strain_summary_background.sh
Usage (local):    WORK_DIR=downloaded_results python scripts/82_strain_summary_background.py
"""

import os
import sys
from pathlib import Path

import pandas as pd

# ---- Paths ----
WORK_DIR = Path(os.environ.get("WORK_DIR", "downloaded_results"))
STRAIN_DIR = WORK_DIR / "processing" / "strain_analysis"
RESULTS_TSV = STRAIN_DIR / "strain_results_5.tsv"
OUT_DIR = STRAIN_DIR

METADATA_CANDIDATES = [
    WORK_DIR / "samplesheets" / "sample_metadata.csv",
    Path(__file__).resolve().parent.parent / "data" / "sample_metadata.csv",
]

NEGATIVE_CONTROL_PREFIX = "S13_S14"

# L. mono strains vs non-mono Listeria vs background
LMONO_STRAINS = {"EGDe", "LL195", "LMNC326", "N13-0119"}
NON_MONO_SPECIES = {"L_innocua_J5051", "L_ivanovii_Nr26", "L_welshimeri_Nr14"}
BACKGROUND_SPECIES = {
    "E_coli",
    "P_mirabilis",
    "Y_enterocolitica",
    "Y_frederiksenii",
    "S_aureus",
    "R_equi",
    "P_aeruginosa",
}


def classify(strain: str) -> str:
    if strain in LMONO_STRAINS:
        return "L_monocytogenes"
    if strain in NON_MONO_SPECIES:
        return "non_mono"
    if strain in BACKGROUND_SPECIES:
        return "background"
    return "unknown"


def find_metadata():
    for p in METADATA_CANDIDATES:
        if p.exists():
            return p
    return None


def _summary_by_condition(df_subset: pd.DataFrame) -> pd.DataFrame:
    return (
        df_subset
        .groupby(["strain", "condition"])
        .agg(
            n_samples=("basename", "nunique"),
            mean_proportion=("proportion", "mean"),
            std_proportion=("proportion", "std"),
            mean_coverage_breadth=("coverage_breadth_pct", "mean"),
            mean_depth=("mean_depth", "mean"),
            mean_mapq=("mean_mapq", "mean"),
            total_mapped_reads=("mapped_reads", "sum"),
        )
        .reset_index()
        .sort_values(["strain", "condition"])
    )


def main():
    # ---- Load data ----
    if not RESULTS_TSV.exists():
        print(f"ERROR: Results file not found: {RESULTS_TSV}")
        sys.exit(1)

    df = pd.read_csv(RESULTS_TSV, sep="\t")
    print(f"Loaded {len(df)} rows from {RESULTS_TSV}")
    print(f"Samples: {df['basename'].nunique()}, Strains: {df['strain'].nunique()}")
    print(f"Strains found: {', '.join(sorted(df['strain'].unique()))}")
    print()

    df["species_group"] = df["strain"].apply(classify)
    unknown_mask = df["species_group"] == "unknown"
    if unknown_mask.any():
        unknowns = sorted(df.loc[unknown_mask, "strain"].unique())
        print(
            f"WARNING: {unknown_mask.sum()} rows with unknown strain labels: "
            f"{', '.join(unknowns)}. Update LMONO_STRAINS / NON_MONO_SPECIES / "
            f"BACKGROUND_SPECIES in this script."
        )
        print()

    # ---- Separate negative control ----
    is_control = df["basename"].str.startswith(NEGATIVE_CONTROL_PREFIX)
    df_control = df[is_control].copy()
    df_samples = df[~is_control].copy()

    # ---- Join with metadata ----
    meta_path = find_metadata()
    if meta_path:
        print(f"Using metadata: {meta_path}")
        meta = pd.read_csv(meta_path)
        meta_cols = ["basename", "round", "condition", "cohort", "group",
                     "swab_type", "kit", "dna_concentration_ng_ul"]
        available_cols = [c for c in meta_cols if c in meta.columns]
        meta_subset = meta[available_cols].drop_duplicates(subset=["basename"])
        df_samples = df_samples.merge(meta_subset, on="basename", how="left")
    else:
        print("WARNING: No metadata file found, skipping join.")

    # ---- Master table ----
    out_master = OUT_DIR / "strain_proportions_master_5.csv"
    df_samples.to_csv(out_master, index=False)
    print(f"Written: {out_master} ({len(df_samples)} rows)")

    # ---- Summaries by condition (per tier) ----
    tier_outputs = {
        "L_monocytogenes": OUT_DIR / "strain_summary_by_condition_5.csv",
        "non_mono":        OUT_DIR / "nonmono_summary_by_condition_5.csv",
        "background":      OUT_DIR / "background_summary_by_condition_5.csv",
    }

    for tier, out_path in tier_outputs.items():
        df_tier = df_samples[df_samples["species_group"] == tier]
        if "condition" not in df_tier.columns or len(df_tier) == 0:
            continue
        summary = _summary_by_condition(df_tier)
        summary.to_csv(out_path, index=False)
        print(f"Written: {out_path}")

        print(f"\n=== {tier} by condition ===")
        for strain in sorted(summary["strain"].unique()):
            print(f"\n  {strain}:")
            for _, row in summary[summary["strain"] == strain].iterrows():
                print(
                    f"    {row['condition']:3s}: "
                    f"proportion={row['mean_proportion']:.4f} +/- {row['std_proportion']:.4f}, "
                    f"breadth={row['mean_coverage_breadth']:.1f}%, "
                    f"depth={row['mean_depth']:.1f}x, "
                    f"MAPQ={row['mean_mapq']:.0f} "
                    f"(n={row['n_samples']})"
                )

    # ---- Negative control (mismapping) ----
    if len(df_control) > 0:
        out_control = OUT_DIR / "mismapping_control_5.csv"
        df_control.to_csv(out_control, index=False)
        print(f"\nWritten: {out_control}")

        print("\n=== Negative control (mismapping estimate) ===")
        print(f"Sample(s): {sorted(df_control['basename'].unique())}")

        total_ctrl_reads = df_control["mapped_reads"].sum()
        if total_ctrl_reads > 0:
            for tier in ["L_monocytogenes", "non_mono", "background"]:
                tier_reads = df_control.loc[
                    df_control["species_group"] == tier, "mapped_reads"
                ].sum()
                pct = tier_reads / total_ctrl_reads
                print(f"  {tier:18s}: {tier_reads} reads ({pct:.1%})")

            print("\nPer-strain breakdown:")
            for tier in ["L_monocytogenes", "non_mono", "background"]:
                rows = df_control[df_control["species_group"] == tier]
                if rows.empty:
                    continue
                print(f"  {tier}:")
                for _, row in rows.iterrows():
                    print(
                        f"    {row['strain']}: "
                        f"{row['mapped_reads']} reads ({row['proportion']:.4%}), "
                        f"breadth={row['coverage_breadth_pct']:.2f}%, "
                        f"depth={row['mean_depth']:.2f}x, "
                        f"MAPQ={row['mean_mapq']:.1f}"
                    )
    else:
        print("\nNo negative control samples found (prefix: S13_S14).")

    print("\nDone.")


if __name__ == "__main__":
    main()
