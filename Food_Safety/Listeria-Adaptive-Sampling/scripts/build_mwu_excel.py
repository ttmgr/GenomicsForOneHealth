#!/usr/bin/env python3
"""Build a clean, PI-friendly Excel of Mann-Whitney U results only.

Reads the combined stats table from an output round and writes
`listeria_mann_whitney_u_tests.xlsx` next to it with just the MWU rows,
grouped by figure/question, with p-values and rank-biserial effect sizes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

METRIC_LABEL = {
    "Lm % Reads": "Lm reads (%)",
    "Lm % Bases": "Lm bases (%)",
    "L. ivanovii Nr26 Proportion": "L. ivanovii Nr26 proportion",
}

FIGURE_TO_SHEET = {
    "Fig 3a.3 (AS vs N)": "AS_vs_N_sponge_perLm",
    "Fig 3a.3p (pooled AS vs N)": "AS_vs_N_sponge_pooled",
    "Fig 3b.2 (AS vs N)": "AS_vs_N_metagenomic",
    "Fig 3a.t (pairwise timepoint)": "Timepoint_pairwise",
    "Fig 3a.5 (dose)": "Dose_response_24h",
    "Fig 3b.1 (swab pairwise)": "Swab_pairwise_metagenomic",
    "Fig 3b.sp (swab pairwise N)": "Swab_pairwise_metagenomic",
    "Fig 3b.1p (pooled quasi swab)": "Swab_pairwise_quasimeta",
    "Fig 3c (kit)": "Extraction_kit",
    "Fig 3d (baseline vs time)": "Baseline_vs_time",
}

SHEET_ORDER = [
    "AS_vs_N_sponge_perLm",
    "AS_vs_N_sponge_pooled",
    "AS_vs_N_metagenomic",
    "Timepoint_pairwise",
    "Dose_response_24h",
    "Swab_pairwise_metagenomic",
    "Swab_pairwise_quasimeta",
    "Extraction_kit",
    "Baseline_vs_time",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Output round directory (expects optional/stats_all.csv inside).",
    )
    parser.add_argument(
        "--out-name",
        default="listeria_mann_whitney_u_tests.xlsx",
        help="File name for the resulting Excel workbook.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats_csv = args.output_root / "optional" / "stats_all.csv"
    if not stats_csv.exists():
        raise SystemExit(f"Missing stats file: {stats_csv}")

    raw = pd.read_csv(stats_csv)
    mwu = raw[raw["stat_name"] == "U"].copy()
    if mwu.empty:
        raise SystemExit("No Mann-Whitney U rows in stats file.")

    mwu["sheet"] = mwu["figure"].map(FIGURE_TO_SHEET)
    missing_sheet = mwu[mwu["sheet"].isna()]["figure"].dropna().unique().tolist()
    if missing_sheet:
        print(f"[warn] dropping unmapped figures: {missing_sheet}")
    mwu = mwu.dropna(subset=["sheet"]).copy()

    mwu.rename(
        columns={
            "figure": "Figure",
            "comparison": "Comparison",
            "subgroup": "Subgroup",
            "metric": "Metric",
            "n1": "n_group_1",
            "n2": "n_group_2",
            "median1": "Median_group_1",
            "median2": "Median_group_2",
            "stat": "U",
            "p": "p_value",
            "p_BH": "p_BH_adjusted",
            "effect_r": "Effect_size_r",
            "sig": "Significance_raw",
            "sig_BH": "Significance_BH",
        },
        inplace=True,
    )
    mwu["Metric_label"] = mwu["Metric"].map(METRIC_LABEL).fillna(mwu["Metric"])

    display_cols = [
        "Figure",
        "Comparison",
        "Subgroup",
        "Metric_label",
        "n_group_1",
        "n_group_2",
        "Median_group_1",
        "Median_group_2",
        "U",
        "p_value",
        "p_BH_adjusted",
        "Effect_size_r",
        "Significance_raw",
        "Significance_BH",
    ]

    # Overview: Lm % Reads only, sorted by figure order
    overview = mwu[mwu["Metric"] == "Lm % Reads"][display_cols].copy()
    overview = overview.sort_values(
        by=["Figure", "Subgroup", "Comparison"], kind="stable"
    ).reset_index(drop=True)

    out_path = args.output_root / args.out_name
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        readme = pd.DataFrame(
            {
                "field": [
                    "Effect size",
                    "Rank-biserial r",
                    "p_value",
                    "p_BH_adjusted",
                    "Significance_raw",
                    "Significance_BH",
                    "Source data",
                    "Filters",
                    "Pooling",
                ],
                "value": [
                    "Rank-biserial correlation (Kerby 2014), r = 2*U1/(n1*n2) - 1, where U1 is the Mann-Whitney U statistic (scipy default). Range [-1, 1]. |r| < 0.1 vanishingly small, 0.1-0.3 small, 0.3-0.5 medium, >= 0.5 large.",
                    "Group_1 is the LEFT side of the Comparison string, group_2 is the right side. Positive r => group_1 tends to be larger than group_2 (e.g. for 'AS vs N', positive r => AS > N). Negative r => group_2 > group_1.",
                    "Two-sided Mann-Whitney U test, raw p-value.",
                    "Benjamini-Hochberg adjusted p-value within each figure/question.",
                    "Stars based on raw p: *** p<0.001, ** p<0.01, * p<0.05, ns p>=0.05.",
                    "Stars based on BH-adjusted p (same thresholds).",
                    f"{stats_csv.name} generated by analyze_listeria.py.",
                    "Blank/Background samples excluded; samples without a valid swab type excluded. N = Native, AS = Adaptive Sampling.",
                    "Tests are run per Lm spiking concentration (Lm2/Lm4/Lm6) where indicated, and additionally pooled across Lm2/4/6 where indicated in the Subgroup column ('Lm pooled').",
                ],
            }
        )
        readme.to_excel(xw, sheet_name="README", index=False)

        overview.to_excel(xw, sheet_name="Overview_Lm_percent_reads", index=False)

        for sheet in SHEET_ORDER:
            sub = mwu[mwu["sheet"] == sheet][display_cols].copy()
            if sub.empty:
                continue
            sub = sub.sort_values(
                by=["Metric_label", "Subgroup", "Comparison"], kind="stable"
            ).reset_index(drop=True)
            sub.to_excel(xw, sheet_name=sheet, index=False)
            print(f"[sheet] {sheet}: {len(sub)} rows")

    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
