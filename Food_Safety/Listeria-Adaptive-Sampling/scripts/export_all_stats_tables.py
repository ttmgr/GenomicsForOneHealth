"""Export consolidated statistical test outputs and methods markdown.

Writes:
- outputs/publication_v4/listeria_all_statistical_tests.csv
- outputs/publication_v4/methods.md
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import date
from pathlib import Path

import pandas as pd

from listeria_pipeline_common import (
    DEFAULT_INPUT_PATH,
    DEFAULT_INPUT_SHEET,
    DEFAULT_OUTPUT_ROOT,
    ROOT,
    build_pipeline_paths,
    format_input_label,
)

INPUT_STATS = DEFAULT_OUTPUT_ROOT / "optional" / "stats_all.csv"
OUTPUT_DIR = DEFAULT_OUTPUT_ROOT / "publication_v4"
OUTPUT_CSV = OUTPUT_DIR / "listeria_all_statistical_tests.csv"
OUTPUT_MD = OUTPUT_DIR / "methods.md"
SOURCE_INPUT = DEFAULT_INPUT_PATH
SOURCE_SHEET = DEFAULT_INPUT_SHEET

PLOT_DESCRIPTIONS = OrderedDict(
    [
        ("fig1_quasimeta_AS_vs_N", "Sponge quasimetagenomic Lm % reads, pooled Lm2-Lm6, AS versus N."),
        ("fig2_quasimeta_timecourse_N", "Sponge N-only Lm % reads over time with metagenomic baseline as 0 h."),
        ("fig3_metagenomic_AS_vs_N", "Metagenomic Lm % reads by swab type, AS versus N."),
        ("fig4_metagenomic_swab_comparison_N", "Metagenomic N-only Lm % reads compared across swab types."),
        ("fig5_combined_panel", "Combined panel with sponge time-course at left and metagenomic swab comparison at right."),
        ("fig6_total_reads_by_approach", "Total sequencing reads by approach, with AS and N shown side by side."),
        ("fig7_total_bases_by_approach", "Total sequencing bases by approach, with AS and N shown side by side."),
        ("fig8_total_reads_by_extraction_kit", "Total sequencing reads by approach, grouped by extraction kit."),
        ("fig9_total_bases_by_extraction_kit", "Total sequencing bases by approach, grouped by extraction kit."),
        ("fig10_lm_total_reads_by_approach", "Lm-mapped reads by approach, with AS and N shown side by side."),
        ("fig11_lm_total_bases_by_approach", "Lm-mapped bases by approach, with AS and N shown side by side."),
        ("fig12_lm_mean_read_length_by_approach", "Mean read length of Lm-mapped reads by approach, with AS and N shown side by side."),
        ("fig13_lm_detected_strains_by_approach", "Mean number of detected Lm strains by approach, with AS and N shown side by side."),
        ("fig14_ivanovii_reads_by_approach", "L. ivanovii read counts by approach, with AS and N shown side by side."),
        ("fig15_ivanovii_proportion_by_approach", "L. ivanovii proportion by approach, with AS and N shown side by side."),
    ]
)

FIGURE_DESCRIPTIONS = OrderedDict(
    [
        (
            "Fig 3a.1 (trend)",
            "Per-treatment Spearman trend tests across sponge N timepoints.",
        ),
        (
            "Fig 3a.1p (pooled trend)",
            "Pooled Spearman trend tests across sponge N timepoints with Lm2/Lm4/Lm6 combined.",
        ),
        (
            "Fig 3a.3 (AS vs N)",
            "Sponge quasimetagenomic AS-vs-N comparisons stratified by timepoint and treatment.",
        ),
        (
            "Fig 3a.3p (pooled AS vs N)",
            "Sponge quasimetagenomic AS-vs-N comparisons with Lm2/Lm4/Lm6 pooled.",
        ),
        (
            "Fig 3a.5 (dose)",
            "Dose comparisons among Lm2, Lm4, and Lm6 at pooled 24 h in sponge N samples.",
        ),
        (
            "Fig 3b.1 (swab KW)",
            "Metagenomic N-only omnibus swab-type comparisons using Kruskal-Wallis.",
        ),
        (
            "Fig 3b.1 (swab pairwise)",
            "Metagenomic N-only pairwise swab-type comparisons.",
        ),
        (
            "Fig 3b.1p (pooled quasi swab)",
            "Quasimetagenomic N-only pooled swab-type comparisons with Lm2/Lm4/Lm6 combined.",
        ),
        (
            "Fig 3b.2 (AS vs N)",
            "Metagenomic AS-vs-N comparisons stratified by swab type.",
        ),
        (
            "Fig 3c (kit)",
            "Quasimetagenomic N-only Micro-vs-Mini extraction-kit comparisons, pooled and within swab type.",
        ),
        (
            "Fig 3d (baseline vs time)",
            "Sponge N-only pooled comparisons of metagenomic baseline versus later quasimetagenomic timepoints.",
        ),
    ]
)

TEST_TYPE_MAP = {
    "U": "Mann-Whitney U",
    "H": "Kruskal-Wallis",
    "rho": "Spearman correlation",
}

TEST_TYPE_ORDER = {
    "Mann-Whitney U": 0,
    "Kruskal-Wallis": 1,
    "Spearman correlation": 2,
}


def configure_paths(
    output_root: str | Path | None = None,
    source_input: str | Path | None = None,
    source_sheet: str = DEFAULT_INPUT_SHEET,
) -> None:
    global INPUT_STATS, OUTPUT_DIR, OUTPUT_CSV, OUTPUT_MD, SOURCE_INPUT, SOURCE_SHEET

    paths = build_pipeline_paths(output_root=output_root)
    INPUT_STATS = paths.optional_dir / "stats_all.csv"
    OUTPUT_DIR = paths.publication_dir
    OUTPUT_CSV = OUTPUT_DIR / "listeria_all_statistical_tests.csv"
    OUTPUT_MD = OUTPUT_DIR / "methods.md"
    SOURCE_INPUT = Path(source_input or DEFAULT_INPUT_PATH)
    SOURCE_SHEET = source_sheet


def display_path(path: Path) -> str:
    candidate = path.resolve() if not path.is_absolute() else path
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return str(candidate)


def derive_groups(row: pd.Series) -> tuple[str, str]:
    comparison = str(row["comparison"])
    figure = str(row["figure"])
    stat_name = str(row["stat_name"])

    if stat_name != "U":
        return "", ""
    if comparison.startswith("Micro vs Mini"):
        return "Micro", "Mini"
    if comparison.startswith("0h vs "):
        return "0h", comparison.replace("0h vs ", "", 1).strip()
    if comparison.endswith(" (N only)"):
        left, right = comparison.replace(" (N only)", "").split(" vs ", 1)
        return left.strip(), right.strip()
    if " vs " in comparison:
        left, right = comparison.split(" vs ", 1)
        return left.strip(), right.strip()
    return "", ""


def build_csv() -> pd.DataFrame:
    df = pd.read_csv(INPUT_STATS)
    df["test_type"] = df["stat_name"].map(TEST_TYPE_MAP).fillna(df["stat_name"])
    df["figure_description"] = df["figure"].map(FIGURE_DESCRIPTIONS).fillna("")

    groups = df.apply(derive_groups, axis=1, result_type="expand")
    df["group_1"] = groups[0]
    df["group_2"] = groups[1]

    df["figure_order"] = df["figure"].map({k: i for i, k in enumerate(FIGURE_DESCRIPTIONS)})
    df["test_order"] = df["test_type"].map(TEST_TYPE_ORDER).fillna(99)
    df = df.sort_values(["figure_order", "test_order", "metric", "comparison", "subgroup"]).drop(
        columns=["figure_order", "test_order"]
    )

    cols = [
        "figure",
        "figure_description",
        "test_type",
        "comparison",
        "subgroup",
        "metric",
        "group_1",
        "group_2",
        "n1",
        "n2",
        "median1",
        "median2",
        "stat_name",
        "stat",
        "p",
        "p_BH",
        "sig",
        "sig_BH",
    ]
    out = df[cols].copy()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)
    return out


def methods_markdown(df: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("# Methods")
    lines.append("")
    lines.append(f"Generated on {date.today().isoformat()}.")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- CSV table: `{display_path(OUTPUT_CSV)}`")
    lines.append(f"- Source combined stats table: `{display_path(INPUT_STATS)}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"This package summarizes all {len(df)} statistical test rows exported from the Listeria analysis pipeline."
    )
    lines.append("")

    counts = df["test_type"].value_counts()
    for test_name in ["Mann-Whitney U", "Kruskal-Wallis", "Spearman correlation"]:
        lines.append(f"- {test_name}: {int(counts.get(test_name, 0))} tests")
    lines.append("")

    lines.append("## Data Source And Preprocessing")
    lines.append("")
    lines.append(f"- Primary input file: `{format_input_label(SOURCE_INPUT, SOURCE_SHEET)}`.")
    lines.append(
        "- The analysis pipeline in `scripts/analyze_listeria.py` cleaned headers, parsed numeric columns, mapped `Sample Type` to timepoint labels, and added an `included_in_analysis` flag."
    )
    lines.append(
        "- Rows with `Treatment` equal to `Blank` or `Background` were retained in the master workbook for record-keeping but excluded from all downstream statistics and plots."
    )
    lines.append(
        "- Metagenomic rows were not forced into a synthetic `Baseline` treatment. Source treatment labels were preserved in the master table when present."
    )
    lines.append(
        "- The main time-course analyses still pooled metagenomic samples as the shared `0h` baseline, while `quasimeta_24h_1` and `quasimeta_24h_2` were either shown separately or pooled depending on the figure family."
    )
    lines.append(
        "- The source dataset contains `L. ivanovii Nr26 Reads` and `L. ivanovii Nr26 Proportion`, but it does not contain ivanovii-specific bases or ivanovii-specific mean read length columns."
    )
    lines.append("")

    lines.append("## Metrics Tested")
    lines.append("")
    for metric in df["metric"].dropna().drop_duplicates().tolist():
        lines.append(f"- `{metric}`")
    lines.append("")
    lines.append("- Additional publication_v4 summary plots also use raw columns such as `Lm Total Reads (4 strains)`, `Lm Total Bases`, `Lm Mean Read Length`, `# Lm Strains Detected`, and `L. ivanovii Nr26 Reads`.")
    lines.append("")

    lines.append("## Statistical Tests")
    lines.append("")
    lines.append(
        "- `Mann-Whitney U`: two-sided non-parametric pairwise comparisons computed with `scipy.stats.mannwhitneyu(a, b, alternative='two-sided')` after dropping missing values."
    )
    lines.append(
        "- `Kruskal-Wallis`: omnibus non-parametric tests across three groups when a multi-group comparison was needed."
    )
    lines.append(
        "- `Spearman correlation`: monotonic trend tests against a timepoint index for time-course analyses."
    )
    lines.append("")

    lines.append("## Multiple Testing Correction")
    lines.append("")
    lines.append(
        "- `p` is the raw p-value from the specific test."
    )
    lines.append(
        "- `p_BH` is the Benjamini-Hochberg adjusted p-value stored by the original analysis pipeline."
    )
    lines.append(
        "- Important: `p_BH` was adjusted within the original analysis families in `scripts/analyze_listeria.py` before concatenation into the combined table. It is not a fresh single correction across all rows in this CSV."
    )
    lines.append(
        "- `sig` is the raw-p significance label; `sig_BH` is the BH-adjusted significance label."
    )
    lines.append(
        "- Significance thresholds: `***` < 0.001, `**` < 0.01, `*` < 0.05, `ns` otherwise."
    )
    lines.append("")

    lines.append("## CSV Column Guide")
    lines.append("")
    lines.append("- `figure`: figure family or analysis block from the original pipeline.")
    lines.append("- `figure_description`: short plain-language description of that figure family.")
    lines.append("- `test_type`: human-readable test class.")
    lines.append("- `comparison`: named comparison from the original output.")
    lines.append("- `subgroup`: stratum within the figure family.")
    lines.append("- `metric`: response variable tested.")
    lines.append("- `group_1`, `group_2`: parsed pairwise groups for Mann-Whitney U rows; blank for omnibus or correlation tests.")
    lines.append("- `n1`, `n2`: sample counts carried from the original output. For omnibus and correlation rows, `n2` can be `0`.")
    lines.append("- `median1`, `median2`: medians reported by the original pipeline. These are primarily meaningful for pairwise comparisons.")
    lines.append("- `stat_name`: raw statistic identifier (`U`, `H`, or `rho`).")
    lines.append("- `stat`: numeric test statistic.")
    lines.append("- `p`: raw p-value.")
    lines.append("- `p_BH`: BH-adjusted p-value from the original analysis family.")
    lines.append("- `sig`, `sig_BH`: significance labels based on `p` and `p_BH`.")
    lines.append("")

    lines.append("## Publication Figure Outputs")
    lines.append("")
    lines.append(
        "The `outputs/publication_v4/` folder also contains the current publication-style plots in PNG, PDF, and SVG formats."
    )
    lines.append("")
    for stem, description in PLOT_DESCRIPTIONS.items():
        lines.append(f"- `{stem}`: {description}")
    lines.append("")

    lines.append("## Plotting Conventions")
    lines.append("")
    lines.append("- Boxplots are used for distribution-style comparisons and include overlaid individual sample points.")
    lines.append("- Summary bar plots do not show individual sample points or whiskers/error bars.")
    lines.append("- Summary plots labeled with `Total` use summed values within each plotted group.")
    lines.append("- Summary plots for read length, detected-strain count, and ivanovii proportion use group means.")
    lines.append("- Current publication_v4 figures use a `14 x 10` inch canvas by default.")
    lines.append("")

    lines.append("## Figure Families Included")
    lines.append("")
    for fig_name, description in FIGURE_DESCRIPTIONS.items():
        sub = df[df["figure"] == fig_name]
        if sub.empty:
            continue
        lines.append(f"- `{fig_name}`: {description} ({len(sub)} rows)")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- For pairwise Mann-Whitney U rows, `group_1` is the left side of the `comparison` string and `group_2` is the right side (e.g. `AS vs N` => group_1 = AS, group_2 = N). `median1`/`median2` and the rank-biserial effect size `r` follow the same order: positive `r` means group_1 tends to have larger values than group_2."
    )
    lines.append(
        "- This methods file describes the exported statistics package; it does not replace the figure-by-figure narrative interpretation."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    configure_paths(
        output_root=args.output_root,
        source_input=args.source_input,
        source_sheet=args.source_sheet,
    )
    df = build_csv()
    OUTPUT_MD.write_text(methods_markdown(df))
    print(f"Saved {OUTPUT_CSV}")
    print(f"Saved {OUTPUT_MD}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the consolidated Listeria statistics CSV and methods markdown."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root output directory containing optional/stats_all.csv and publication_v4/.",
    )
    parser.add_argument(
        "--source-input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Original input data file used for the analysis run.",
    )
    parser.add_argument(
        "--source-sheet",
        default=DEFAULT_INPUT_SHEET,
        help="Worksheet name for XLSX source inputs. Ignored for CSV.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
