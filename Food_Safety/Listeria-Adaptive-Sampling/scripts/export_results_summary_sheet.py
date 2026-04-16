#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from listeria_pipeline_common import DEFAULT_OUTPUT_ROOT

AS_VS_N_FIGURES = {
    "Fig 3a.3 (AS vs N)",
    "Fig 3b.2 (AS vs N)",
    "Fig 3a.3p (pooled AS vs N)",
}

FIGURE_DESCRIPTIONS = {
    "Fig 3a.3 (AS vs N)": "Sponge quasimetagenomic AS vs N by timepoint and treatment",
    "Fig 3b.2 (AS vs N)": "Metagenomic AS vs N by swab type",
    "Fig 3a.3p (pooled AS vs N)": "Sponge quasimetagenomic AS vs N with Lm pooled",
    "Fig 3a.1 (trend)": "Sponge N-only time-course trends by treatment",
    "Fig 3a.5 (dose)": "Sponge N-only 24h dose comparisons",
    "Fig 3b.1 (swab KW)": "Metagenomic N-only swab omnibus tests",
    "Fig 3b.1 (swab pairwise)": "Metagenomic N-only swab pairwise tests",
    "Fig 3c (kit)": "Quasimetagenomic N-only extraction kit comparisons",
    "Fig 3a.1p (pooled trend)": "Sponge N-only pooled time-course trend",
    "Fig 3d (baseline vs time)": "Sponge N-only baseline versus later timepoints",
    "Fig 3b.1p (pooled quasi swab)": "Quasimetagenomic N-only pooled swab comparisons",
}

FIGURE_ORDER = {name: i for i, name in enumerate(FIGURE_DESCRIPTIONS)}
METRIC_ORDER = {"Lm % Reads": 0, "Lm % Bases": 1, "L. ivanovii Nr26 Proportion": 2}


def add_scope(stats: pd.DataFrame) -> pd.DataFrame:
    out = stats.copy()
    out["scope"] = out["figure"].isin(AS_VS_N_FIGURES).map({True: "AS vs N", False: "N only"})
    out["figure_description"] = out["figure"].map(FIGURE_DESCRIPTIONS).fillna("")
    return out


def build_scope_overview(stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, sub in stats.groupby("scope", sort=False):
        rows.append(
            {
                "scope": scope,
                "what_was_tested": (
                    "Adaptive Sampling versus Native comparisons"
                    if scope == "AS vs N"
                    else "Analyses restricted to Native samples only"
                ),
                "test_rows": len(sub),
                "raw_significant_rows": int((sub["p"] < 0.05).sum()),
                "bh_significant_rows": int((sub["p_BH"] < 0.05).sum()),
                "headline": (
                    "No AS-vs-N result stayed significant after correction"
                    if scope == "AS vs N"
                    else "Multiple N-only findings stayed significant after correction"
                ),
            }
        )
    return pd.DataFrame(rows)


def build_figure_metric_summary(stats: pd.DataFrame) -> pd.DataFrame:
    summary = (
        stats.groupby(["scope", "figure", "figure_description", "metric"], sort=False)
        .agg(
            tests=("figure", "size"),
            raw_significant=("p", lambda s: int((s < 0.05).sum())),
            bh_significant=("p_BH", lambda s: int((s < 0.05).sum())),
        )
        .reset_index()
    )
    summary["interpretation"] = summary.apply(
        lambda row: (
            "No evidence of AS benefit"
            if row["scope"] == "AS vs N" and row["bh_significant"] == 0
            else (
                "BH-significant N-only finding(s)"
                if row["scope"] == "N only" and row["bh_significant"] > 0
                else "No BH-significant finding"
            )
        ),
        axis=1,
    )
    summary["figure_order"] = summary["figure"].map(FIGURE_ORDER).fillna(999)
    summary["metric_order"] = summary["metric"].map(METRIC_ORDER).fillna(999)
    return summary.sort_values(["scope", "figure_order", "metric_order"]).drop(
        columns=["figure_order", "metric_order"]
    )


def build_bh_significant(stats: pd.DataFrame) -> pd.DataFrame:
    sig = stats[stats["p_BH"] < 0.05].copy()
    sig["figure_order"] = sig["figure"].map(FIGURE_ORDER).fillna(999)
    sig["metric_order"] = sig["metric"].map(METRIC_ORDER).fillna(999)
    cols = [
        "scope",
        "figure",
        "figure_description",
        "comparison",
        "subgroup",
        "metric",
        "p",
        "p_BH",
        "sig_BH",
    ]
    return sig.sort_values(["scope", "figure_order", "metric_order", "comparison", "subgroup"])[cols]


def write_markdown(
    output_path: Path,
    scope_overview: pd.DataFrame,
    summary: pd.DataFrame,
    bh_significant: pd.DataFrame,
) -> None:
    lines = ["# Results Summary", ""]
    lines.append("## Scope Overview")
    lines.append("")
    lines.append(scope_overview.to_markdown(index=False))
    lines.append("")
    lines.append("## Figure And Metric Summary")
    lines.append("")
    lines.append(summary.to_markdown(index=False))
    lines.append("")
    lines.append("## BH-Significant Findings")
    lines.append("")
    if bh_significant.empty:
        lines.append("No BH-significant findings.")
    else:
        lines.append(bh_significant.to_markdown(index=False))
    lines.append("")
    output_path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a compact results summary sheet from stats_all.csv."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Run-specific output root containing optional/stats_all.csv and listeria_final_table.xlsx.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = args.output_root
    stats_path = output_root / "optional" / "stats_all.csv"
    workbook_path = output_root / "listeria_final_table.xlsx"
    markdown_path = output_root / "publication_v4" / "results_summary.md"

    stats = pd.read_csv(stats_path)
    stats = add_scope(stats)
    scope_overview = build_scope_overview(stats)
    summary = build_figure_metric_summary(stats)
    bh_significant = build_bh_significant(stats)

    with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        scope_overview.to_excel(writer, sheet_name="results_scope_overview", index=False)
        summary.to_excel(writer, sheet_name="results_summary", index=False)
        bh_significant.to_excel(writer, sheet_name="bh_significant_findings", index=False)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(markdown_path, scope_overview, summary, bh_significant)

    print(f"Saved sheets to {workbook_path}")
    print(f"Saved {markdown_path}")


if __name__ == "__main__":
    main()
