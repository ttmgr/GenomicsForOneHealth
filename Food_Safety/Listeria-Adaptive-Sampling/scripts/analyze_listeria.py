"""Listeria metagenomics: build final Excel table, stats, and publication figures.

Runs end-to-end from `listeria_reads.csv` and writes to `outputs/`.
"""

from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats

from listeria_pipeline_common import (
    ALL_STRAINS,
    CONDITION_ORDER,
    DEFAULT_INPUT_PATH,
    DEFAULT_INPUT_SHEET,
    DEFAULT_OUTPUT_ROOT,
    LM_STRAINS,
    OTHER_STRAINS,
    ROOT,
    SWAB_ORDER,
    TIMEPOINT_DISPLAY_ORDER,
    TIMEPOINT_ORDER,
    TREATMENT_ORDER,
    build_pipeline_paths,
    describe_filtering,
    load_listeria_data,
)

INPUT_PATH = DEFAULT_INPUT_PATH
INPUT_SHEET = DEFAULT_INPUT_SHEET
OUT = DEFAULT_OUTPUT_ROOT
OUT_OPTIONAL = OUT / "optional"
OUT.mkdir(exist_ok=True)
OUT_OPTIONAL.mkdir(exist_ok=True)

# Colourblind-safe palette (Okabe-Ito); condition pair chosen to stay
# distinguishable in grayscale (blue desaturates dark, orange desaturates mid).
PALETTE_TREATMENT = {"Lm2": "#0072B2", "Lm4": "#009E73", "Lm6": "#D55E00"}
PALETTE_CONDITION = {"N": "#0072B2", "AS": "#D55E00"}
PALETTE_SWAB = {"Sponge": "#0072B2", "Cotton": "#E69F00", "Zymo": "#009E73"}
CONDITION_MARKERS = {"N": "o", "AS": "^"}  # redundant encoding for grayscale
# Okabe-Ito + one extra, colourblind-safe for four L. monocytogenes strains.
PALETTE_LM_STRAIN = {
    "EGDe":     "#0072B2",   # blue
    "LL195":    "#D55E00",   # vermillion
    "LMNC326":  "#009E73",   # bluish green
    "N13-0119": "#CC79A7",   # reddish purple
}
LM_STRAIN_MARKERS = {
    "EGDe":     "o",
    "LL195":    "s",
    "LMNC326":  "D",
    "N13-0119": "^",
}


def _set_style() -> None:
    sns.set_theme(style="ticks", context="paper")
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


# --------------------------------------------------------------------------------------
# 1. Load + clean
# --------------------------------------------------------------------------------------
def configure_paths(
    input_path: str | Path | None = None,
    sheet_name: str = DEFAULT_INPUT_SHEET,
    output_root: str | Path | None = None,
) -> None:
    global INPUT_PATH, INPUT_SHEET, OUT, OUT_OPTIONAL

    paths = build_pipeline_paths(input_path=input_path, sheet_name=sheet_name, output_root=output_root)
    INPUT_PATH = paths.input_path
    INPUT_SHEET = paths.sheet_name
    OUT = paths.output_root
    OUT_OPTIONAL = paths.optional_dir
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_OPTIONAL.mkdir(parents=True, exist_ok=True)


def load_clean() -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows, analysis_df = load_listeria_data(INPUT_PATH, INPUT_SHEET)
    print(f"[load] {describe_filtering(all_rows, analysis_df)}")

    lm_sum = analysis_df[[f"{s} Reads" for s in LM_STRAINS]].sum(axis=1)
    diff = (lm_sum - analysis_df["Lm Total Reads (4 strains)"]).abs()
    if (diff > 1).any():
        bad = analysis_df.loc[diff > 1, ["Lab ID", "Sample Type", "Condition"]]
        warnings.warn(f"Lm strain reads disagree with Lm total for {len(bad)} rows")

    total_mapped = analysis_df[[f"{s} Reads" for s in ALL_STRAINS]].sum(axis=1)
    overreach = (total_mapped - analysis_df["Total Reads"]).gt(1)
    if overreach.any():
        warnings.warn(
            f"{int(overreach.sum())} rows have per-strain mapped > Total Reads (reads may map to >1 strain)"
        )

    return all_rows, analysis_df


# --------------------------------------------------------------------------------------
# 2. Excel table
# --------------------------------------------------------------------------------------
def build_excel(all_rows: pd.DataFrame, analysis_df: pd.DataFrame) -> None:
    out_path = OUT / "listeria_final_table.xlsx"

    samples_cols = [
        "Sample Type",
        "timepoint",
        "timepoint_display",
        "Treatment",
        "Swab Type",
        "Lab ID",
        "Condition",
        "included_in_analysis",
        "Extraction Kit",
        "DNA Conc. (ng/uL)",
        "Total Reads",
        "Total Bases",
        "Mean Read Length",
        "Mean Read Quality",
        "Lm Total Reads (4 strains)",
        "Lm Total Bases",
        "Lm Mean Read Length",
        "Lm % Reads",
        "Lm % Bases",
        "# Lm Strains Detected",
        "Detected Strains",
        "Dominant Lm Strain",
        "L. innocua J5051 Reads",
        "L. innocua J5051 Proportion",
        "L. ivanovii Nr26 Reads",
        "L. ivanovii Nr26 Proportion",
        "L. welshimeri Nr14 Reads",
        "L. welshimeri Nr14 Proportion",
    ]
    all_rows_sheet = all_rows.sort_values(
        ["timepoint", "Swab Type", "Lab ID", "Treatment", "Condition"]
    ).copy()
    analysis_only = analysis_df.sort_values(
        ["timepoint", "Swab Type", "Lab ID", "Treatment", "Condition"]
    ).copy()
    all_rows_sheet = all_rows_sheet[samples_cols]
    analysis_only = analysis_only[samples_cols]

    samples = analysis_only.copy()
    samples_cols = [
        "Sample Type",
        "timepoint",
        "timepoint_display",
        "Treatment",
        "Swab Type",
        "Lab ID",
        "Condition",
        "included_in_analysis",
        "Extraction Kit",
        "DNA Conc. (ng/uL)",
        "Total Reads",
        "Total Bases",
        "Mean Read Length",
        "Mean Read Quality",
        "Lm Total Reads (4 strains)",
        "Lm Total Bases",
        "Lm Mean Read Length",
        "Lm % Reads",
        "Lm % Bases",
        "# Lm Strains Detected",
        "Detected Strains",
        "Dominant Lm Strain",
        "L. innocua J5051 Reads",
        "L. innocua J5051 Proportion",
        "L. ivanovii Nr26 Reads",
        "L. ivanovii Nr26 Proportion",
        "L. welshimeri Nr14 Reads",
        "L. welshimeri Nr14 Proportion",
    ]
    samples = samples[samples_cols]

    # Long per-strain table
    rows = []
    for _, r in analysis_df.iterrows():
        for strain in ALL_STRAINS:
            rows.append(
                {
                    "Sample Type": r["Sample Type"],
                    "timepoint": r["timepoint"],
                    "Treatment": r["Treatment"],
                    "Swab Type": r["Swab Type"],
                    "Lab ID": r["Lab ID"],
                    "Condition": r["Condition"],
                    "strain": strain,
                    "strain_group": "Lm" if strain in LM_STRAINS else "Other",
                    "reads": r[f"{strain} Reads"],
                    "proportion_of_Lm_or_group": r[f"{strain} Proportion"],
                    "pct_of_total_reads": 100.0
                    * r[f"{strain} Reads"]
                    / max(r["Total Reads"], 1),
                }
            )
    per_strain = pd.DataFrame(rows)

    excluded_rows = len(all_rows_sheet) - len(analysis_only)
    readme = pd.DataFrame(
        [
            {
                "field": "source_input",
                "value": str(INPUT_PATH),
                "notes": "Canonical source for this run.",
            },
            {
                "field": "source_sheet",
                "value": INPUT_SHEET if INPUT_PATH.suffix.lower() in {".xlsx", ".xls"} else "",
                "notes": "Excel sheet name used for workbook inputs.",
            },
            {
                "field": "all_rows_sheet",
                "value": len(all_rows_sheet),
                "notes": "All source rows retained exactly for record-keeping.",
            },
            {
                "field": "analysis_only_sheet",
                "value": len(analysis_only),
                "notes": "Only rows with included_in_analysis = True feed stats and figures.",
            },
            {
                "field": "excluded_rows",
                "value": excluded_rows,
                "notes": "Rows excluded from analyses because Treatment is Blank or Background.",
            },
            {
                "field": "included_in_analysis",
                "value": "False for Blank/Background; True otherwise",
                "notes": "Explicit analysis flag carried in the table sheets.",
            },
            {
                "field": "timepoint",
                "value": "0h / 4h / 12h / 24h (1) / 24h (2)",
                "notes": "Internal timepoint labels for stats and data tables.",
            },
            {
                "field": "timepoint_display",
                "value": "0h / 4h / 12h / 24h",
                "notes": "Display label that pools 24h (1) and 24h (2) for time-course figures.",
            },
            {
                "field": "metagenomics_pooling",
                "value": "Metagenomics rows retain corrected Treatment labels in the master data.",
                "notes": "Time-course analyses still pool metagenomics rows as the shared 0h baseline.",
            },
            {
                "field": "mapping_setup",
                "value": "minimap2 vs 4 Lm strains + 3 other Listeria genomes (7-strain setup)",
                "notes": "See supporting notes for the upstream mapping configuration.",
            },
        ]
    )

    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        all_rows_sheet.to_excel(xw, sheet_name="all_rows", index=False)
        analysis_only.to_excel(xw, sheet_name="analysis_only", index=False)
        samples.to_excel(xw, sheet_name="samples", index=False)
        per_strain.to_excel(xw, sheet_name="per_strain_analysis", index=False)
        readme.to_excel(xw, sheet_name="readme", index=False)
    print(
        f"[excel] wrote {out_path} — all_rows={len(all_rows_sheet)}, "
        f"analysis_only={len(analysis_only)}, per_strain={len(per_strain)}"
    )


# --------------------------------------------------------------------------------------
# 3. Stats
# --------------------------------------------------------------------------------------
@dataclass
class TestResult:
    comparison: str
    subgroup: str
    metric: str
    n1: int
    n2: int
    median1: float
    median2: float
    U: float
    p: float
    effect_r: float


def _mwu(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Two-sided MWU + rank-biserial effect size (Kerby 2014). Returns (U, p, r).

    scipy.stats.mannwhitneyu returns U1 = number of pairs (a_i, b_j) where
    a_i > b_j (ties counted as 0.5). Kerby's rank-biserial correlation is
    r = f - u, where f is the proportion of favorable pairs (a > b) and u
    is the proportion of unfavorable pairs (a < b). For two sample sizes
    n1 and n2 without ties this simplifies to:

        r = 2 * U1 / (n1 * n2) - 1

    Positive r  =>  group `a` tends to be larger than group `b`
    Negative r  =>  group `b` tends to be larger than group `a`
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return np.nan, np.nan, np.nan
    U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    r = (2.0 * float(U)) / (len(a) * len(b)) - 1.0
    return float(U), float(p), float(r)


def _bh_adjust(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(1, n + 1))
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out.tolist()


def _spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 3:
        return np.nan, np.nan, int(mask.sum())
    rho, p = stats.spearmanr(x[mask], y[mask])
    return float(rho), float(p), int(mask.sum())


def run_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = ["Lm % Reads", "Lm % Bases", "L. ivanovii Nr26 Proportion"]

    # ---- 3a: quasimeta sponge only, AS vs N per timepoint × treatment ----
    # Convention: group 1 = AS, group 2 = N (matches the left-to-right order of
    # the "AS vs N" comparison string). Positive effect-size r  =>  AS > N.
    qm_sponge = df[(df["is_quasimeta"]) & (df["Swab Type"] == "Sponge")].copy()
    rows_a: list[TestResult] = []
    for metric in metrics:
        for tp in ["4h", "12h", "24h (1)", "24h (2)"]:
            for tr in TREATMENT_ORDER:
                sub = qm_sponge[(qm_sponge["timepoint"] == tp) & (qm_sponge["Treatment"] == tr)]
                a = sub.loc[sub["Condition"] == "AS", metric].to_numpy()
                b = sub.loc[sub["Condition"] == "N", metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_a.append(
                    TestResult(
                        comparison="AS vs N",
                        subgroup=f"sponge | {tp} | {tr}",
                        metric=metric,
                        n1=len(a),
                        n2=len(b),
                        median1=float(np.median(a)) if len(a) else np.nan,
                        median2=float(np.median(b)) if len(b) else np.nan,
                        U=U,
                        p=p,
                        effect_r=r,
                    )
                )
    stats_a = pd.DataFrame([vars(r) for r in rows_a])
    stats_a["p_BH"] = _bh_adjust(stats_a["p"].fillna(1.0).tolist())

    # ---- 3b: metagenomic, AS vs N per swab type + swab-type comparisons ----
    # Same convention as above: group 1 = AS, group 2 = N for "AS vs N" rows.
    meta = df[~df["is_quasimeta"]].copy()
    rows_b: list[TestResult] = []
    for metric in metrics:
        for swab in SWAB_ORDER:
            sub = meta[meta["Swab Type"] == swab]
            a = sub.loc[sub["Condition"] == "AS", metric].to_numpy()
            b = sub.loc[sub["Condition"] == "N", metric].to_numpy()
            U, p, r = _mwu(a, b)
            rows_b.append(
                TestResult(
                    comparison="AS vs N",
                    subgroup=f"metagenomic | {swab}",
                    metric=metric,
                    n1=len(a),
                    n2=len(b),
                    median1=float(np.median(a)) if len(a) else np.nan,
                    median2=float(np.median(b)) if len(b) else np.nan,
                    U=U,
                    p=p,
                    effect_r=r,
                )
            )

        # Pairwise swab comparisons (N samples only)
        meta_n = meta[meta["Condition"] == "N"]
        for i, s1 in enumerate(SWAB_ORDER):
            for s2 in SWAB_ORDER[i + 1 :]:
                a = meta_n.loc[meta_n["Swab Type"] == s1, metric].to_numpy()
                b = meta_n.loc[meta_n["Swab Type"] == s2, metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_b.append(
                    TestResult(
                        comparison=f"{s1} vs {s2} (N only)",
                        subgroup="metagenomic",
                        metric=metric,
                        n1=len(a),
                        n2=len(b),
                        median1=float(np.median(a)) if len(a) else np.nan,
                        median2=float(np.median(b)) if len(b) else np.nan,
                        U=U,
                        p=p,
                        effect_r=r,
                    )
                )

        # Kruskal-Wallis across all 3 swab types (N)
        groups_n = [meta_n.loc[meta_n["Swab Type"] == s, metric].dropna().to_numpy() for s in SWAB_ORDER]
        if all(len(g) > 0 for g in groups_n):
            H, p = stats.kruskal(*groups_n)
            rows_b.append(
                TestResult(
                    comparison="Kruskal-Wallis swab types (N only)",
                    subgroup="metagenomic",
                    metric=metric,
                    n1=sum(len(g) for g in groups_n),
                    n2=0,
                    median1=float(np.median(np.concatenate(groups_n))),
                    median2=np.nan,
                    U=float(H),
                    p=float(p),
                    effect_r=np.nan,
                )
            )

    stats_b = pd.DataFrame([vars(r) for r in rows_b])
    stats_b["p_BH"] = _bh_adjust(stats_b["p"].fillna(1.0).tolist())

    # ---- N-only time-course trend (Spearman rho vs timepoint index) ----
    # Sponge only, treatments Lm2/Lm4/Lm6, 0h included from metagenomics baseline
    rows_t: list[dict] = []
    for metric in metrics:
        data = _prep_quasimeta_sponge(df, metric)
        n_data = data[data["Condition"] == "N"].copy()
        n_data["tp_idx"] = n_data["timepoint"].map(
            {"0h": 0, "4h": 1, "12h": 2, "24h (1)": 3, "24h (2)": 3}
        )
        for tr in TREATMENT_ORDER:
            sub = n_data[n_data["Treatment"] == tr]
            rho, p, n = _spearman(sub["tp_idx"].to_numpy(), sub[metric].to_numpy())
            rows_t.append(
                {
                    "figure": "Fig 3a.1 (trend)",
                    "comparison": "Spearman: Lm % vs timepoint index",
                    "subgroup": f"sponge | N | {tr}",
                    "metric": metric,
                    "n1": n,
                    "n2": 0,
                    "median1": float(np.median(sub[metric])) if len(sub) else np.nan,
                    "median2": np.nan,
                    "stat_name": "rho",
                    "stat": rho,
                    "p": p,
                }
            )
    stats_trend = pd.DataFrame(rows_t)
    stats_trend["p_BH"] = _bh_adjust(stats_trend["p"].fillna(1.0).tolist())

    # ---- N-only dose-response at 24 h (Lm2 vs Lm4 vs Lm6, sponge) ----
    # Pool 24h (1) + 24h (2)
    rows_d: list[dict] = []
    qm_sponge_n = df[
        df["is_quasimeta"]
        & (df["Swab Type"] == "Sponge")
        & (df["Condition"] == "N")
        & df["timepoint"].astype(str).isin(["24h (1)", "24h (2)"])
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    for metric in metrics:
        groups = [
            qm_sponge_n.loc[qm_sponge_n["Treatment"] == tr, metric].dropna().to_numpy()
            for tr in TREATMENT_ORDER
        ]
        if all(len(g) > 0 for g in groups):
            H, p = stats.kruskal(*groups)
            rows_d.append(
                {
                    "figure": "Fig 3a.5 (dose)",
                    "comparison": "Kruskal-Wallis Lm2 vs Lm4 vs Lm6",
                    "subgroup": "sponge | N | 24h pooled",
                    "metric": metric,
                    "n1": sum(len(g) for g in groups),
                    "n2": 0,
                    "median1": float(np.median(np.concatenate(groups))),
                    "median2": np.nan,
                    "stat_name": "H",
                    "stat": float(H),
                    "p": float(p),
                }
            )
        for i, t1 in enumerate(TREATMENT_ORDER):
            for t2 in TREATMENT_ORDER[i + 1 :]:
                a = qm_sponge_n.loc[qm_sponge_n["Treatment"] == t1, metric].to_numpy()
                b = qm_sponge_n.loc[qm_sponge_n["Treatment"] == t2, metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_d.append(
                    {
                        "figure": "Fig 3a.5 (dose)",
                        "comparison": f"{t1} vs {t2}",
                        "subgroup": "sponge | N | 24h pooled",
                        "metric": metric,
                        "n1": len(a),
                        "n2": len(b),
                        "median1": float(np.median(a)) if len(a) else np.nan,
                        "median2": float(np.median(b)) if len(b) else np.nan,
                        "stat_name": "U",
                        "stat": U,
                        "p": p,
                        "effect_r": r,
                    }
                )
    stats_dose = pd.DataFrame(rows_d)
    stats_dose["p_BH"] = _bh_adjust(stats_dose["p"].fillna(1.0).tolist())

    # ---- Extraction-kit comparison (quasimeta only, N samples) ----
    # In the metagenomic data kit is perfectly confounded with swab type
    # (Sponge→PowerSoil, Cotton & Zymo swab→Zymo kit), so no test is identifiable.
    # In quasimeta, Micro and Mini kits were used on all three swab types — clean MWU.
    rows_k: list[dict] = []
    quasi_n = df[df["is_quasimeta"] & (df["Condition"] == "N") & df["Treatment"].isin(TREATMENT_ORDER)].copy()
    for metric in metrics:
        # Overall Micro vs Mini, pooled across swab types & timepoints
        a = quasi_n.loc[quasi_n["Extraction Kit"] == "Micro", metric].to_numpy()
        b = quasi_n.loc[quasi_n["Extraction Kit"] == "Mini", metric].to_numpy()
        U, p, r = _mwu(a, b)
        rows_k.append(
            {
                "figure": "Fig 3c (kit)",
                "comparison": "Micro vs Mini (quasimeta, pooled)",
                "subgroup": "quasimeta | N | all swab types",
                "metric": metric,
                "n1": len(a),
                "n2": len(b),
                "median1": float(np.median(a)) if len(a) else np.nan,
                "median2": float(np.median(b)) if len(b) else np.nan,
                "stat_name": "U",
                "stat": U,
                "p": p,
                "effect_r": r,
            }
        )
        # Within each swab type
        for swab in SWAB_ORDER:
            sub = quasi_n[quasi_n["Swab Type"] == swab]
            a = sub.loc[sub["Extraction Kit"] == "Micro", metric].to_numpy()
            b = sub.loc[sub["Extraction Kit"] == "Mini", metric].to_numpy()
            U, p, r = _mwu(a, b)
            rows_k.append(
                {
                    "figure": "Fig 3c (kit)",
                    "comparison": "Micro vs Mini",
                    "subgroup": f"quasimeta | N | {swab}",
                    "metric": metric,
                    "n1": len(a),
                    "n2": len(b),
                    "median1": float(np.median(a)) if len(a) else np.nan,
                    "median2": float(np.median(b)) if len(b) else np.nan,
                    "stat_name": "U",
                    "stat": U,
                    "p": p,
                    "effect_r": r,
                }
            )
    stats_kit = pd.DataFrame(rows_k)
    stats_kit["p_BH"] = _bh_adjust(stats_kit["p"].fillna(1.0).tolist())

    # ---- POOLED analyses: Lm2/Lm4/Lm6 treated as one "Lm-inoculated" group ----
    # (Lm2/4/6 are just spike-in CFU levels.) The 0 h baseline comes from metagenomics
    # sponge rows. These tests gain power by dropping the per-dose stratification and
    # answer the overall-effect questions Lara needs for the main story.
    rows_p: list[dict] = []

    # P1) AS vs N per timepoint, sponge quasimeta, treatments pooled
    qm_sponge_inoc = df[
        df["is_quasimeta"]
        & (df["Swab Type"] == "Sponge")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    for metric in metrics:
        for tp in ["4h", "12h", "24h (1)", "24h (2)"]:
            sub = qm_sponge_inoc[qm_sponge_inoc["timepoint"] == tp]
            # Convention: group 1 = AS, group 2 = N. Positive r => AS > N.
            a = sub.loc[sub["Condition"] == "AS", metric].to_numpy()
            b = sub.loc[sub["Condition"] == "N", metric].to_numpy()
            U, p, r = _mwu(a, b)
            rows_p.append(
                {
                    "figure": "Fig 3a.3p (pooled AS vs N)",
                    "comparison": "AS vs N",
                    "subgroup": f"sponge | {tp} | Lm pooled",
                    "metric": metric,
                    "n1": len(a),
                    "n2": len(b),
                    "median1": float(np.median(a)) if len(a) else np.nan,
                    "median2": float(np.median(b)) if len(b) else np.nan,
                    "stat_name": "U",
                    "stat": U,
                    "p": p,
                    "effect_r": r,
                }
            )

    # P2) Spearman time-course trend, sponge N, pooled
    data_pool = _prep_quasimeta_sponge(df, "Lm % Reads")  # baseline injection happens here
    # Build a generic pooled frame per metric
    for metric in metrics:
        data = _prep_quasimeta_sponge(df, metric)
        n_pool = data[data["Condition"] == "N"].copy()
        n_pool["tp_idx"] = n_pool["timepoint"].map(
            {"0h": 0, "4h": 1, "12h": 2, "24h (1)": 3, "24h (2)": 3}
        )
        rho, p, n = _spearman(n_pool["tp_idx"].to_numpy(), n_pool[metric].to_numpy())
        rows_p.append(
            {
                "figure": "Fig 3a.1p (pooled trend)",
                "comparison": "Spearman: metric vs timepoint index",
                "subgroup": "sponge | N | Lm pooled",
                "metric": metric,
                "n1": n,
                "n2": 0,
                "median1": float(np.nanmedian(n_pool[metric])),
                "median2": np.nan,
                "stat_name": "rho",
                "stat": rho,
                "p": p,
            }
        )

    # P3) 0 h baseline vs each later timepoint (sponge N, pooled)
    for metric in metrics:
        data = _prep_quasimeta_sponge(df, metric)
        n_pool = data[data["Condition"] == "N"].copy()
        baseline = n_pool.loc[n_pool["timepoint"] == "0h", metric].to_numpy()
        # dedupe the injected 0h rows (they were triplicated across treatments)
        baseline = np.unique(baseline)
        for tp in ["4h", "12h", "24h (1)", "24h (2)"]:
            later = n_pool.loc[n_pool["timepoint"] == tp, metric].to_numpy()
            U, p, r = _mwu(baseline, later)
            rows_p.append(
                {
                    "figure": "Fig 3d (baseline vs time)",
                    "comparison": f"0h vs {tp}",
                    "subgroup": "sponge | N | Lm pooled",
                    "metric": metric,
                    "n1": len(baseline),
                    "n2": len(later),
                    "median1": float(np.median(baseline)) if len(baseline) else np.nan,
                    "median2": float(np.median(later)) if len(later) else np.nan,
                    "stat_name": "U",
                    "stat": U,
                    "p": p,
                    "effect_r": r,
                }
            )
        # also a single 0 h vs 24 h-pooled summary
        later24 = n_pool.loc[n_pool["timepoint"].astype(str).isin(["24h (1)", "24h (2)"]), metric].to_numpy()
        U, p, r = _mwu(baseline, later24)
        rows_p.append(
            {
                "figure": "Fig 3d (baseline vs time)",
                "comparison": "0h vs 24h pooled",
                "subgroup": "sponge | N | Lm pooled",
                "metric": metric,
                "n1": len(baseline),
                "n2": len(later24),
                "median1": float(np.median(baseline)) if len(baseline) else np.nan,
                "median2": float(np.median(later24)) if len(later24) else np.nan,
                "stat_name": "U",
                "stat": U,
                "p": p,
                "effect_r": r,
            }
        )

    # P4) Swab-type effect in quasimeta (N, pooled Lm2/4/6) — new, cross-cutting
    qm_inoc_n = df[
        df["is_quasimeta"]
        & (df["Condition"] == "N")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    for metric in metrics:
        groups = [
            qm_inoc_n.loc[qm_inoc_n["Swab Type"] == s, metric].dropna().to_numpy()
            for s in SWAB_ORDER
        ]
        if all(len(g) > 0 for g in groups):
            H, p = stats.kruskal(*groups)
            rows_p.append(
                {
                    "figure": "Fig 3b.1p (pooled quasi swab)",
                    "comparison": "Kruskal-Wallis swab types",
                    "subgroup": "quasimeta | N | Lm pooled",
                    "metric": metric,
                    "n1": sum(len(g) for g in groups),
                    "n2": 0,
                    "median1": float(np.median(np.concatenate(groups))),
                    "median2": np.nan,
                    "stat_name": "H",
                    "stat": float(H),
                    "p": float(p),
                }
            )
        for i, s1 in enumerate(SWAB_ORDER):
            for s2 in SWAB_ORDER[i + 1 :]:
                a = qm_inoc_n.loc[qm_inoc_n["Swab Type"] == s1, metric].to_numpy()
                b = qm_inoc_n.loc[qm_inoc_n["Swab Type"] == s2, metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_p.append(
                    {
                        "figure": "Fig 3b.1p (pooled quasi swab)",
                        "comparison": f"{s1} vs {s2}",
                        "subgroup": "quasimeta | N | Lm pooled",
                        "metric": metric,
                        "n1": len(a),
                        "n2": len(b),
                        "median1": float(np.median(a)) if len(a) else np.nan,
                        "median2": float(np.median(b)) if len(b) else np.nan,
                        "stat_name": "U",
                        "stat": U,
                        "p": p,
                        "effect_r": r,
                    }
                )

    # ---- NEW: Pairwise timepoint MWU within each Lm level (sponge N only) ----
    rows_tt: list[dict] = []
    tps_tt = ["4h", "12h", "24h (1)", "24h (2)"]
    qm_sponge_n_all = df[
        df["is_quasimeta"]
        & (df["Swab Type"] == "Sponge")
        & (df["Condition"] == "N")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    for metric in metrics:
        for tr in TREATMENT_ORDER:
            sub_tr = qm_sponge_n_all[qm_sponge_n_all["Treatment"] == tr]
            for i, t1 in enumerate(tps_tt):
                for t2 in tps_tt[i + 1 :]:
                    a = sub_tr.loc[sub_tr["timepoint"].astype(str) == t1, metric].to_numpy()
                    b = sub_tr.loc[sub_tr["timepoint"].astype(str) == t2, metric].to_numpy()
                    U, p, r = _mwu(a, b)
                    rows_tt.append(
                        {
                            "figure": "Fig 3a.t (pairwise timepoint)",
                            "comparison": f"{t1} vs {t2}",
                            "subgroup": f"sponge | N | {tr}",
                            "metric": metric,
                            "n1": len(a),
                            "n2": len(b),
                            "median1": float(np.median(a)) if len(a) else np.nan,
                            "median2": float(np.median(b)) if len(b) else np.nan,
                            "stat_name": "U",
                            "stat": U,
                            "p": p,
                            "effect_r": r,
                        }
                    )
        # Also pooled across Lm2/4/6 for a trend-friendly overview
        for i, t1 in enumerate(tps_tt):
            for t2 in tps_tt[i + 1 :]:
                a = qm_sponge_n_all.loc[qm_sponge_n_all["timepoint"].astype(str) == t1, metric].to_numpy()
                b = qm_sponge_n_all.loc[qm_sponge_n_all["timepoint"].astype(str) == t2, metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_tt.append(
                    {
                        "figure": "Fig 3a.t (pairwise timepoint)",
                        "comparison": f"{t1} vs {t2}",
                        "subgroup": "sponge | N | Lm pooled",
                        "metric": metric,
                        "n1": len(a),
                        "n2": len(b),
                        "median1": float(np.median(a)) if len(a) else np.nan,
                        "median2": float(np.median(b)) if len(b) else np.nan,
                        "stat_name": "U",
                        "stat": U,
                        "p": p,
                        "effect_r": r,
                    }
                )
    stats_timepoint = pd.DataFrame(rows_tt)
    stats_timepoint["p_BH"] = _bh_adjust(stats_timepoint["p"].fillna(1.0).tolist())

    # ---- NEW: Per-Lm-level pairwise swab comparisons (metagenomic N only) ----
    rows_sp: list[dict] = []
    meta_n_all = df[~df["is_quasimeta"] & (df["Condition"] == "N")].copy()
    for metric in metrics:
        for i, s1 in enumerate(SWAB_ORDER):
            for s2 in SWAB_ORDER[i + 1 :]:
                a = meta_n_all.loc[meta_n_all["Swab Type"] == s1, metric].to_numpy()
                b = meta_n_all.loc[meta_n_all["Swab Type"] == s2, metric].to_numpy()
                U, p, r = _mwu(a, b)
                rows_sp.append(
                    {
                        "figure": "Fig 3b.sp (swab pairwise N)",
                        "comparison": f"{s1} vs {s2}",
                        "subgroup": "metagenomic | N | Lm pooled",
                        "metric": metric,
                        "n1": len(a),
                        "n2": len(b),
                        "median1": float(np.median(a)) if len(a) else np.nan,
                        "median2": float(np.median(b)) if len(b) else np.nan,
                        "stat_name": "U",
                        "stat": U,
                        "p": p,
                        "effect_r": r,
                    }
                )
    stats_swab_pool = pd.DataFrame(rows_sp)
    stats_swab_pool["p_BH"] = _bh_adjust(stats_swab_pool["p"].fillna(1.0).tolist())

    stats_pool = pd.DataFrame(rows_p)
    stats_pool["p_BH"] = _bh_adjust(stats_pool["p"].fillna(1.0).tolist())

    # ---- Consolidated, readable table ----
    def tag_a(row):
        if "sponge" in row["subgroup"]:
            return "Fig 3a.3 (AS vs N)"
        return ""

    def tag_b(row):
        if row["comparison"] == "AS vs N":
            return "Fig 3b.2 (AS vs N)"
        if "Kruskal-Wallis" in row["comparison"]:
            return "Fig 3b.1 (swab KW)"
        return "Fig 3b.1 (swab pairwise)"

    sa = stats_a.copy()
    sa["figure"] = sa.apply(tag_a, axis=1)
    sa["stat_name"] = "U"
    sa = sa.rename(columns={"U": "stat"})

    sb = stats_b.copy()
    sb["figure"] = sb.apply(tag_b, axis=1)
    sb["stat_name"] = sb["comparison"].apply(lambda c: "H" if "Kruskal" in c else "U")
    sb = sb.rename(columns={"U": "stat"})

    cols = [
        "figure",
        "comparison",
        "subgroup",
        "metric",
        "n1",
        "n2",
        "median1",
        "median2",
        "stat_name",
        "stat",
        "p",
        "p_BH",
        "effect_r",
    ]
    all_frames = (sa, sb, stats_trend, stats_dose, stats_kit, stats_pool, stats_timepoint, stats_swab_pool)
    for d in all_frames:
        for c in cols:
            if c not in d.columns:
                d[c] = np.nan
    combined = pd.concat(
        [
            sa[cols],
            sb[cols],
            stats_trend[cols],
            stats_dose[cols],
            stats_kit[cols],
            stats_pool[cols],
            stats_timepoint[cols],
            stats_swab_pool[cols],
        ],
        ignore_index=True,
    )
    combined["sig"] = combined["p"].apply(lambda p: _p_stars(p) if pd.notna(p) else "")
    combined["sig_BH"] = combined["p_BH"].apply(lambda p: _p_stars(p) if pd.notna(p) else "")

    stats_a.to_csv(OUT / "stats_3a.csv", index=False)
    stats_b.to_csv(OUT / "stats_3b.csv", index=False)
    # Combined table (incl. extra pooled / dose / kit tests) → optional subfolder
    combined.to_csv(OUT_OPTIONAL / "stats_all.csv", index=False)

    # Append as sheets into the Excel workbook
    with pd.ExcelWriter(OUT / "listeria_final_table.xlsx", engine="openpyxl", mode="a", if_sheet_exists="replace") as xw:
        combined.to_excel(xw, sheet_name="stats", index=False)

    # Markdown summary for quick scanning
    md_lines = ["# Listeria stats summary\n"]
    for fig_tag, sub in combined.groupby("figure", sort=False):
        md_lines.append(f"\n## {fig_tag}\n")
        tbl = sub[["comparison", "subgroup", "metric", "n1", "n2", "median1", "median2", "stat_name", "stat", "p", "p_BH", "sig"]].copy()
        tbl["p"] = tbl["p"].apply(lambda v: "n/a" if pd.isna(v) else f"{v:.3g}")
        tbl["p_BH"] = tbl["p_BH"].apply(lambda v: "n/a" if pd.isna(v) else f"{v:.3g}")
        for c in ("median1", "median2", "stat"):
            tbl[c] = tbl[c].apply(lambda v: "n/a" if pd.isna(v) else f"{v:.3g}")
        md_lines.append(tbl.to_markdown(index=False))
        md_lines.append("\n")
    (OUT_OPTIONAL / "stats_summary.md").write_text("\n".join(md_lines))

    print(
        f"[stats] wrote stats_3a.csv ({len(stats_a)}), stats_3b.csv ({len(stats_b)}), "
        f"stats_trend ({len(stats_trend)}), stats_dose ({len(stats_dose)}), "
        f"stats_timepoint ({len(stats_timepoint)}), stats_swab_pool ({len(stats_swab_pool)}), "
        f"stats_all.csv ({len(combined)}), stats_summary.md"
    )

    return stats_a, stats_b, stats_trend, stats_dose, stats_kit, stats_pool, stats_timepoint, stats_swab_pool


# --------------------------------------------------------------------------------------
# 4. Figures — helpers
# --------------------------------------------------------------------------------------
def _save(fig: plt.Figure, name: str, optional: bool = False) -> None:
    dest = OUT_OPTIONAL if optional else OUT
    pdf_path = dest / f"{name}.pdf"
    png_path = dest / f"{name}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    tag = "opt" if optional else "fig"
    print(f"[{tag} ] wrote {pdf_path} + .png")


def _annotate_n(ax: plt.Axes, n: int) -> None:
    ax.text(
        0.99,
        0.99,
        f"n = {n}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color="#444",
    )


def _add_panel_labels(axes, labels: list[str] | None = None, x: float = -0.08, y: float = 1.08) -> None:
    """Add a, b, c, d bold panel labels to a list of axes (top-left, outside)."""
    if labels is None:
        labels = [chr(ord("a") + i) for i in range(len(axes))]
    for ax, lab in zip(axes, labels):
        ax.text(
            x,
            y,
            lab,
            transform=ax.transAxes,
            fontsize=13,
            fontweight="bold",
            va="bottom",
            ha="left",
        )


def _mwu_annotation(stats_row: pd.Series) -> str:
    """Formatted MWU annotation with effect size r (rank-biserial)."""
    p = stats_row["p"]
    stars = _p_stars(p)
    r = stats_row.get("effect_r", np.nan)
    n1 = int(stats_row.get("n1", 0))
    n2 = int(stats_row.get("n2", 0))
    if pd.notna(r):
        return f"p = {p:.3g} ({stars})\nr = {r:+.2f}   n = {n1}/{n2}"
    return f"p = {p:.3g} ({stars})\nn = {n1}/{n2}"


def _p_stars(p: float) -> str:
    if np.isnan(p):
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def _prep_quasimeta_sponge(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Stack 0h metagenomics-sponge as shared baseline for every treatment.

    Returns both the fine-grained `timepoint` (for stats: keeps 24h_1/24h_2 apart)
    and a `tp_display` column that pools 24h_1+24h_2 into a single '24h' bin
    (for plots: figure-qa rule 1 — no batches on the time axis).
    """
    q = df[(df["Swab Type"] == "Sponge") & (df["is_quasimeta"])].copy()
    q = q[q["Treatment"].isin(TREATMENT_ORDER)]

    base = df[(df["Swab Type"] == "Sponge") & (~df["is_quasimeta"])].copy()
    base["timepoint"] = "0h"
    frames = [q]
    for tr in TREATMENT_ORDER:
        bb = base.copy()
        bb["Treatment"] = tr
        frames.append(bb)
    out = pd.concat(frames, ignore_index=True)
    out["timepoint"] = pd.Categorical(out["timepoint"], TIMEPOINT_ORDER, ordered=True)
    out["tp_display"] = out["timepoint"].astype(str).replace(
        {"24h (1)": "24h", "24h (2)": "24h"}
    )
    out["tp_display"] = pd.Categorical(
        out["tp_display"], TIMEPOINT_DISPLAY_ORDER, ordered=True
    )
    out["Treatment"] = pd.Categorical(out["Treatment"], TREATMENT_ORDER, ordered=True)
    out["Condition"] = pd.Categorical(out["Condition"], CONDITION_ORDER, ordered=True)
    return out[["timepoint", "tp_display", "Treatment", "Condition", "Lab ID", metric]]


# --------------------------------------------------------------------------------------
# 4a. Quasimeta figures
# --------------------------------------------------------------------------------------
def fig_3a1_timecourse(df: pd.DataFrame, metric: str = "Lm % Reads", label: str | None = None, out_name: str = "fig_3a1_timecourse_lm_pct") -> None:
    data = _prep_quasimeta_sponge(df, metric)
    n_data = data[data["Condition"] == "N"]

    fig, ax = plt.subplots(figsize=(9.0, 5.5), constrained_layout=True)
    sns.stripplot(
        data=n_data,
        x="timepoint",
        y=metric,
        hue="Treatment",
        palette=PALETTE_TREATMENT,
        order=TIMEPOINT_ORDER,
        dodge=True,
        jitter=0.2,
        alpha=0.75,
        size=6,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
    )
    med = n_data.groupby(["timepoint", "Treatment"], observed=True)[metric].median().reset_index()
    for tr in TREATMENT_ORDER:
        m = med[med["Treatment"] == tr].set_index("timepoint").reindex(TIMEPOINT_ORDER)
        ax.plot(
            range(len(TIMEPOINT_ORDER)),
            m[metric].to_numpy(),
            color=PALETTE_TREATMENT[tr],
            linewidth=2.2,
            marker="o",
            markersize=7,
            markeredgecolor="white",
            markeredgewidth=1.0,
            zorder=5,
            label=None,
        )
    ax.set_xlabel("Timepoint (sponge quasimetagenomic, N samples)")
    ax.set_ylabel(label or f"{metric} (%)")
    ax.set_title(f"Listeria time course — {label or metric}")
    ax.legend(title="Treatment", loc="upper left", frameon=False, bbox_to_anchor=(1.01, 1.0))
    _annotate_n(ax, len(n_data))
    _save(fig, out_name)


def fig_3a2_timecourse_nstrains(df: pd.DataFrame) -> None:
    data = _prep_quasimeta_sponge(df, "# Lm Strains Detected")
    n_data = data[data["Condition"] == "N"]

    fig, ax = plt.subplots(figsize=(9.0, 5.5), constrained_layout=True)
    sns.stripplot(
        data=n_data,
        x="timepoint",
        y="# Lm Strains Detected",
        hue="Treatment",
        palette=PALETTE_TREATMENT,
        order=TIMEPOINT_ORDER,
        dodge=True,
        jitter=0.2,
        alpha=0.8,
        size=7,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_yticks(range(0, 5))
    ax.set_ylim(-0.4, 4.4)
    ax.set_xlabel("Timepoint (sponge, N samples)")
    ax.set_ylabel("Number of Lm strains detected")
    ax.set_title("Strain-level Lm detection over time")
    ax.legend(title="Treatment", loc="upper left", frameon=False, bbox_to_anchor=(1.01, 1.0))
    _annotate_n(ax, len(n_data))
    _save(fig, "fig_3a2_timecourse_nstrains")


def fig_3a3_as_vs_n_quasimeta(df: pd.DataFrame, stats_a: pd.DataFrame, metric: str = "Lm % Reads", out_name: str = "fig_3a3_as_vs_n_quasimeta", label: str | None = None) -> None:
    """One figure per treatment (3 separate PDFs) to keep panels large."""
    data = _prep_quasimeta_sponge(df, metric)
    quasi_tps = ["4h", "12h", "24h (1)", "24h (2)"]
    data = data[data["timepoint"].isin(quasi_tps)].copy()
    data["timepoint"] = data["timepoint"].astype(str)

    stats_sub = stats_a[stats_a["metric"] == metric].copy()

    for treatment in TREATMENT_ORDER:
        sub = data[data["Treatment"] == treatment]
        if sub.empty:
            continue
        fig, axes = plt.subplots(1, 4, figsize=(14, 5.2), constrained_layout=True, sharey=True)
        ymax = sub[metric].max()
        headroom = ymax * 1.28 if ymax > 0 else 1.0
        for ax, tp in zip(axes, quasi_tps):
            panel = sub[sub["timepoint"] == tp]
            sns.stripplot(
                data=panel,
                x="Condition",
                y=metric,
                hue="Condition",
                palette=PALETTE_CONDITION,
                order=CONDITION_ORDER,
                jitter=0.18,
                size=9,
                alpha=0.85,
                ax=ax,
                legend=False,
                edgecolor="white",
                linewidth=0.6,
            )
            sns.boxplot(
                data=panel,
                x="Condition",
                y=metric,
                order=CONDITION_ORDER,
                ax=ax,
                showfliers=False,
                width=0.5,
                boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
                medianprops=dict(color="black", linewidth=1.8),
                whiskerprops=dict(color="black", linewidth=1.1),
                capprops=dict(color="black", linewidth=1.1),
            )
            row = stats_sub[stats_sub["subgroup"] == f"sponge | {tp} | {treatment}"]
            if len(row):
                ax.text(
                    0.5,
                    1.02,
                    _mwu_annotation(row.iloc[0]),
                    transform=ax.transAxes,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#333",
                )
            ax.set_title(tp, pad=36)
            ax.set_xlabel("Condition")
            if ax is axes[0]:
                ax.set_ylabel(label or f"{metric} (%)")
            else:
                ax.set_ylabel("")
        for ax in axes:
            ax.set_ylim(top=headroom)
        _add_panel_labels(list(axes))
        fig.suptitle(
            f"AS vs N — sponge quasimetagenomic, {treatment} — {label or metric}",
            fontsize=13,
        )
        suffix = treatment.lower()
        _save(fig, f"{out_name}_{suffix}")


def fig_strain_timecourse(df: pd.DataFrame) -> None:
    """Relative abundance of the four L. monocytogenes strains across the
    sponge quasimetagenomic timeline, N only, Lm2/Lm4/Lm6 pooled.

    Produces two panels side by side:
      - left  : each strain's reads as % of total sample reads (absolute view)
      - right : each strain's reads as % of the Lm-mapped reads pool
                (relative strain composition, sums to ~100 % per timepoint)
    Lines = mean per timepoint, error bars = SEM, raw per-sample points jittered
    behind the lines. Four colours, one per strain.
    """
    q = df[
        (df["Swab Type"] == "Sponge")
        & df["is_quasimeta"]
        & (df["Condition"] == "N")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    baseline = df[
        (df["Swab Type"] == "Sponge")
        & (~df["is_quasimeta"])
        & (df["Condition"] == "N")
    ].copy()
    baseline["timepoint"] = "0h"

    frames: list[pd.DataFrame] = []
    for strain in LM_STRAINS:
        reads_col = f"{strain} Reads"
        for src_df in (q, baseline):
            sub = src_df.copy()
            sub["strain"] = strain
            sub["abs_pct"] = 100.0 * sub[reads_col] / sub["Total Reads"].replace(0, np.nan)
            lm_total = sub[[f"{s} Reads" for s in LM_STRAINS]].sum(axis=1)
            sub["rel_pct"] = 100.0 * sub[reads_col] / lm_total.replace(0, np.nan)
            frames.append(sub[["timepoint", "strain", "abs_pct", "rel_pct", "Lab ID"]])
    long = pd.concat(frames, ignore_index=True)
    long["timepoint"] = long["timepoint"].astype(str)
    long["tp_idx"] = long["timepoint"].map(
        {tp: i for i, tp in enumerate(TIMEPOINT_ORDER)}
    )

    fig, (ax_abs, ax_rel) = plt.subplots(1, 2, figsize=(15, 5.8), constrained_layout=True)
    rng = np.random.default_rng(123)

    def _draw(ax, metric_col: str, ylabel: str, title: str) -> None:
        for strain in LM_STRAINS:
            colour = PALETTE_LM_STRAIN[strain]
            marker = LM_STRAIN_MARKERS[strain]
            s = long[long["strain"] == strain].dropna(subset=[metric_col])
            means: list[float] = []
            sems: list[float] = []
            xs: list[int] = []
            for tp in TIMEPOINT_ORDER:
                vals = s[s["timepoint"] == tp][metric_col].to_numpy()
                if not len(vals):
                    continue
                xs.append(TIMEPOINT_ORDER.index(tp))
                means.append(float(vals.mean()))
                sems.append(float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0)
                jitter = rng.uniform(-0.14, 0.14, size=len(vals))
                ax.scatter(
                    np.full(len(vals), TIMEPOINT_ORDER.index(tp)) + jitter,
                    vals,
                    color=colour,
                    s=18,
                    alpha=0.35,
                    zorder=2,
                    linewidths=0,
                )
            ax.errorbar(
                xs,
                means,
                yerr=sems,
                color=colour,
                lw=2.2,
                marker=marker,
                markersize=7,
                capsize=3.5,
                zorder=5,
                markeredgecolor="white",
                markeredgewidth=0.8,
                label=strain,
            )
        ax.set_xticks(range(len(TIMEPOINT_ORDER)))
        ax.set_xticklabels(TIMEPOINT_ORDER, rotation=25, ha="right")
        ax.set_xlabel("Sponge incubation timepoint (N samples, Lm2/4/6 pooled)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.set_ylim(bottom=0)

    _draw(
        ax_abs,
        "abs_pct",
        "Strain reads / total reads (%)",
        "Absolute strain abundance",
    )
    _draw(
        ax_rel,
        "rel_pct",
        "Strain reads / Lm-mapped reads (%)",
        "Relative strain composition (within Lm pool)",
    )
    _add_panel_labels([ax_abs, ax_rel])
    ax_rel.legend(
        title="L. monocytogenes strain",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        frameon=False,
        fontsize=9,
        title_fontsize=10,
    )
    fig.suptitle(
        "Per-strain relative abundance across the quasimetagenomic timeline",
        fontsize=13,
    )
    _annotate_n(ax_rel, len(q) + len(baseline))
    _save(fig, "fig_strain_timecourse_per_strain")


def fig_3a4_strain_heatmap(df: pd.DataFrame) -> None:
    data = _prep_quasimeta_sponge(df, "Lm % Reads")  # for ordering only
    q = df[(df["Swab Type"] == "Sponge") & df["is_quasimeta"] & df["Treatment"].isin(TREATMENT_ORDER)].copy()
    q = q[q["Condition"] == "N"]

    # mean per (timepoint, treatment) of each Lm strain's share of total reads (%)
    rows = []
    for (tp, tr), sub in q.groupby(["timepoint", "Treatment"], observed=True):
        for strain in LM_STRAINS:
            val = 100.0 * sub[f"{strain} Reads"].sum() / max(sub["Total Reads"].sum(), 1)
            rows.append({"timepoint": str(tp), "Treatment": str(tr), "strain": strain, "pct": val})
    # 0h baseline (treatment-agnostic)
    base = df[(df["Swab Type"] == "Sponge") & (~df["is_quasimeta"]) & (df["Condition"] == "N")]
    for strain in LM_STRAINS:
        val = 100.0 * base[f"{strain} Reads"].sum() / max(base["Total Reads"].sum(), 1)
        for tr in TREATMENT_ORDER:
            rows.append({"timepoint": "0h", "Treatment": tr, "strain": strain, "pct": val})

    hm = pd.DataFrame(rows)
    hm["col"] = hm["Treatment"].astype(str) + " | " + hm["timepoint"].astype(str)
    col_order = [f"{tr} | {tp}" for tr in TREATMENT_ORDER for tp in TIMEPOINT_ORDER]
    mat = hm.pivot(index="strain", columns="col", values="pct").reindex(index=LM_STRAINS, columns=col_order)

    fig, ax = plt.subplots(figsize=(14, 6.0), constrained_layout=True)
    sns.heatmap(
        mat,
        cmap="viridis",
        cbar_kws={"label": "% of total reads"},
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        annot=True,
        fmt=".2f",
        annot_kws={"fontsize": 10},
    )
    ax.set_xlabel("Treatment | Timepoint")
    ax.set_ylabel("Lm strain")
    ax.set_title("Per-strain Lm detection — sponge quasimetagenomic, N samples")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=10)
    plt.setp(ax.get_yticklabels(), fontsize=11)
    _save(fig, "fig_3a4_strain_heatmap", optional=True)


# --------------------------------------------------------------------------------------
# 4b. Metagenomic figures (all swab types)
# --------------------------------------------------------------------------------------
def fig_3b1_swabtypes_lm_pct(df: pd.DataFrame, stats_b: pd.DataFrame, metric: str = "Lm % Reads", out_name: str = "fig_3b1_swabtypes_lm_pct", label: str | None = None) -> None:
    meta = df[~df["is_quasimeta"] & (df["Condition"] == "N")].copy()

    fig, ax = plt.subplots(figsize=(7.5, 6.0), constrained_layout=True)
    sns.stripplot(
        data=meta,
        x="Swab Type",
        y=metric,
        hue="Swab Type",
        palette=PALETTE_SWAB,
        order=SWAB_ORDER,
        jitter=0.2,
        size=8,
        alpha=0.85,
        ax=ax,
        legend=False,
    )
    sns.boxplot(
        data=meta,
        x="Swab Type",
        y=metric,
        order=SWAB_ORDER,
        ax=ax,
        showfliers=False,
        width=0.5,
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
        medianprops=dict(color="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.1),
        capprops=dict(color="black", linewidth=1.1),
    )
    ax.set_xlabel("Swab type")
    ax.set_ylabel(label or f"{metric} (%)")
    ax.set_title(f"Metagenomic samples — {label or metric} by swab type (N only)")

    # Annotate pairwise MWU p-values from stats_b
    stats_sub = stats_b[(stats_b["metric"] == metric) & stats_b["comparison"].str.contains(" vs ")]
    ymax = meta[metric].max()
    y = ymax * 1.08 if ymax > 0 else 1.0
    for _, row in stats_sub.iterrows():
        comp = row["comparison"].replace(" (N only)", "")
        parts = [p.strip() for p in comp.split(" vs ")]
        if len(parts) != 2 or any(p not in SWAB_ORDER for p in parts):
            continue
        if "AS" in row["comparison"]:
            continue
        x1, x2 = SWAB_ORDER.index(parts[0]), SWAB_ORDER.index(parts[1])
        ax.plot([x1, x1, x2, x2], [y, y * 1.04, y * 1.04, y], color="black", lw=1.0)
        r_val = row.get("effect_r", np.nan)
        r_str = f"  r={r_val:+.2f}" if pd.notna(r_val) else ""
        ax.text(
            (x1 + x2) / 2,
            y * 1.06,
            f"p={row['p']:.2g} ({_p_stars(row['p'])}){r_str}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
        y *= 1.15
    ax.set_ylim(top=y * 1.05 if y > 0 else None)
    _annotate_n(ax, len(meta))
    _save(fig, out_name)


def fig_3b2_as_vs_n_metagenomic(df: pd.DataFrame, stats_b: pd.DataFrame, metric: str = "Lm % Reads", out_name: str = "fig_3b2_as_vs_n_metagenomic", label: str | None = None) -> None:
    meta = df[~df["is_quasimeta"]].copy()

    fig, axes = plt.subplots(1, 3, figsize=(13, 5.5), constrained_layout=True, sharey=True)
    for ax, swab in zip(axes, SWAB_ORDER):
        sub = meta[meta["Swab Type"] == swab]
        sns.stripplot(
            data=sub,
            x="Condition",
            y=metric,
            hue="Condition",
            palette=PALETTE_CONDITION,
            order=CONDITION_ORDER,
            jitter=0.2,
            size=8,
            alpha=0.85,
            ax=ax,
            legend=False,
        )
        sns.boxplot(
            data=sub,
            x="Condition",
            y=metric,
            order=CONDITION_ORDER,
            ax=ax,
            showfliers=False,
            width=0.5,
            boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.2),
            medianprops=dict(color="black", linewidth=1.6),
            whiskerprops=dict(color="black", linewidth=1.0),
            capprops=dict(color="black", linewidth=1.0),
        )
        row = stats_b[
            (stats_b["metric"] == metric)
            & (stats_b["subgroup"] == f"metagenomic | {swab}")
            & (stats_b["comparison"] == "AS vs N")
        ]
        if len(row):
            ax.text(
                0.5,
                1.02,
                _mwu_annotation(row.iloc[0]),
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333",
            )
        ax.set_title(swab, pad=36)
        ax.set_xlabel("Condition")
        if ax is axes[0]:
            ax.set_ylabel(label or f"{metric} (%)")
        else:
            ax.set_ylabel("")
    _add_panel_labels(list(axes))
    fig.suptitle(f"AS vs N in metagenomic samples — {label or metric}", fontsize=13)
    _save(fig, out_name)


def fig_3b3_swabtypes_nstrains(df: pd.DataFrame) -> None:
    meta = df[~df["is_quasimeta"] & (df["Condition"] == "N")].copy()

    fig, ax = plt.subplots(figsize=(7.5, 5.5), constrained_layout=True)
    sns.stripplot(
        data=meta,
        x="Swab Type",
        y="# Lm Strains Detected",
        hue="Swab Type",
        palette=PALETTE_SWAB,
        order=SWAB_ORDER,
        jitter=0.2,
        size=9,
        alpha=0.85,
        ax=ax,
        legend=False,
    )
    ax.set_yticks(range(0, 5))
    ax.set_ylim(-0.4, 4.4)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Number of Lm strains detected")
    ax.set_title("Strain-level Lm detection by swab type (metagenomic, N only)")
    _annotate_n(ax, len(meta))
    _save(fig, "fig_3b3_swabtypes_nstrains")


# --------------------------------------------------------------------------------------
# 4c. QC figure
# --------------------------------------------------------------------------------------
def fig_qc_readlength_enrichment(df: pd.DataFrame) -> None:
    d = df[df["Lm Total Reads (4 strains)"] > 0].copy()

    fig, ax = plt.subplots(figsize=(8.0, 6.0), constrained_layout=True)
    for swab in SWAB_ORDER:
        sub = d[d["Swab Type"] == swab]
        for cond, marker in (("N", "o"), ("AS", "^")):
            s = sub[sub["Condition"] == cond]
            ax.scatter(
                s["Mean Read Length"],
                s["Lm Mean Read Length"],
                label=f"{swab} · {cond}",
                color=PALETTE_SWAB[swab],
                marker=marker,
                alpha=0.75,
                s=55,
                edgecolor="white",
                linewidth=0.5,
            )
    lims = [
        0,
        max(
            d["Mean Read Length"].max(),
            d["Lm Mean Read Length"].max(),
        )
        * 1.05,
    ]
    ax.plot(lims, lims, "--", color="#999", lw=1.0, label="y = x")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("Mean read length — all reads (bp)")
    ax.set_ylabel("Mean read length — Lm-mapped reads (bp)")
    ax.set_title("Read-length enrichment: Lm-mapped vs all reads")
    ax.legend(loc="upper left", frameon=False, bbox_to_anchor=(1.01, 1.0), fontsize=9)
    _annotate_n(ax, len(d))
    _save(fig, "fig_qc_readlength_enrichment", optional=True)


# --------------------------------------------------------------------------------------
# 4d. Ivanovii supplements
# --------------------------------------------------------------------------------------
def fig_ivanovii_supplements(df: pd.DataFrame, stats_a: pd.DataFrame, stats_b: pd.DataFrame) -> None:
    metric = "L. ivanovii Nr26 Proportion"
    label = "L. ivanovii Nr26 proportion"

    # Time course (analog of 3a1) — x by treatment is meaningless for ivanovii
    # but we keep the same panel so Lara can compare to the Lm version.
    data = _prep_quasimeta_sponge(df, metric)
    n_data = data[data["Condition"] == "N"]
    fig, ax = plt.subplots(figsize=(9.0, 5.5), constrained_layout=True)
    sns.stripplot(
        data=n_data,
        x="timepoint",
        y=metric,
        hue="Treatment",
        palette=PALETTE_TREATMENT,
        order=TIMEPOINT_ORDER,
        dodge=True,
        jitter=0.2,
        alpha=0.8,
        size=6,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
    )
    med = n_data.groupby(["timepoint", "Treatment"], observed=True)[metric].median().reset_index()
    for tr in TREATMENT_ORDER:
        m = med[med["Treatment"] == tr].set_index("timepoint").reindex(TIMEPOINT_ORDER)
        ax.plot(
            range(len(TIMEPOINT_ORDER)),
            m[metric].to_numpy(),
            color=PALETTE_TREATMENT[tr],
            linewidth=2.0,
            marker="o",
            markersize=6,
            markeredgecolor="white",
            markeredgewidth=1.0,
            zorder=5,
        )
    ax.set_xlabel("Timepoint (sponge, N samples)")
    ax.set_ylabel(label)
    ax.set_title(f"Supplement — {label} over time")
    ax.legend(title="Treatment", loc="upper left", frameon=False, bbox_to_anchor=(1.01, 1.0))
    _annotate_n(ax, len(n_data))
    _save(fig, "supp_ivanovii_3a1")

    has_as = "AS" in set(df["Condition"].dropna().astype(str).unique())
    if has_as:
        fig_3a3_as_vs_n_quasimeta(
            df, stats_a, metric=metric, out_name="supp_ivanovii_3a3", label=label
        )
    else:
        print("[skip] supp_ivanovii_3a3 (no AS samples in input)")
    fig_3b1_swabtypes_lm_pct(
        df, stats_b, metric=metric, out_name="supp_ivanovii_3b1", label=label
    )
    if has_as:
        fig_3b2_as_vs_n_metagenomic(
            df, stats_b, metric=metric, out_name="supp_ivanovii_3b2", label=label
        )
    else:
        print("[skip] supp_ivanovii_3b2 (no AS samples in input)")


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def fig_3a5_dose_response(df: pd.DataFrame, stats_dose: pd.DataFrame) -> None:
    qm_sponge_n = df[
        df["is_quasimeta"]
        & (df["Swab Type"] == "Sponge")
        & (df["Condition"] == "N")
        & df["timepoint"].astype(str).isin(["24h (1)", "24h (2)"])
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    qm_sponge_n["Treatment"] = qm_sponge_n["Treatment"].astype(str)

    fig, ax = plt.subplots(figsize=(7.5, 6.0), constrained_layout=True)
    sns.stripplot(
        data=qm_sponge_n,
        x="Treatment",
        y="Lm % Reads",
        hue="Treatment",
        palette=PALETTE_TREATMENT,
        order=TREATMENT_ORDER,
        jitter=0.2,
        size=9,
        alpha=0.85,
        ax=ax,
        legend=False,
    )
    sns.boxplot(
        data=qm_sponge_n,
        x="Treatment",
        y="Lm % Reads",
        order=TREATMENT_ORDER,
        ax=ax,
        showfliers=False,
        width=0.5,
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
        medianprops=dict(color="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.1),
        capprops=dict(color="black", linewidth=1.1),
    )
    kw = stats_dose[
        (stats_dose["metric"] == "Lm % Reads")
        & (stats_dose["comparison"] == "Kruskal-Wallis Lm2 vs Lm4 vs Lm6")
    ]
    if len(kw):
        r = kw.iloc[0]
        ax.text(
            0.02,
            0.97,
            f"Kruskal-Wallis H = {r['stat']:.2f}\np = {r['p']:.3g} ({_p_stars(r['p'])})",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#333",
        )

    # Pairwise annotations
    pairs = stats_dose[
        (stats_dose["metric"] == "Lm % Reads") & stats_dose["comparison"].str.contains(" vs ")
    ]
    ymax = qm_sponge_n["Lm % Reads"].max()
    y = ymax * 1.08 if ymax > 0 else 1.0
    for _, row in pairs.iterrows():
        parts = [p.strip() for p in row["comparison"].split(" vs ")]
        if any(p not in TREATMENT_ORDER for p in parts):
            continue
        x1, x2 = TREATMENT_ORDER.index(parts[0]), TREATMENT_ORDER.index(parts[1])
        ax.plot([x1, x1, x2, x2], [y, y * 1.04, y * 1.04, y], color="black", lw=1.0)
        r_val = row.get("effect_r", np.nan)
        r_str = f"  r={r_val:+.2f}" if pd.notna(r_val) else ""
        ax.text(
            (x1 + x2) / 2,
            y * 1.06,
            f"p={row['p']:.2g} ({_p_stars(row['p'])}){r_str}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
        y *= 1.18
    ax.set_ylim(top=y * 1.05 if y > 0 else None)
    ax.set_xlabel("Treatment")
    ax.set_ylabel("Lm % Reads")
    ax.set_title("Dose response at 24 h — sponge quasimetagenomic, N only\n(24h_1 + 24h_2 pooled)")
    _annotate_n(ax, len(qm_sponge_n))
    _save(fig, "fig_3a5_dose_response_24h", optional=True)


def fig_3c_extraction_kit(df: pd.DataFrame, stats_kit: pd.DataFrame) -> None:
    quasi_n = df[
        df["is_quasimeta"]
        & (df["Condition"] == "N")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()

    fig, axes = plt.subplots(1, 3, figsize=(13, 5.5), constrained_layout=True, sharey=True)
    for ax, swab in zip(axes, SWAB_ORDER):
        sub = quasi_n[quasi_n["Swab Type"] == swab]
        sns.stripplot(
            data=sub,
            x="Extraction Kit",
            y="Lm % Reads",
            hue="Extraction Kit",
            palette={"Micro": "#0072B2", "Mini": "#E69F00"},
            order=["Micro", "Mini"],
            jitter=0.2,
            size=7,
            alpha=0.85,
            ax=ax,
            legend=False,
        )
        sns.boxplot(
            data=sub,
            x="Extraction Kit",
            y="Lm % Reads",
            order=["Micro", "Mini"],
            ax=ax,
            showfliers=False,
            width=0.5,
            boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
            medianprops=dict(color="black", linewidth=1.8),
            whiskerprops=dict(color="black", linewidth=1.1),
            capprops=dict(color="black", linewidth=1.1),
        )
        row = stats_kit[
            (stats_kit["metric"] == "Lm % Reads")
            & (stats_kit["subgroup"] == f"quasimeta | N | {swab}")
        ]
        if len(row):
            r = row.iloc[0]
            ax.text(
                0.5,
                1.02,
                f"p = {r['p']:.3g} ({_p_stars(r['p'])})\nn = {int(r['n1'])}/{int(r['n2'])}",
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333",
            )
        ax.set_title(swab, pad=30)
        ax.set_xlabel("Extraction kit")
        if ax is axes[0]:
            ax.set_ylabel("Lm % Reads")
        else:
            ax.set_ylabel("")
    _add_panel_labels(list(axes))
    fig.suptitle("Micro vs Mini kit — quasimetagenomic N samples (all treatments pooled)", fontsize=13)
    _save(fig, "fig_3c_extraction_kit", optional=True)


def _pooled_sponge_n(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Sponge, N samples, treatments pooled as 'Lm-inoculated', plus 0h baseline."""
    d = _prep_quasimeta_sponge(df, metric)
    d = d[d["Condition"] == "N"].copy()
    # Deduplicate baseline rows that were triplicated across treatments
    base = d[d["timepoint"].astype(str) == "0h"].drop_duplicates(subset=["Lab ID"])
    later = d[d["timepoint"].astype(str) != "0h"]
    out = pd.concat([base, later], ignore_index=True)
    out["timepoint"] = pd.Categorical(out["timepoint"], TIMEPOINT_ORDER, ordered=True)
    out["tp_display"] = pd.Categorical(
        out["tp_display"], TIMEPOINT_DISPLAY_ORDER, ordered=True
    )
    return out


def fig_3a1p_pooled_timecourse(df: pd.DataFrame) -> None:
    data = _pooled_sponge_n(df, "Lm % Reads")

    fig, ax = plt.subplots(figsize=(9.0, 5.5), constrained_layout=True)
    sns.stripplot(
        data=data,
        x="timepoint",
        y="Lm % Reads",
        color="#0072B2",
        order=TIMEPOINT_ORDER,
        jitter=0.2,
        alpha=0.75,
        size=7,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
    )
    med = data.groupby("timepoint", observed=True)["Lm % Reads"].median().reindex(TIMEPOINT_ORDER).reset_index()
    ax.plot(
        range(len(med)),
        med["Lm % Reads"].to_numpy(),
        color="#0072B2",
        linewidth=2.4,
        marker="o",
        markersize=9,
        markeredgecolor="white",
        markeredgewidth=1.2,
        zorder=5,
        label="median",
    )
    ax.set_xlabel("Timepoint (sponge, N samples, Lm2/4/6 pooled)")
    ax.set_ylabel("Lm % Reads")
    ax.set_title("Pooled Lm time course — all spike-in levels together")
    _annotate_n(ax, len(data))
    _save(fig, "fig_3a1p_pooled_timecourse", optional=True)


def fig_3a3p_pooled_as_vs_n(df: pd.DataFrame, stats_pool: pd.DataFrame) -> None:
    q = df[
        df["is_quasimeta"]
        & (df["Swab Type"] == "Sponge")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()
    q["timepoint"] = q["timepoint"].astype(str)
    tps = ["4h", "12h", "24h (1)", "24h (2)"]

    fig, axes = plt.subplots(1, 4, figsize=(14, 5.5), constrained_layout=True, sharey=True)
    ymax = q["Lm % Reads"].max()
    headroom = ymax * 1.28 if ymax > 0 else 1.0
    stats_sub = stats_pool[
        (stats_pool["metric"] == "Lm % Reads")
        & (stats_pool["figure"] == "Fig 3a.3p (pooled AS vs N)")
    ]
    for ax, tp in zip(axes, tps):
        panel = q[q["timepoint"] == tp]
        sns.stripplot(
            data=panel,
            x="Condition",
            y="Lm % Reads",
            hue="Condition",
            palette=PALETTE_CONDITION,
            order=CONDITION_ORDER,
            jitter=0.2,
            size=8,
            alpha=0.85,
            ax=ax,
            legend=False,
        )
        sns.boxplot(
            data=panel,
            x="Condition",
            y="Lm % Reads",
            order=CONDITION_ORDER,
            ax=ax,
            showfliers=False,
            width=0.5,
            boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
            medianprops=dict(color="black", linewidth=1.8),
            whiskerprops=dict(color="black", linewidth=1.1),
            capprops=dict(color="black", linewidth=1.1),
        )
        row = stats_sub[stats_sub["subgroup"] == f"sponge | {tp} | Lm pooled"]
        if len(row):
            ax.text(
                0.5,
                1.02,
                _mwu_annotation(row.iloc[0]),
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333",
            )
        ax.set_title(tp, pad=36)
        ax.set_xlabel("Condition")
        if ax is axes[0]:
            ax.set_ylabel("Lm % Reads")
        else:
            ax.set_ylabel("")
        ax.set_ylim(top=headroom)
    _add_panel_labels(list(axes))
    fig.suptitle("AS vs N — sponge quasimetagenomic, Lm2/4/6 pooled", fontsize=13)
    _save(fig, "fig_3a3p_pooled_as_vs_n", optional=True)


def fig_3d_baseline_vs_time(df: pd.DataFrame, stats_pool: pd.DataFrame) -> None:
    data = _pooled_sponge_n(df, "Lm % Reads")

    fig, ax = plt.subplots(figsize=(9.5, 6.0), constrained_layout=True)
    sns.stripplot(
        data=data,
        x="timepoint",
        y="Lm % Reads",
        hue="timepoint",
        palette=sns.color_palette("crest", n_colors=len(TIMEPOINT_ORDER)),
        order=TIMEPOINT_ORDER,
        jitter=0.2,
        size=8,
        alpha=0.85,
        ax=ax,
        legend=False,
        edgecolor="white",
        linewidth=0.5,
    )
    sns.boxplot(
        data=data,
        x="timepoint",
        y="Lm % Reads",
        order=TIMEPOINT_ORDER,
        ax=ax,
        showfliers=False,
        width=0.55,
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
        medianprops=dict(color="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.1),
        capprops=dict(color="black", linewidth=1.1),
    )
    # Annotate 0h vs each later timepoint (one bracket per actual timepoint)
    stats_sub = stats_pool[
        (stats_pool["metric"] == "Lm % Reads")
        & (stats_pool["figure"] == "Fig 3d (baseline vs time)")
    ]
    ymax = data["Lm % Reads"].max()
    y = ymax * 1.06 if ymax > 0 else 1.0
    baseline_idx = TIMEPOINT_ORDER.index("0h")
    for tp_label in ["4h", "12h", "24h (1)", "24h (2)"]:
        row = stats_sub[stats_sub["comparison"] == f"0h vs {tp_label}"]
        if not len(row):
            continue
        r = row.iloc[0]
        x2 = TIMEPOINT_ORDER.index(tp_label)
        ax.plot([baseline_idx, baseline_idx, x2, x2], [y, y * 1.03, y * 1.03, y], color="black", lw=1.0)
        r_val = r.get("effect_r", np.nan)
        r_str = f"  r={r_val:+.2f}" if pd.notna(r_val) else ""
        ax.text(
            (baseline_idx + x2) / 2,
            y * 1.05,
            f"p={r['p']:.2g} ({_p_stars(r['p'])}){r_str}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
        y *= 1.18
    ax.set_ylim(top=y * 1.05 if y > 0 else None)
    ax.set_xlabel("Timepoint (sponge, N samples, Lm2/4/6 pooled)")
    ax.set_ylabel("Lm % Reads")
    ax.set_title("Baseline vs time — Lm detection after inoculation")
    _annotate_n(ax, len(data))
    _save(fig, "fig_3d_baseline_vs_time", optional=True)


def fig_3b1p_pooled_swab_quasimeta(df: pd.DataFrame, stats_pool: pd.DataFrame) -> None:
    q = df[
        df["is_quasimeta"]
        & (df["Condition"] == "N")
        & df["Treatment"].isin(TREATMENT_ORDER)
    ].copy()

    fig, ax = plt.subplots(figsize=(8.0, 6.0), constrained_layout=True)
    sns.stripplot(
        data=q,
        x="Swab Type",
        y="Lm % Reads",
        hue="Swab Type",
        palette=PALETTE_SWAB,
        order=SWAB_ORDER,
        jitter=0.2,
        size=7,
        alpha=0.85,
        ax=ax,
        legend=False,
    )
    sns.boxplot(
        data=q,
        x="Swab Type",
        y="Lm % Reads",
        order=SWAB_ORDER,
        ax=ax,
        showfliers=False,
        width=0.5,
        boxprops=dict(facecolor="none", edgecolor="black", linewidth=1.3),
        medianprops=dict(color="black", linewidth=1.8),
        whiskerprops=dict(color="black", linewidth=1.1),
        capprops=dict(color="black", linewidth=1.1),
    )
    stats_sub = stats_pool[
        (stats_pool["metric"] == "Lm % Reads")
        & (stats_pool["figure"] == "Fig 3b.1p (pooled quasi swab)")
    ]
    kw = stats_sub[stats_sub["comparison"] == "Kruskal-Wallis swab types"]
    if len(kw):
        r = kw.iloc[0]
        ax.text(
            0.02,
            0.97,
            f"Kruskal-Wallis H = {r['stat']:.2f}\np = {r['p']:.3g} ({_p_stars(r['p'])})",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#333",
        )
    # pairwise brackets
    pairs = stats_sub[stats_sub["comparison"].str.contains(" vs ")]
    ymax = q["Lm % Reads"].max()
    y = ymax * 1.06 if ymax > 0 else 1.0
    for _, row in pairs.iterrows():
        parts = [p.strip() for p in row["comparison"].split(" vs ")]
        if any(p not in SWAB_ORDER for p in parts):
            continue
        x1, x2 = SWAB_ORDER.index(parts[0]), SWAB_ORDER.index(parts[1])
        ax.plot([x1, x1, x2, x2], [y, y * 1.03, y * 1.03, y], color="black", lw=1.0)
        r_val = row.get("effect_r", np.nan)
        r_str = f"  r={r_val:+.2f}" if pd.notna(r_val) else ""
        ax.text(
            (x1 + x2) / 2,
            y * 1.05,
            f"p={row['p']:.2g} ({_p_stars(row['p'])}){r_str}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
        y *= 1.18
    ax.set_ylim(top=y * 1.05 if y > 0 else None)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Lm % Reads")
    ax.set_title("Swab type — quasimetagenomic N samples (Lm2/4/6 pooled)")
    _annotate_n(ax, len(q))
    _save(fig, "fig_3b1p_pooled_swab_quasimeta", optional=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Listeria analysis pipeline from a CSV or XLSX input file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Input CSV or XLSX file.",
    )
    parser.add_argument(
        "--sheet",
        default=DEFAULT_INPUT_SHEET,
        help="Worksheet name for XLSX inputs. Ignored for CSV.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root output directory for this run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_paths(input_path=args.input, sheet_name=args.sheet, output_root=args.output_root)
    _set_style()
    all_rows, df = load_clean()
    build_excel(all_rows, df)
    stats_a, stats_b, stats_trend, stats_dose, stats_kit, stats_pool, stats_timepoint, stats_swab_pool = run_stats(df)

    has_as = "AS" in set(df["Condition"].dropna().astype(str).unique())

    fig_3a1_timecourse(df)
    fig_3a2_timecourse_nstrains(df)
    if has_as:
        fig_3a3_as_vs_n_quasimeta(df, stats_a)
    else:
        print("[skip] fig_3a3_as_vs_n_quasimeta (no AS samples in input)")
    fig_3a4_strain_heatmap(df)
    fig_strain_timecourse(df)
    fig_3a5_dose_response(df, stats_dose)

    fig_3b1_swabtypes_lm_pct(df, stats_b)
    if has_as:
        fig_3b2_as_vs_n_metagenomic(df, stats_b)
    else:
        print("[skip] fig_3b2_as_vs_n_metagenomic (no AS samples in input)")
    fig_3b3_swabtypes_nstrains(df)

    fig_3c_extraction_kit(df, stats_kit)
    fig_qc_readlength_enrichment(df)
    fig_ivanovii_supplements(df, stats_a, stats_b)

    # Pooled Lm (Lm2/4/6 treated as a single inoculated group)
    fig_3a1p_pooled_timecourse(df)
    if has_as:
        fig_3a3p_pooled_as_vs_n(df, stats_pool)
    else:
        print("[skip] fig_3a3p_pooled_as_vs_n (no AS samples in input)")
    fig_3d_baseline_vs_time(df, stats_pool)
    fig_3b1p_pooled_swab_quasimeta(df, stats_pool)

    print("\n=== Summary ===")
    for name, table in [
        ("3a AS vs N (sponge quasi, per dose)", stats_a),
        ("3b AS vs N + swab comp (metagen)", stats_b),
        ("3a trend (N, per dose)", stats_trend),
        ("3a dose-response (N, 24h)", stats_dose),
        ("3c kit (quasimeta N)", stats_kit),
        ("POOLED (Lm2/4/6 together)", stats_pool),
    ]:
        n_tests = (table["metric"] == "Lm % Reads").sum()
        n_sig = ((table["p"] < 0.05) & (table["metric"] == "Lm % Reads")).sum()
        print(f"  {name}: {n_sig}/{n_tests} Lm % Reads significant (raw p<0.05)")
    print("\nDone.")


if __name__ == "__main__":
    main()
