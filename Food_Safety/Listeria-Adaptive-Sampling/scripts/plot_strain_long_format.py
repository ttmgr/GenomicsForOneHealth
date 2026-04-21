#!/usr/bin/env python3
"""Plot Listeria strain-level results from the long-format cluster output.

Reads `listeria_final_final_strain/strain_proportions_master_5.csv`
(produced by `listeria_as/scripts/82_strain_summary_background.py` after the
expanded 14-genome competitive minimap2 rerun) and produces four focused
publication figures plus a clean MWU Excel workbook.

Schema note: the cluster output is LONG format (one row per basename × strain)
with 14 strains in 3 tiers (4 L. monocytogenes, 3 non-mono Listeria, 7
background species). `round` encodes the sequencing batch, which maps to
timepoints as: R1=0h (metagenomics), R3=4h, R5=12h, R2=24h(1), R4=24h(2).

Usage:
    python scripts/plot_strain_long_format.py \\
        --input listeria_final_final_strain/strain_proportions_master_5.csv \\
        --output-root outputs/pi_revision_v2
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MPL_CONFIG_DIR = ROOT / ".matplotlib-cache"
MPL_CONFIG_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_listeria_publication_v4 import (  # noqa: E402
    boxplot_manual,
    jstrip,
    mwu_pr,
    safe_top,
)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_INPUT = ROOT / "final_round" / "processing" / "strain_analysis" / "strain_proportions_master_5.csv"
DEFAULT_READ_METRICS = ROOT / "final_round" / "processing" / "stats" / "read_metrics_summary.csv"
DEFAULT_MISMAPPING = ROOT / "listeria_final_final_strain" / "mismapping_control_5.csv"
DEFAULT_SAMPLE_METADATA = ROOT / "sample_metadata_v3.csv"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "pi_revision_v4"

TREATMENT_ORDER = ["Lm2", "Lm4", "Lm6"]
PALETTE_TREATMENT = {"Lm2": "#0072B2", "Lm4": "#009E73", "Lm6": "#D55E00"}

LM_STRAINS = ["EGDe", "LL195", "LMNC326", "N13-0119"]
NONMONO_SPECIES = ["L_innocua_J5051", "L_ivanovii_Nr26", "L_welshimeri_Nr14"]
BACKGROUND_SPECIES = [
    "B_cereus",
    "B_subtilis",
    "E_coli",
    "P_aeruginosa",
    "P_mirabilis",
    "R_equi",
    "S_aureus",
    "Y_enterocolitica",
    "Y_frederiksenii",
]
ALL_STRAINS = LM_STRAINS + NONMONO_SPECIES + BACKGROUND_SPECIES

ROUND_TO_TIMEPOINT = {1: "0h", 3: "4h", 5: "12h", 2: "24h (1)", 4: "24h (2)"}
TP_ORDER = ["0h", "4h", "12h", "24h (1)", "24h (2)"]
TP_HOURS = [0, 4, 12, 24, 26]  # 24h(2) nudged for x-axis display

SWAB_ORDER = ["Sponge", "Cotton", "Zymo"]

# Okabe-Ito palette (colourblind-safe)
PALETTE_LM_STRAIN = {
    "EGDe":     "#0072B2",
    "LL195":    "#D55E00",
    "LMNC326":  "#009E73",
    "N13-0119": "#CC79A7",
}
LM_STRAIN_MARKERS = {
    "EGDe":     "o",
    "LL195":    "s",
    "LMNC326":  "D",
    "N13-0119": "^",
}
PALETTE_CONDITION = {"AS": "#C0392B", "N": "#2471A3"}
COND_MARKERS = {"AS": "D", "N": "o"}
PALETTE_SWAB = {"Sponge": "#2E75B6", "Cotton": "#C55A11", "Zymo": "#7030A0"}
PALETTE_TIER = {
    "L_monocytogenes": "#D55E00",
    "non_mono":        "#0072B2",
    "background":      "#8C8C8C",
}

SAVE_FORMATS = ("png", "pdf")


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 12,
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 10,
        "axes.linewidth": 0.9,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
def _classify(strain: str) -> str:
    if strain in LM_STRAINS:
        return "L_monocytogenes"
    if strain in NONMONO_SPECIES:
        return "non_mono"
    if strain in BACKGROUND_SPECIES:
        return "background"
    return "unknown"


def load_strain_long(
    input_csv: Path,
    read_metrics_csv: Path | None = None,
    sample_metadata_csv: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load strain_proportions_master_5.csv and return (long_df, wide_sample_df).

    If ``read_metrics_csv`` is provided and contains a ``number_of_reads`` column
    per basename (NanoStat output), the wide frame gets a ``lm_pct_total_reads``
    column defined as ``100 * lm_total_reads / number_of_reads`` — directly
    comparable to the pre-rerun ``Lm % Reads`` metric.
    """
    long = pd.read_csv(input_csv)
    print(f"[load] {input_csv} ({len(long)} rows, "
          f"{long['basename'].nunique()} basenames, {long['strain'].nunique()} strains)")

    # Drop rows with all-NaN cluster metadata (round/cohort/group/condition).
    # In the final_round run, r1_barcode31/32/33 AS/N have no sample-sheet
    # entry and show up as untagged metagenomic background reads; they were
    # never production samples for any of Lara's figures.
    orphan = long["round"].isna()
    if orphan.any():
        n_orphan = long.loc[orphan, "basename"].nunique()
        print(f"[load] dropping {n_orphan} basenames with NaN metadata (orphans from cluster sample sheet)")
        long = long[~orphan].copy()
    long["round"] = long["round"].astype(int)

    # Classify strains into tiers (authoritative; overrides any CSV value)
    long["species_group"] = long["strain"].apply(_classify)

    # Tag (but do NOT drop) samples with swab_type == "-". These are the four
    # R4 background rows (r4_barcode95/96 AS/N) that have no swab assignment
    # and are the only post-rerun record of R4 background residual Lm; we
    # keep them so the background sanity figure can show them. Downstream
    # swab-based filters naturally exclude them.
    bad_swab = long["swab_type"].astype(str).isin(["-"])
    if bad_swab.any():
        n_bad = long.loc[bad_swab, "basename"].nunique()
        print(f"[load] keeping {n_bad} basenames with swab_type='-' (R4 background)")
        long.loc[bad_swab, "swab_type"] = "none"

    # Normalise Zymo label (R1-R2 used "Zymo_swab", R3-R5 uses "Zymo")
    long["swab_type"] = long["swab_type"].replace({"Zymo_swab": "Zymo"})

    # Mark Control_Lm as positive controls so downstream filters can skip them
    long["is_control"] = long["group"].astype(str) == "Control_Lm"

    # Derive timepoint from round
    long["timepoint"] = long["round"].map(ROUND_TO_TIMEPOINT)
    long["timepoint"] = pd.Categorical(long["timepoint"], TP_ORDER, ordered=True)

    # Long → wide: per-sample row with one column per strain
    wide = long.pivot_table(
        index="basename",
        columns="strain",
        values="mapped_reads",
        aggfunc="sum",
        fill_value=0,
    )
    # Ensure all expected columns exist (even if a strain is absent in some subset)
    for s in ALL_STRAINS:
        if s not in wide.columns:
            wide[s] = 0
    wide = wide[ALL_STRAINS]

    # Same pivot on mapped_bases so we can compute a base-fraction metric that
    # mirrors lm_pct_total_reads. Nanopore read length is roughly comparable
    # across species in the panel, so the base-% metric tracks the read-%
    # metric closely and exists as a confirmatory view.
    bases_wide = long.pivot_table(
        index="basename",
        columns="strain",
        values="mapped_bases",
        aggfunc="sum",
        fill_value=0,
    )
    for s in LM_STRAINS:
        if s not in bases_wide.columns:
            bases_wide[s] = 0
    wide["lm_total_bases"] = bases_wide[LM_STRAINS].sum(axis=1)

    # Preserve per-strain bases for the non-Lm Listeria species so the
    # species-timecourse bases variant can compute individual species base
    # fractions. The column name is `<strain>_bases` (e.g. L_innocua_J5051_bases).
    for s in NONMONO_SPECIES:
        if s in bases_wide.columns:
            wide[f"{s}_bases"] = bases_wide[s]
        else:
            wide[f"{s}_bases"] = 0

    # Total reads = sum over all 16 strains in the panel (NOT total sequencer reads).
    # This is the denominator for "abundance within the reference panel".
    wide["total_panel_reads"] = wide[ALL_STRAINS].sum(axis=1)
    wide["lm_total_reads"] = wide[LM_STRAINS].sum(axis=1)
    wide["nonmono_total_reads"] = wide[NONMONO_SPECIES].sum(axis=1)
    wide["background_total_reads"] = wide[BACKGROUND_SPECIES].sum(axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        # Panel-relative (tiers sum to 100 % per sample — used for the
        # background sanity-check stacked bars where the 14-genome panel IS
        # the denominator of interest).
        wide["lm_pct_panel"] = 100.0 * wide["lm_total_reads"] / wide["total_panel_reads"]
        wide["nonmono_pct_panel"] = 100.0 * wide["nonmono_total_reads"] / wide["total_panel_reads"]
        wide["background_pct_panel"] = 100.0 * wide["background_total_reads"] / wide["total_panel_reads"]
        # Within-Lm composition (each Lm strain as % of the 4-Lm-strain pool,
        # independent of denominator choice).
        for s in LM_STRAINS:
            wide[f"{s}_pct_within_lm"] = 100.0 * wide[s] / wide["lm_total_reads"]
    wide = wide.replace([np.inf, -np.inf], np.nan)

    # Join sample-level metadata (one row per basename)
    meta_cols = [
        "round", "timepoint", "condition", "cohort", "group",
        "swab_type", "kit", "dna_concentration_ng_ul", "is_control",
    ]
    meta = long.drop_duplicates("basename")[["basename", *meta_cols]].set_index("basename")
    wide = wide.join(meta)

    # Join total sequenced read counts (from NanoStat) so we can compute the
    # old-style "Lm / total reads" metric — directly comparable to the
    # pre-rerun foodsafety `Lm % Reads` column.
    if read_metrics_csv is not None and read_metrics_csv.exists():
        rm = pd.read_csv(read_metrics_csv)
        if "sample" in rm.columns and "number_of_reads" in rm.columns:
            rm = rm[["sample", "number_of_reads", "total_bases"]].rename(
                columns={"sample": "basename",
                         "number_of_reads": "total_sample_reads",
                         "total_bases": "total_sample_bases"}
            )
            wide = wide.join(rm.set_index("basename"))
            with np.errstate(divide="ignore", invalid="ignore"):
                wide["lm_pct_total_reads"] = 100.0 * wide["lm_total_reads"] / wide["total_sample_reads"]
                wide["lm_pct_sample_bases"] = 100.0 * wide["lm_total_bases"] / wide["total_sample_bases"]
                for s in LM_STRAINS:
                    wide[f"{s}_pct_sample_total"] = 100.0 * wide[s] / wide["total_sample_reads"]
            wide = wide.replace([np.inf, -np.inf], np.nan)
            print(f"[load] joined read metrics from {read_metrics_csv.name}; "
                  f"computed 'lm_pct_total_reads' and 'lm_pct_sample_bases'")
        else:
            print(f"[warn] {read_metrics_csv} missing expected columns; skipping total-reads join")
    else:
        raise SystemExit(
            f"Missing read_metrics_summary.csv at {read_metrics_csv}. "
            "This file is required to compute the pre-rerun-comparable "
            "`Lm % Reads` metric. Drop the cluster `processing/stats/"
            "read_metrics_summary.csv` into the same directory as the "
            "strain_proportions_master_5.csv."
        )

    wide = wide.reset_index()
    wide["timepoint"] = pd.Categorical(wide["timepoint"], TP_ORDER, ordered=True)

    # Treatment (Lm2/Lm4/Lm6/Blank/Background) comes either from the
    # cluster-side `group` column directly (the final_round run already has
    # Lm2/Lm4/Lm6 in `group`) or from a fallback join with
    # sample_metadata_v3.csv (the earlier listeria_final_final_strain run put
    # cohort-swab codes in `group` instead, so Treatment had to be joined in).
    group_vals = set(str(g) for g in wide.get("group", pd.Series(dtype=str)).dropna().unique())
    cluster_native = bool(group_vals & set(TREATMENT_ORDER))
    if cluster_native:
        wide["Treatment"] = wide["group"].astype(str)
        wide.loc[wide["is_control"].fillna(False), "Treatment"] = "Control_Lm"
        print(f"[load] using cluster `group` column as Treatment; counts: "
              f"{dict(wide['Treatment'].value_counts(dropna=False))}")
    elif sample_metadata_csv is not None and sample_metadata_csv.exists():
        meta = pd.read_csv(sample_metadata_csv)
        slim = meta[["basename", "cohort", "group"]].rename(
            columns={"cohort": "sample_type_meta", "group": "Treatment"}
        ).drop_duplicates("basename")
        wide = wide.merge(slim, on="basename", how="left")
        ctrl_mask = wide["is_control"].fillna(False)
        wide.loc[ctrl_mask & wide["Treatment"].isna(), "Treatment"] = "Control_Lm"
        r4bg_mask = (wide["swab_type"] == "none") & wide["Treatment"].isna()
        wide.loc[r4bg_mask, "Treatment"] = "Background"
        n_missing = wide["Treatment"].isna().sum()
        if n_missing:
            print(f"[warn] {n_missing} basenames still missing Treatment after metadata join")
        print(f"[load] joined sample_metadata_v3.csv; Treatment counts: "
              f"{dict(wide['Treatment'].value_counts(dropna=False))}")

    if "Treatment" in wide.columns:
        wide["Treatment"] = pd.Categorical(
            wide["Treatment"],
            TREATMENT_ORDER + ["Control_Lm", "Background", "Blank"],
        )

    return long, wide


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------
def _save(fig: plt.Figure, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in SAVE_FORMATS:
        fig.savefig(out_dir / f"{stem}.{ext}")
    print(f"[fig] wrote {out_dir / stem}.{{png,pdf}}")


def _stars(p: float | None) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def _bh_adjust(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out.tolist()


def _dotplot_small_n(
    ax,
    x_center: float,
    vals,
    color: str,
    marker: str = "o",
    seed: int = 0,
    width: float = 0.38,
) -> None:
    """Dot plot for small-n groups — jittered raw points + short mean bar.

    Used in place of boxplot_manual where each group has only n ≈ 2 replicates
    (the per-Lm-stratified AS-vs-N figures), because box/IQR/whisker summaries
    are degenerate at n = 2 and visually misleading.
    """
    vals_arr = np.asarray(vals, dtype=float)
    vals_arr = vals_arr[~np.isnan(vals_arr)]
    if len(vals_arr) == 0:
        return
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-width * 0.25, width * 0.25, size=len(vals_arr))
    ax.scatter(
        np.full(len(vals_arr), x_center) + jitter,
        vals_arr,
        color=color,
        s=56,
        alpha=0.9,
        marker=marker,
        edgecolor="black",
        linewidths=0.7,
        zorder=3,
    )
    mean_val = float(vals_arr.mean())
    half = width / 2
    ax.plot(
        [x_center - half, x_center + half],
        [mean_val, mean_val],
        color=color,
        lw=2.4,
        solid_capstyle="butt",
        zorder=4,
    )


# ---------------------------------------------------------------------------
# Figure 1 — per-strain relative abundance across the quasimeta timeline
# ---------------------------------------------------------------------------
def fig_strain_timecourse_by_strain(wide: pd.DataFrame, out_dir: Path) -> None:
    """Two-panel figure: absolute abundance + within-Lm composition per timepoint.

    Subset: Sponge swab, N condition, non-control samples only. Follows Lara's
    ask for 'relative abundance across the quasimetagenomic timeline for the
    four Listeria strains (four different colors in the same plot)'.
    """
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, (ax_abs, ax_rel) = plt.subplots(1, 2, figsize=(15, 7.2))
    rng = np.random.default_rng(123)

    def _draw(ax, metric_col_tpl: str, ylabel: str, title: str) -> None:
        for strain in LM_STRAINS:
            col = metric_col_tpl.format(strain=strain)
            colour = PALETTE_LM_STRAIN[strain]
            marker = LM_STRAIN_MARKERS[strain]
            xs: list[float] = []
            means: list[float] = []
            sems: list[float] = []
            for tp_idx, tp in enumerate(TP_ORDER):
                vals = sub.loc[sub["timepoint"] == tp, col].dropna().to_numpy()
                if not len(vals):
                    continue
                xs.append(tp_idx)
                means.append(float(vals.mean()))
                sems.append(
                    float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
                )
                jitter = rng.uniform(-0.14, 0.14, size=len(vals))
                ax.scatter(
                    np.full(len(vals), tp_idx) + jitter,
                    vals,
                    color=colour,
                    s=18,
                    alpha=0.35,
                    zorder=2,
                    linewidths=0,
                )
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2,
                marker=marker, markersize=7,
                capsize=3.5, zorder=5,
                markeredgecolor="white", markeredgewidth=0.8,
                label=strain,
            )
        ax.set_xticks(range(len(TP_ORDER)))
        ax.set_xticklabels(TP_ORDER, rotation=25, ha="right")
        ax.set_xlabel("Sponge quasimetagenomic timepoint (N samples, round → timepoint)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.set_ylim(bottom=0)

    _draw(
        ax_abs,
        "{strain}_pct_sample_total",
        "Strain reads / total sample reads (%)",
        "Absolute strain abundance (= classic 'Lm % Reads' per strain)",
    )
    _draw(
        ax_rel,
        "{strain}_pct_within_lm",
        "Strain reads / Lm-mapped reads (%)",
        "Relative strain composition (within Lm pool)",
    )
    # Legend below, centered between the two panels. n is folded into the
    # legend title so we don't need a separate corner annotation.
    handles, labels = ax_abs.get_legend_handles_labels()
    n_samples = sub["basename"].nunique()
    fig.legend(
        handles, labels,
        title=f"L. monocytogenes strain  (n = {n_samples})",
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=len(LM_STRAINS),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    fig.suptitle(
        "Per-strain relative abundance across the quasimetagenomic timeline",
        fontsize=14,
    )
    # Reserve ~14% at the bottom for legend + rotated x-labels, ~5% at the top
    # for the suptitle. No constrained_layout — fig.legend outside the axes
    # interacts badly with it.
    fig.subplots_adjust(left=0.07, right=0.98, top=0.92, bottom=0.18, wspace=0.22)
    _save(fig, out_dir, "fig_strain_timecourse_by_strain")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 — background sanity check
# ---------------------------------------------------------------------------
def fig_background_sanity_check(
    wide: pd.DataFrame,
    out_dir: Path,
    mismapping_csv: Path | None = None,
) -> None:
    """Stacked bars per sample for positive (Control_Lm) and negative (S13_S14)
    control samples, showing tier-level read allocation after the 14-genome
    competitive mapping.

    The critical row is the negative control at the bottom: a pure
    L. welshimeri / L. innocua mix that should NOT map to L. monocytogenes.
    Pre-rerun (4-genome reference), that mix produced ~80k false-positive
    Lm reads; with MAPQ >= 60, still ~14k. The 14-genome panel should drop
    this close to zero.
    """
    ctrl = wide[wide["is_control"]].copy()
    rows: list[tuple[str, float, float, float, str]] = []

    for _, r in ctrl.sort_values(["round", "condition", "basename"]).iterrows():
        label = f"R{int(r['round'])} {r['basename']} [{r['condition']}]"
        rows.append((
            label,
            float(r["lm_pct_panel"]),
            float(r["nonmono_pct_panel"]),
            float(r["background_pct_panel"]),
            "positive",
        ))

    # Negative control from mismapping_control_5.csv (S13_S14 pure welshimeri+innocua mix)
    if mismapping_csv is not None and mismapping_csv.exists():
        mis = pd.read_csv(mismapping_csv)
        for basename, sub in mis.groupby("basename"):
            total = float(sub["mapped_reads"].sum())
            if total <= 0:
                continue
            lm = float(sub.loc[sub["species_group"] == "L_monocytogenes", "mapped_reads"].sum())
            nm = float(sub.loc[sub["species_group"] == "non_mono", "mapped_reads"].sum())
            bg = float(sub.loc[sub["species_group"] == "background", "mapped_reads"].sum())
            rows.append((
                f"NEG {basename} (welshimeri+innocua)",
                100.0 * lm / total,
                100.0 * nm / total,
                100.0 * bg / total,
                "negative",
            ))

    if not rows:
        print("[warn] no control or negative samples found; skipping background sanity check")
        return

    labels, lm_pct, nm_pct, bg_pct, kinds = zip(*rows)
    lm_pct = np.asarray(lm_pct)
    nm_pct = np.asarray(nm_pct)
    bg_pct = np.asarray(bg_pct)

    n = len(labels)
    fig, ax = plt.subplots(figsize=(13, max(5.0, 0.38 * n + 1.8)))
    y = np.arange(n)

    ax.barh(y, lm_pct, color=PALETTE_TIER["L_monocytogenes"],
            edgecolor="white", linewidth=0.6, label="L. monocytogenes (4 strains)")
    ax.barh(y, nm_pct, left=lm_pct, color=PALETTE_TIER["non_mono"],
            edgecolor="white", linewidth=0.6, label="non-mono Listeria (3 species)")
    ax.barh(y, bg_pct, left=lm_pct + nm_pct, color=PALETTE_TIER["background"],
            edgecolor="white", linewidth=0.6, label="background species (7 species)")

    # Mark negative-control tick labels in red for visual emphasis
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    for i, (tick, kind) in enumerate(zip(ax.get_yticklabels(), kinds)):
        if kind == "negative":
            tick.set_color("#B22222")
            tick.set_fontweight("bold")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Proportion of panel-mapped reads (%)")
    ax.set_title(
        "Background sanity check — control samples after 14-genome competitive mapping\n"
        "Pre-rerun (4-genome): negative control had ~80 000 false-positive Lm reads; MAPQ≥60 still ~14 000.",
        fontsize=11,
    )
    ax.invert_yaxis()
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    pos_mask = np.array([k == "positive" for k in kinds])
    pos_lm_mean = float(lm_pct[pos_mask].mean()) if pos_mask.any() else float("nan")
    neg_mask = ~pos_mask
    neg_lm_mean = float(lm_pct[neg_mask].mean()) if neg_mask.any() else float("nan")
    txt = (
        f"Mean Lm / panel %:\n"
        f"  positive ctrl: {pos_lm_mean:5.2f} %\n"
        f"  NEG ctrl:      {neg_lm_mean:5.2f} %"
    )
    ax.text(
        1.02, 0.0, txt,
        transform=ax.transAxes, ha="left", va="bottom",
        fontsize=8, family="monospace", color="#333",
    )
    fig.tight_layout(rect=[0, 0, 0.78, 1])
    _save(fig, out_dir, "fig_background_sanity_check")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 — metagenomic AS vs N per swab type (R1 = 0h metagenomics only)
# ---------------------------------------------------------------------------
def fig_AS_vs_N_per_swab_metagenomic(wide: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """AS vs N boxplots per swab type on metagenomic (R1) samples only.

    Returns the stats table used for annotations so it can be folded into
    the MWU Excel.
    """
    meta = wide[
        (wide["round"] == 1)
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    y_all: list[float] = []
    for i, swab in enumerate(SWAB_ORDER):
        sub = meta[meta["swab_type"] == swab]
        as_v = sub.loc[sub["condition"] == "AS", "lm_pct_total_reads"].dropna()
        n_v = sub.loc[sub["condition"] == "N", "lm_pct_total_reads"].dropna()
        boxplot_manual(
            ax, i - 0.22, as_v, PALETTE_CONDITION["AS"],
            width=0.38, marker=COND_MARKERS["AS"], seed=i * 13,
        )
        boxplot_manual(
            ax, i + 0.22, n_v, PALETTE_CONDITION["N"],
            width=0.38, marker=COND_MARKERS["N"], seed=i * 13 + 1,
        )
        y_all.extend(as_v.tolist() + n_v.tolist())

    y_ref = safe_top(y_all, 1.10)
    stats_rows = []
    for i, swab in enumerate(SWAB_ORDER):
        sub = meta[meta["swab_type"] == swab]
        p_v, r_v, n1, n2 = mwu_pr(
            sub.loc[sub["condition"] == "AS", "lm_pct_total_reads"],
            sub.loc[sub["condition"] == "N", "lm_pct_total_reads"],
        )
        med_as = float(sub.loc[sub["condition"] == "AS", "lm_pct_total_reads"].median()) if n1 else np.nan
        med_n  = float(sub.loc[sub["condition"] == "N", "lm_pct_total_reads"].median()) if n2 else np.nan
        stats_rows.append({
            "figure": "Fig 3 (AS vs N, metagenomic per swab)",
            "comparison": "AS vs N",
            "subgroup": f"metagenomic | {swab}",
            "metric": "lm_pct_total_reads",
            "n1": n1, "n2": n2,
            "median1": med_as, "median2": med_n,
            "U": np.nan,
            "p": p_v,
            "effect_r": r_v,
        })

    ax.set_xticks(range(len(SWAB_ORDER)))
    ax.set_xticklabels(SWAB_ORDER)
    ax.set_xlim(-0.65, len(SWAB_ORDER) - 0.35)
    ax.set_ylim(bottom=0, top=y_ref * 1.15 if y_ref > 0 else 1.0)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Lm reads / total sample reads (%)")
    ax.set_title("AS vs N — metagenomic samples (round 1), per swab type", fontsize=11)
    ax.legend(
        handles=[
            mpatches.Patch(color=PALETTE_CONDITION["AS"], label="Adaptive Sampling (AS)"),
            mpatches.Patch(color=PALETTE_CONDITION["N"],  label="Native (N)"),
        ],
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )
    fig.tight_layout(rect=[0, 0, 0.85, 1])
    _save(fig, out_dir, "fig_AS_vs_N_per_swab_metagenomic")
    plt.close(fig)

    df = pd.DataFrame(stats_rows)
    df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
    df["sig"] = df["p"].apply(_stars)
    df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


# ---------------------------------------------------------------------------
# Figure 4 — N-only swab-type comparison (metagenomic, R1)
# ---------------------------------------------------------------------------
def fig_swab_comparison_N_only(wide: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    meta_n = wide[
        (wide["round"] == 1)
        & (wide["condition"] == "N")
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    y_all: list[float] = []
    for i, swab in enumerate(SWAB_ORDER):
        vals = meta_n.loc[meta_n["swab_type"] == swab, "lm_pct_total_reads"].dropna()
        boxplot_manual(
            ax, i, vals, PALETTE_SWAB[swab],
            width=0.55, marker="o", seed=i * 11,
        )
        y_all.extend(vals.tolist())

    y_max = safe_top(y_all, 1.10)
    pairs = list(combinations(range(len(SWAB_ORDER)), 2))

    stats_rows = []
    for i, j in pairs:
        s1, s2 = SWAB_ORDER[i], SWAB_ORDER[j]
        g1 = meta_n.loc[meta_n["swab_type"] == s1, "lm_pct_total_reads"]
        g2 = meta_n.loc[meta_n["swab_type"] == s2, "lm_pct_total_reads"]
        p_v, r_v, n1, n2 = mwu_pr(g1, g2)
        stats_rows.append({
            "figure": "Fig 4 (swab pairwise, metagenomic N)",
            "comparison": f"{s1} vs {s2}",
            "subgroup": "metagenomic | N",
            "metric": "lm_pct_total_reads",
            "n1": n1, "n2": n2,
            "median1": float(g1.median()) if len(g1) else np.nan,
            "median2": float(g2.median()) if len(g2) else np.nan,
            "U": np.nan,
            "p": p_v,
            "effect_r": r_v,
        })

    ax.set_xticks(range(len(SWAB_ORDER)))
    ax.set_xticklabels(SWAB_ORDER)
    ax.set_xlim(-0.55, len(SWAB_ORDER) - 0.45)
    ax.set_ylim(bottom=0, top=y_max * 1.15 if y_max > 0 else 1.0)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Lm reads / total sample reads (%)")
    ax.set_title("Swab-type comparison — metagenomic samples, N only (round 1)", fontsize=11)
    ax.legend(
        handles=[mpatches.Patch(color=PALETTE_SWAB[s], label=s) for s in SWAB_ORDER],
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )
    fig.tight_layout(rect=[0, 0, 0.85, 1])
    _save(fig, out_dir, "fig_swab_comparison_N_only")
    plt.close(fig)

    df = pd.DataFrame(stats_rows)
    df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
    df["sig"] = df["p"].apply(_stars)
    df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


# ---------------------------------------------------------------------------
# Figure 5 — per-Lm-level N-only sponge timecourse (PI revision ask)
# ---------------------------------------------------------------------------
def fig_timecourse_N_sponge_per_Lm(wide: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """Three-panel N-only sponge timecourse, one per Lm spiking level.

    Replicates are kept as independent data points; 24h (1) and 24h (2) are
    drawn at separate x positions. Per-panel means are shown with SEM bars
    computed as std(ddof=1) / sqrt(n). Mann-Whitney U p-values and rank-
    biserial r are annotated only where a pairwise timepoint contrast is
    significant (raw p < 0.05).
    """
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=False)
    rng = np.random.default_rng(321)
    stats_rows: list[dict] = []

    for ax, tr in zip(axes, TREATMENT_ORDER):
        data = sub[sub["Treatment"] == tr]
        colour = PALETTE_TREATMENT[tr]
        xs: list[float] = []
        means: list[float] = []
        sems: list[float] = []
        values_by_tp: dict[str, np.ndarray] = {}
        for tp_idx, tp in enumerate(TP_ORDER):
            vals = data.loc[data["timepoint"] == tp, "lm_pct_total_reads"].dropna().to_numpy()
            values_by_tp[tp] = vals
            if not len(vals):
                continue
            xs.append(tp_idx)
            means.append(float(vals.mean()))
            sems.append(
                float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            )
            jitter = rng.uniform(-0.14, 0.14, size=len(vals))
            ax.scatter(
                np.full(len(vals), tp_idx) + jitter, vals,
                color=colour, s=22, alpha=0.45, zorder=2, linewidths=0,
            )

        if xs:
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2, marker="o", markersize=7,
                capsize=3.5, zorder=5,
                markeredgecolor="white", markeredgewidth=0.8,
            )

        # Pairwise MWU between timepoints for this treatment
        for t1, t2 in combinations(TP_ORDER, 2):
            a, b = values_by_tp.get(t1, np.array([])), values_by_tp.get(t2, np.array([]))
            if len(a) < 2 or len(b) < 2:
                p_v, r_v = np.nan, np.nan
            else:
                p_v, r_v, _, _ = mwu_pr(pd.Series(a), pd.Series(b))
            stats_rows.append({
                "figure": "Fig 5 (per-Lm sponge N timecourse)",
                "comparison": f"{t1} vs {t2}",
                "subgroup": f"sponge | N | {tr}",
                "metric": "lm_pct_total_reads",
                "n1": int(len(a)), "n2": int(len(b)),
                "median1": float(np.median(a)) if len(a) else np.nan,
                "median2": float(np.median(b)) if len(b) else np.nan,
                "U": np.nan,
                "p": p_v,
                "effect_r": r_v,
                "Treatment": tr,
            })

        ymax = 0.0
        for v in values_by_tp.values():
            if len(v):
                ymax = max(ymax, float(np.nanmax(v)))

        ax.set_xticks(range(len(TP_ORDER)))
        ax.set_xticklabels(TP_ORDER, rotation=25, ha="right")
        ax.set_xlabel("Sponge quasimetagenomic timepoint")
        if tr == TREATMENT_ORDER[0]:
            ax.set_ylabel("Lm reads / total sample reads (%)")
        ax.set_title(f"{tr} (N, sponge)  n={int(data['basename'].nunique())}", fontsize=11)
        ax.set_ylim(bottom=0)
        if ymax > 0:
            ax.set_ylim(top=ymax * 1.10)

    fig.suptitle(
        "Sponge quasimetagenomic timecourse, N only — stratified by Lm spiking level",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, out_dir, "fig_timecourse_N_sponge_per_Lm")
    plt.close(fig)

    df = pd.DataFrame(stats_rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


# ---------------------------------------------------------------------------
# Figure 6 — per-Lm-level AS vs N sponge quasimetagenomic (PI revision ask)
# ---------------------------------------------------------------------------
def fig_AS_vs_N_sponge_per_Lm(wide: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """One figure per Lm spiking level: AS vs N at each quasimeta timepoint.

    Sponge swab only, quasimetagenomic rounds only (R3/R5/R2/R4). 24h (1)
    and 24h (2) kept as separate x positions. p and r annotated only where
    the raw contrast is significant.
    """
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
        & (wide["timepoint"] != "0h")  # quasimeta only
    ].copy()
    stats_rows: list[dict] = []

    for tr in TREATMENT_ORDER:
        data = sub[sub["Treatment"] == tr]
        tps_present = [tp for tp in TP_ORDER if tp != "0h" and (data["timepoint"] == tp).any()]
        if not tps_present:
            continue
        fig, ax = plt.subplots(figsize=(2.7 * len(tps_present) + 2.5, 5.4))
        y_all: list[float] = []
        for i, tp in enumerate(tps_present):
            tp_data = data[data["timepoint"] == tp]
            as_v = tp_data.loc[tp_data["condition"] == "AS", "lm_pct_total_reads"].dropna()
            n_v = tp_data.loc[tp_data["condition"] == "N", "lm_pct_total_reads"].dropna()
            _dotplot_small_n(
                ax, i - 0.22, as_v, PALETTE_CONDITION["AS"],
                width=0.38, marker=COND_MARKERS["AS"], seed=i * 7,
            )
            _dotplot_small_n(
                ax, i + 0.22, n_v, PALETTE_CONDITION["N"],
                width=0.38, marker=COND_MARKERS["N"], seed=i * 7 + 1,
            )
            y_all.extend(as_v.tolist() + n_v.tolist())

            p_v, r_v, n1, n2 = mwu_pr(as_v, n_v)
            stats_rows.append({
                "figure": f"Fig 6 ({tr} AS vs N sponge per timepoint)",
                "comparison": "AS vs N",
                "subgroup": f"sponge | {tp} | {tr}",
                "metric": "lm_pct_total_reads",
                "n1": n1, "n2": n2,
                "median1": float(as_v.median()) if len(as_v) else np.nan,
                "median2": float(n_v.median()) if len(n_v) else np.nan,
                "U": np.nan,
                "p": p_v,
                "effect_r": r_v,
                "Treatment": tr,
            })

        y_ref = safe_top(y_all, 1.10)

        ax.set_xticks(range(len(tps_present)))
        ax.set_xticklabels(tps_present)
        ax.set_xlim(-0.65, len(tps_present) - 0.35)
        ax.set_ylim(bottom=0, top=y_ref * 1.15 if y_ref > 0 else 1.0)
        ax.set_xlabel("Sponge quasimetagenomic timepoint")
        ax.set_ylabel("Lm reads / total sample reads (%)")
        ax.set_title(f"AS vs N — sponge quasimetagenomic, {tr}", fontsize=11)
        ax.legend(
            handles=[
                mpatches.Patch(color=PALETTE_CONDITION["AS"], label="Adaptive Sampling (AS)"),
                mpatches.Patch(color=PALETTE_CONDITION["N"],  label="Native (N)"),
            ],
            loc="upper left", bbox_to_anchor=(1.02, 1.0),
            frameon=False, fontsize=9,
        )
        fig.tight_layout(rect=[0, 0, 0.85, 1])
        _save(fig, out_dir, f"fig_AS_vs_N_sponge_{tr}")
        plt.close(fig)

    df = pd.DataFrame(stats_rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


# ---------------------------------------------------------------------------
# Figure 7 — AS vs N sponge quasimetagenomic, Lm2-6 pooled (old-design style)
# ---------------------------------------------------------------------------
def fig_AS_vs_N_sponge_quasimeta(wide: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """AS vs N on sponge quasimetagenomic samples, Lm2/Lm4/Lm6 pooled.

    Replaces the per-Lm-stratified ``fig_AS_vs_N_sponge_per_Lm`` figures, which
    had n = 2 per box and produced degenerate boxplots. Pooling the three
    spiking levels gives n = 6–8 per box, allowing meaningful box/IQR
    summaries, and matches the style of the old 13-April publication plots
    (soft pastel fills, jstrip overlay with AS = diamond / N = circle,
    legend outside top-right). Replicates remain independent data points
    — they are stacked, not averaged.
    """
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
        & (wide["timepoint"] != "0h")  # quasimeta only
    ].copy()

    tps = [tp for tp in TP_ORDER if tp != "0h" and (sub["timepoint"] == tp).any()]
    n_tps = len(tps)

    fig, ax = plt.subplots(figsize=(2.7 * n_tps + 3.2, 6.4))
    stats_rows: list[dict] = []
    y_all: list[float] = []

    for i, tp in enumerate(tps):
        tp_data = sub[sub["timepoint"] == tp]
        as_v = tp_data.loc[tp_data["condition"] == "AS", "lm_pct_total_reads"].dropna()
        n_v = tp_data.loc[tp_data["condition"] == "N", "lm_pct_total_reads"].dropna()

        boxplot_manual(
            ax, i - 0.22, as_v, PALETTE_CONDITION["AS"],
            width=0.38, marker=COND_MARKERS["AS"], seed=i * 7,
        )
        boxplot_manual(
            ax, i + 0.22, n_v, PALETTE_CONDITION["N"],
            width=0.38, marker=COND_MARKERS["N"], seed=i * 7 + 1,
        )
        y_all.extend(as_v.tolist() + n_v.tolist())

        p_v, r_v, n1, n2 = mwu_pr(as_v, n_v)
        stats_rows.append({
            "figure": "Fig 5 (AS vs N sponge quasimeta, Lm2-6 pooled)",
            "comparison": "AS vs N",
            "subgroup": f"sponge | {tp} | Lm2-6 pooled",
            "metric": "lm_pct_total_reads",
            "n1": n1, "n2": n2,
            "median1": float(as_v.median()) if len(as_v) else np.nan,
            "median2": float(n_v.median()) if len(n_v) else np.nan,
            "U": np.nan,
            "p": p_v,
            "effect_r": r_v,
        })

    y_max = safe_top(y_all, 1.10)

    ax.set_xticks(range(n_tps))
    ax.set_xticklabels(tps)
    ax.set_xlim(-0.6, n_tps - 0.4)
    ax.set_ylim(bottom=0, top=y_max * 1.12 if y_max > 0 else 1.0)
    ax.set_xlabel("Sponge incubation timepoint")
    ax.set_ylabel("Lm reads (%)")
    ax.legend(
        handles=[
            mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["AS"], 0.35), label="Adaptive Sampling (AS)"),
            mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["N"], 0.35),  label="Native (N)"),
        ],
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )
    fig.tight_layout(rect=[0, 0, 0.86, 1])
    _save(fig, out_dir, "fig_AS_vs_N_sponge_quasimeta")
    plt.close(fig)

    df = pd.DataFrame(stats_rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


# ---------------------------------------------------------------------------
# Base-% confirmatory figures (mirror the read-% versions one-to-one)
# ---------------------------------------------------------------------------
def fig_timecourse_N_sponge_per_Lm_bases(wide: pd.DataFrame, out_dir: Path) -> None:
    """Base-% twin of fig_timecourse_N_sponge_per_Lm.

    Identical layout and subset, but plots ``lm_pct_sample_bases`` instead of
    ``lm_pct_total_reads``. Added to cover the "% bases" side of the PI ask;
    visually near-identical to the read-% version because Nanopore read
    lengths are roughly comparable across panel species.
    """
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=False)
    rng = np.random.default_rng(321)

    for ax, tr in zip(axes, TREATMENT_ORDER):
        data = sub[sub["Treatment"] == tr]
        colour = PALETTE_TREATMENT[tr]
        xs: list[float] = []
        means: list[float] = []
        sems: list[float] = []
        for tp_idx, tp in enumerate(TP_ORDER):
            vals = data.loc[data["timepoint"] == tp, "lm_pct_sample_bases"].dropna().to_numpy()
            if not len(vals):
                continue
            xs.append(tp_idx)
            means.append(float(vals.mean()))
            sems.append(
                float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            )
            jitter = rng.uniform(-0.14, 0.14, size=len(vals))
            ax.scatter(
                np.full(len(vals), tp_idx) + jitter, vals,
                color=colour, s=22, alpha=0.45, zorder=2, linewidths=0,
            )
        if xs:
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2, marker="o", markersize=7,
                capsize=3.5, zorder=5,
                markeredgecolor="white", markeredgewidth=0.8,
            )
        ax.set_xticks(range(len(TP_ORDER)))
        ax.set_xticklabels(TP_ORDER, rotation=25, ha="right")
        ax.set_xlabel("Sponge quasimetagenomic timepoint")
        if tr == TREATMENT_ORDER[0]:
            ax.set_ylabel("Lm bases / total sample bases (%)")
        ax.set_title(f"{tr} (N, sponge)  n={int(data['basename'].nunique())}", fontsize=11)
        ax.set_ylim(bottom=0)

    fig.suptitle(
        "Sponge quasimetagenomic timecourse, N only — stratified by Lm spiking level (base %)",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, out_dir, "fig_timecourse_N_sponge_per_Lm_bases")
    plt.close(fig)


def fig_swab_comparison_N_only_bases(wide: pd.DataFrame, out_dir: Path) -> None:
    """Base-% twin of fig_swab_comparison_N_only.

    Same subset and layout, swaps ``lm_pct_total_reads`` for
    ``lm_pct_sample_bases``. Visually confirms the read-% swab comparison.
    """
    meta_n = wide[
        (wide["round"] == 1)
        & (wide["condition"] == "N")
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    y_all: list[float] = []
    for i, swab in enumerate(SWAB_ORDER):
        vals = meta_n.loc[meta_n["swab_type"] == swab, "lm_pct_sample_bases"].dropna()
        boxplot_manual(
            ax, i, vals, PALETTE_SWAB[swab],
            width=0.55, marker="o", seed=i * 11,
        )
        y_all.extend(vals.tolist())

    y_max = safe_top(y_all, 1.10)

    ax.set_xticks(range(len(SWAB_ORDER)))
    ax.set_xticklabels(SWAB_ORDER)
    ax.set_xlim(-0.55, len(SWAB_ORDER) - 0.45)
    ax.set_ylim(bottom=0, top=y_max * 1.15 if y_max > 0 else 1.0)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Lm bases / total sample bases (%)")
    ax.set_title("Swab-type comparison — metagenomic samples, N only (base %)", fontsize=11)
    ax.legend(
        handles=[mpatches.Patch(color=PALETTE_SWAB[s], label=s) for s in SWAB_ORDER],
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )
    fig.tight_layout(rect=[0, 0, 0.85, 1])
    _save(fig, out_dir, "fig_swab_comparison_N_only_bases")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Extra stats for the MWU workbook
# ---------------------------------------------------------------------------
def stats_sponge_AS_vs_N_per_timepoint(wide: pd.DataFrame) -> pd.DataFrame:
    """AS vs N per timepoint on Sponge quasimetagenomic samples (R3/R5/R2/R4)."""
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()
    rows = []
    for tp in TP_ORDER:
        s = sub[sub["timepoint"] == tp]
        if s.empty:
            continue
        as_v = s.loc[s["condition"] == "AS", "lm_pct_total_reads"]
        n_v  = s.loc[s["condition"] == "N",  "lm_pct_total_reads"]
        p_v, r_v, n1, n2 = mwu_pr(as_v, n_v)
        rows.append({
            "figure": "Fig 3a.3p (sponge AS vs N per timepoint)",
            "comparison": "AS vs N",
            "subgroup": f"sponge | {tp}",
            "metric": "lm_pct_total_reads",
            "n1": n1, "n2": n2,
            "median1": float(as_v.median()) if len(as_v) else np.nan,
            "median2": float(n_v.median())  if len(n_v)  else np.nan,
            "U": np.nan,
            "p": p_v,
            "effect_r": r_v,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


def stats_timepoint_pairwise_sponge_n(wide: pd.DataFrame) -> pd.DataFrame:
    """Pairwise timepoint contrasts on Sponge N samples for each Lm strain + Lm pooled."""
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"])
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()
    rows = []
    metric_col_map = {
        "Lm pooled": "lm_pct_total_reads",
        **{s: f"{s}_pct_sample_total" for s in LM_STRAINS},
    }
    for label, col in metric_col_map.items():
        for t1, t2 in combinations(TP_ORDER, 2):
            a = sub.loc[sub["timepoint"] == t1, col].dropna()
            b = sub.loc[sub["timepoint"] == t2, col].dropna()
            p_v, r_v, n1, n2 = mwu_pr(a, b)
            rows.append({
                "figure": "Fig 2 (pairwise timepoint, sponge N)",
                "comparison": f"{t1} vs {t2}",
                "subgroup": f"sponge | N | {label}",
                "metric": col,
                "n1": n1, "n2": n2,
                "median1": float(a.median()) if len(a) else np.nan,
                "median2": float(b.median()) if len(b) else np.nan,
                "U": np.nan,
                "p": p_v,
                "effect_r": r_v,
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


def stats_swab_pairwise_metagenomic_per_Lm(wide: pd.DataFrame) -> pd.DataFrame:
    """Pairwise swab-type MWU on metagenomic (R1) N samples, stratified by Lm level."""
    sub = wide[
        (wide["round"] == 1)
        & (wide["condition"] == "N")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()
    rows: list[dict] = []
    for tr in TREATMENT_ORDER:
        data = sub[sub["Treatment"] == tr]
        for s1, s2 in combinations(SWAB_ORDER, 2):
            g1 = data.loc[data["swab_type"] == s1, "lm_pct_total_reads"].dropna()
            g2 = data.loc[data["swab_type"] == s2, "lm_pct_total_reads"].dropna()
            p_v, r_v, n1, n2 = mwu_pr(g1, g2)
            rows.append({
                "figure": "Fig 4b (swab pairwise, metagenomic N, per Lm)",
                "comparison": f"{s1} vs {s2}",
                "subgroup": f"metagenomic | N | {tr}",
                "metric": "lm_pct_total_reads",
                "n1": n1, "n2": n2,
                "median1": float(g1.median()) if len(g1) else np.nan,
                "median2": float(g2.median()) if len(g2) else np.nan,
                "U": np.nan,
                "p": p_v,
                "effect_r": r_v,
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


def stats_timepoint_pairwise_sponge_n_per_Lm(wide: pd.DataFrame) -> pd.DataFrame:
    """Pairwise timepoint MWU on sponge N samples, stratified by Lm spiking level."""
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()
    rows: list[dict] = []
    for tr in TREATMENT_ORDER:
        data = sub[sub["Treatment"] == tr]
        for t1, t2 in combinations(TP_ORDER, 2):
            a = data.loc[data["timepoint"] == t1, "lm_pct_total_reads"].dropna()
            b = data.loc[data["timepoint"] == t2, "lm_pct_total_reads"].dropna()
            p_v, r_v, n1, n2 = mwu_pr(a, b)
            rows.append({
                "figure": "Fig 5b (pairwise timepoint, sponge N, per Lm)",
                "comparison": f"{t1} vs {t2}",
                "subgroup": f"sponge | N | {tr}",
                "metric": "lm_pct_total_reads",
                "n1": n1, "n2": n2,
                "median1": float(a.median()) if len(a) else np.nan,
                "median2": float(b.median()) if len(b) else np.nan,
                "U": np.nan,
                "p": p_v,
                "effect_r": r_v,
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["p_BH"] = _bh_adjust(df["p"].fillna(1.0).tolist())
        df["sig"] = df["p"].apply(_stars)
        df["sig_BH"] = df["p_BH"].apply(_stars)
    return df


def stats_background_tier_summary(wide: pd.DataFrame) -> pd.DataFrame:
    ctrl = wide[wide["is_control"]].copy()
    if ctrl.empty:
        return pd.DataFrame()
    keep = [
        "basename", "round", "timepoint", "condition", "cohort", "group",
        "total_panel_reads", "total_sample_reads",
        "lm_total_reads", "nonmono_total_reads", "background_total_reads",
        "lm_pct_panel", "nonmono_pct_panel", "background_pct_panel",
        "lm_pct_total_reads",
    ]
    present = [c for c in keep if c in ctrl.columns]
    out = ctrl[present].copy()
    return out.sort_values(["round", "condition", "basename"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# MWU workbook
# ---------------------------------------------------------------------------
def write_mwu_workbook(
    out_path: Path,
    as_vs_n_meta: pd.DataFrame,
    swab_n: pd.DataFrame,
    as_vs_n_sponge_pooled: pd.DataFrame,
    tp_pairwise: pd.DataFrame,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _finalize(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        cols = [
            "figure", "comparison", "subgroup", "metric",
            "n1", "n2", "median1", "median2", "U",
            "p", "p_BH", "effect_r", "sig", "sig_BH",
        ]
        rename = {
            "figure": "Figure",
            "comparison": "Comparison",
            "subgroup": "Subgroup",
            "metric": "Metric",
            "n1": "n_group_1",
            "n2": "n_group_2",
            "median1": "Median_group_1",
            "median2": "Median_group_2",
            "U": "U",
            "p": "p_value",
            "p_BH": "p_BH_adjusted",
            "effect_r": "Effect_size_r",
            "sig": "Significance_raw",
            "sig_BH": "Significance_BH",
        }
        present = [c for c in cols if c in df.columns]
        return df[present].rename(columns=rename)

    readme = pd.DataFrame({
        "field": [
            "Data provenance",
            "Schema",
            "Round → timepoint",
            "Tiers",
            "Effect size",
            "Sign convention",
            "Multiple-comparison correction",
            "Filters",
            "Sheet map",
        ],
        "value": [
            "strain_proportions_master_5.csv from the 16-genome competitive minimap2 rerun (4 L. monocytogenes + 3 non-mono Listeria + 9 environmental background species).",
            "Long format: one row per sample x strain. 16 strains in 3 tiers.",
            "R1 = metagenomics (0h baseline); R3 = quasimeta 4h; R5 = quasimeta 12h; R2 = quasimeta 24h (1); R4 = quasimeta 24h (2).",
            "L_monocytogenes: EGDe, LL195, LMNC326, N13-0119. non_mono: L. innocua J5051, L. ivanovii Nr26, L. welshimeri Nr14. background: B. cereus, B. subtilis, E. coli, P. aeruginosa, P. mirabilis, R. equi, S. aureus, Y. enterocolitica, Y. frederiksenii.",
            "Rank-biserial correlation r (Kerby 2014), r = 2*U1/(n1*n2) - 1. Range [-1, 1]. |r| thresholds: 0.1 small, 0.3 medium, 0.5 large.",
            "Group 1 is the LEFT side of the Comparison string (e.g. 'AS vs N' => group_1 = AS, group_2 = N). Positive r => group_1 stochastically larger than group_2.",
            "Benjamini-Hochberg (BH) applied within each sheet to control the false discovery rate (FDR). BH is the standard default for exploratory multiple-comparison correction in biology/genomics because it is more powerful than Bonferroni (which controls the family-wise error rate and becomes overly conservative with many tests).",
            "All comparisons use Lm-spiked samples only (Treatment in {Lm2, Lm4, Lm6}). Blank, Background and Control_Lm samples are excluded. Samples with swab_type == '-' excluded. 'Zymo_swab' normalised to 'Zymo'. Metric: lm_pct_total_reads = L. monocytogenes reads / total sequenced reads (NanoStat denominator).",
            "AS_vs_N_metagenomic_per_swab → Fig 3. Swab_pairwise_metagenomic_N → Fig 4. AS_vs_N_sponge_quasimeta → Fig 5. Timepoint_pairwise_sponge_N → Fig 2.",
        ],
    })

    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        _finalize(as_vs_n_meta).to_excel(xw, sheet_name="AS_vs_N_metagenomic_per_swab", index=False)
        _finalize(swab_n).to_excel(xw, sheet_name="Swab_pairwise_metagenomic_N", index=False)
        _finalize(as_vs_n_sponge_pooled).to_excel(xw, sheet_name="AS_vs_N_sponge_quasimeta", index=False)
        _finalize(tp_pairwise).to_excel(xw, sheet_name="Timepoint_pairwise_sponge_N", index=False)
    print(f"[xlsx] wrote {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--read-metrics", type=Path, default=DEFAULT_READ_METRICS,
                        help="Per-sample NanoStat summary with `sample` and `number_of_reads` columns.")
    parser.add_argument("--mismapping", type=Path, default=DEFAULT_MISMAPPING,
                        help="Negative-control mismapping CSV (S13_S14 pure welshimeri+innocua mix).")
    parser.add_argument("--sample-metadata", type=Path, default=DEFAULT_SAMPLE_METADATA,
                        help="Sample metadata CSV with Treatment (Lm2/Lm4/Lm6) and sample_type per basename.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    long_df, wide = load_strain_long(args.input, args.read_metrics, args.sample_metadata)
    pub_dir = args.output_root / "publication_v4"

    fig_strain_timecourse_by_strain(wide, pub_dir)
    fig_background_sanity_check(wide, pub_dir, args.mismapping)
    as_vs_n_meta_stats = fig_AS_vs_N_per_swab_metagenomic(wide, pub_dir)
    swab_n_stats = fig_swab_comparison_N_only(wide, pub_dir)

    # Per-Lm timecourse scatter (Fig 2) — kept because Lara asked for it
    # explicitly; stats from this figure go into the Fig-2 timepoint-pairwise
    # sheet below (pooled), not as per-Lm noise.
    fig_timecourse_N_sponge_per_Lm(wide, pub_dir)

    # Primary AS-vs-N sponge figure (Lm2-6 pooled → proper boxplots).
    as_vs_n_sponge_pooled_stats = fig_AS_vs_N_sponge_quasimeta(wide, pub_dir)

    # Base-% confirmatory figures.
    fig_timecourse_N_sponge_per_Lm_bases(wide, pub_dir)
    fig_swab_comparison_N_only_bases(wide, pub_dir)

    tp_pairwise_stats = stats_timepoint_pairwise_sponge_n(wide)

    mwu_path = args.output_root / "listeria_mann_whitney_u_tests_v4.xlsx"
    write_mwu_workbook(
        mwu_path,
        as_vs_n_meta_stats,
        swab_n_stats,
        as_vs_n_sponge_pooled_stats,
        tp_pairwise_stats,
    )

    print(f"\nDone. Output root: {args.output_root}")


if __name__ == "__main__":
    main()
