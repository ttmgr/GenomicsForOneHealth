"""Generate pooled Listeria publication figures from the local CSV.

This adapts the user-provided plotting code to the project layout:
- reads `listeria_reads.csv` from the repo root
- writes PNG, PDF, and SVG files to `outputs/publication_v4/`
"""

from __future__ import annotations

import argparse
from itertools import combinations
import os
from pathlib import Path
import warnings

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
from matplotlib.ticker import FuncFormatter

from listeria_pipeline_common import (
    DEFAULT_INPUT_PATH,
    DEFAULT_INPUT_SHEET,
    DEFAULT_OUTPUT_ROOT,
    ROOT,
    build_pipeline_paths,
    load_listeria_data,
)

warnings.filterwarnings("ignore")

INPUT_PATH = DEFAULT_INPUT_PATH
INPUT_SHEET = DEFAULT_INPUT_SHEET
OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
OUTPUT_DIR = OUTPUT_ROOT / "publication_v4"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAVE_FORMATS = ("png", "pdf", "svg")
TIMEPOINT_MAP = {
    "metagenomics": "0h",
    "quasimeta_4h": "4h",
    "quasimeta_12h": "12h",
    "quasimeta_24h_1": "24h (1)",
    "quasimeta_24h_2": "24h (2)",
}
APPROACH_SAMPLE_ORDER = [
    "metagenomics",
    "quasimeta_4h",
    "quasimeta_12h",
    "quasimeta_24h_1",
    "quasimeta_24h_2",
]
APPROACH_SAMPLE_LABELS = ["Metagenomics", "4h quasi", "12h quasi", "24h quasi (1)", "24h quasi (2)"]
TP_ORDER = ["0h", "4h", "12h", "24h (1)", "24h (2)"]
TP_HOURS = [0, 4, 12, 24, 26]
APPROACH_ORDER = ["AS", "N"]
SWAB_ORDER = ["Sponge", "Cotton", "Zymo"]
KIT_ORDER = ["PowerSoil", "Zymo", "Micro", "Mini"]
FIGSIZE_STANDARD = (14, 10)

COL_AS = "#C0392B"
COL_N = "#2471A3"
COND_COLORS = {"AS": COL_AS, "N": COL_N}
COND_MARKERS = {"AS": "D", "N": "o"}
SWAB_COLORS = {"Sponge": "#2E75B6", "Cotton": "#C55A11", "Zymo": "#7030A0"}
KIT_COLORS = {"PowerSoil": "#2E75B6", "Zymo": "#7030A0", "Micro": "#C55A11", "Mini": "#2CA02C"}
KIT_MARKERS = {"PowerSoil": "o", "Zymo": "D", "Micro": "s", "Mini": "^"}
LEGEND_RECT = [0, 0, 0.86, 1]


plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
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
        "svg.fonttype": "none",
    }
)


def configure_paths(
    input_path: str | Path | None = None,
    sheet_name: str = DEFAULT_INPUT_SHEET,
    output_root: str | Path | None = None,
) -> None:
    global INPUT_PATH, INPUT_SHEET, OUTPUT_ROOT, OUTPUT_DIR

    paths = build_pipeline_paths(input_path=input_path, sheet_name=sheet_name, output_root=output_root)
    INPUT_PATH = paths.input_path
    INPUT_SHEET = paths.sheet_name
    OUTPUT_ROOT = paths.output_root
    OUTPUT_DIR = paths.publication_dir
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    _all_rows, df = load_listeria_data(INPUT_PATH, INPUT_SHEET)
    df["Timepoint"] = df["Sample Type"].map(TIMEPOINT_MAP)
    return df


def mwu(a: pd.Series, b: pd.Series) -> float | None:
    a_vals = np.asarray(a.dropna())
    b_vals = np.asarray(b.dropna())
    if len(a_vals) < 2 or len(b_vals) < 2:
        return None
    _, p = mannwhitneyu(a_vals, b_vals, alternative="two-sided")
    return float(p)


def mwu_pr(a: pd.Series, b: pd.Series) -> tuple[float | None, float | None, int, int]:
    """Two-sided MWU returning (p, rank-biserial r, n1, n2).

    r follows Kerby (2014): r = 2*U1/(n1*n2) - 1, where U1 is scipy's
    returned statistic (pair count where a > b). Positive r means a > b.
    """
    a_vals = np.asarray(a.dropna(), dtype=float)
    b_vals = np.asarray(b.dropna(), dtype=float)
    n1, n2 = len(a_vals), len(b_vals)
    if n1 < 2 or n2 < 2:
        return None, None, n1, n2
    U, p = mannwhitneyu(a_vals, b_vals, alternative="two-sided")
    r = (2.0 * float(U)) / (n1 * n2) - 1.0
    return float(p), float(r), n1, n2


def annotate_pr(ax, x1: float, x2: float, y: float, p: float | None, r: float | None, dy_frac: float = 0.12, fontsize: float = 9.0) -> None:
    if p is None or p >= 0.05:
        return
    label = stars(p)
    text = f"{label}\np={p:.2g}\nr={r:+.2f}" if r is not None else f"{label}\np={p:.2g}"
    h = y * dy_frac
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=0.9, color="k", clip_on=False)
    ax.text(
        (x1 + x2) / 2,
        y + h * 1.15,
        text,
        ha="center",
        va="bottom",
        fontsize=fontsize,
        color="k",
        fontweight="bold",
        clip_on=False,
    )


def stars(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def bracket(ax, x1: float, x2: float, y: float, p: float | None, dy_frac: float = 0.12, fontsize: float = 9.5, lw: float = 0.9) -> None:
    label = stars(p)
    if label in {"ns", "n/a"}:
        return
    color = "k"
    h = y * dy_frac
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=lw, color=color, clip_on=False)
    ax.text(
        (x1 + x2) / 2,
        y + h * 1.1,
        label,
        ha="center",
        va="bottom",
        fontsize=fontsize,
        color=color,
        fontweight="bold",
        clip_on=False,
    )


def jstrip(ax, x: float, vals: np.ndarray, color: str, marker: str = "o", size: float = 4.8, alpha: float = 0.75, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-0.10, 0.10, size=len(vals))
    ax.scatter(
        x + jitter,
        vals,
        color=color,
        marker=marker,
        s=size**2,
        alpha=alpha,
        zorder=5,
        linewidths=0.5,
        edgecolors="white",
    )


def boxplot_manual(
    ax,
    x: float,
    vals: pd.Series | np.ndarray,
    color: str,
    width: float = 0.40,
    marker: str = "o",
    seed: int = 0,
    whisker_iqr: float = 1.5,
    lw_box: float = 1.0,
    lw_med: float = 2.0,
    lw_whisk: float = 0.9,
    use_full_range: bool = False,
) -> None:
    """Draw a manual box plot.

    If ``use_full_range`` is True, whiskers extend from Q1 to the global minimum
    and from Q3 to the global maximum, and no fliers are drawn. This is the
    right choice for pooled/bimodal groups (e.g. Lm2/Lm4/Lm6 pooled together)
    where Tukey's IQR rule would classify biologically valid clusters as
    outliers and produce misleading or absent whiskers.
    """
    vals_arr = np.asarray(vals, dtype=float)
    vals_arr = vals_arr[~np.isnan(vals_arr)]
    if len(vals_arr) == 0:
        return

    q1, med, q3 = np.percentile(vals_arr, [25, 50, 75])
    iqr = q3 - q1

    if use_full_range:
        lo_whisk = float(vals_arr.min())
        hi_whisk = float(vals_arr.max())
        fliers = np.array([], dtype=float)
    else:
        lo_fence = q1 - whisker_iqr * iqr
        hi_fence = q3 + whisker_iqr * iqr
        lo_whisk = vals_arr[vals_arr >= lo_fence].min() if np.any(vals_arr >= lo_fence) else q1
        hi_whisk = vals_arr[vals_arr <= hi_fence].max() if np.any(vals_arr <= hi_fence) else q3
        # Guard against percentile interpolation jumping over outlier boundaries:
        # if the highest non-outlier is below the (interpolated) Q3, the whisker
        # line would otherwise be drawn downward into the box. Clip to Q1/Q3.
        lo_whisk = min(lo_whisk, q1)
        hi_whisk = max(hi_whisk, q3)
        fliers = vals_arr[(vals_arr < lo_fence) | (vals_arr > hi_fence)]

    half = width / 2
    box = plt.Rectangle(
        (x - half, q1),
        width,
        iqr,
        facecolor=matplotlib.colors.to_rgba(color, 0.25),
        edgecolor="black",
        linewidth=lw_box,
        zorder=2,
    )
    ax.add_patch(box)

    ax.plot([x - half, x + half], [med, med], color="black", lw=lw_med, zorder=4, solid_capstyle="butt")
    ax.plot([x, x], [q1, lo_whisk], color="black", lw=lw_whisk, zorder=3, solid_capstyle="butt")
    ax.plot([x, x], [q3, hi_whisk], color="black", lw=lw_whisk, zorder=3, solid_capstyle="butt")

    cap_w = half * 0.5
    ax.plot([x - cap_w, x + cap_w], [lo_whisk, lo_whisk], color="black", lw=lw_whisk, zorder=3)
    ax.plot([x - cap_w, x + cap_w], [hi_whisk, hi_whisk], color="black", lw=lw_whisk, zorder=3)

    if len(fliers):
        ax.scatter([x] * len(fliers), fliers, marker="+", color=color, s=28, zorder=3, linewidths=0.8, alpha=0.7)

    jstrip(ax, x, vals_arr, color, marker=marker, size=4.8, alpha=0.72, seed=seed)


def safe_top(vals: list[float] | np.ndarray, factor: float, fallback: float = 1.0) -> float:
    arr = np.asarray(vals, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return fallback
    top = np.percentile(arr, 90) * factor
    return float(top if top > 0 else fallback)


def compact_number(value: float, _pos: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        text = f"{value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        text = f"{value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        text = f"{value / 1_000:.1f}k"
    else:
        text = f"{value:.0f}"
    return text.replace(".0", "")


def save_figure(fig: plt.Figure, stem: str) -> None:
    for ext in SAVE_FORMATS:
        fig.savefig(OUTPUT_DIR / f"{stem}.{ext}")


def add_legend_outside(ax, handles=None, labels=None, fontsize: float = 9) -> None:
    ax.legend(
        handles=handles,
        labels=labels,
        frameon=False,
        fontsize=fontsize,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )


def plot_summary_bars(
    ax,
    data: pd.DataFrame,
    group_col: str,
    metric: str,
    order: list[str],
    colors: dict[str, str],
    xlabel: str,
    ylabel: str,
    legend_labels: dict[str, str] | None = None,
    use_compact_ticks: bool = False,
    agg: str = "mean",
) -> None:
    ymax_candidates: list[float] = []
    handles: list[mpatches.Patch] = []

    for idx, group in enumerate(order):
        vals = data.loc[data[group_col] == group, metric].dropna().to_numpy(dtype=float)
        if not len(vals):
            continue

        if agg == "sum":
            bar_val = float(np.sum(vals))
        elif agg == "mean":
            bar_val = float(np.mean(vals))
        else:
            raise ValueError(f"Unsupported aggregation: {agg}")
        ax.bar(
            idx,
            bar_val,
            width=0.58,
            color=matplotlib.colors.to_rgba(colors[group], 0.35),
            edgecolor="black",
            linewidth=1.0,
            zorder=2,
        )
        ymax_candidates.append(bar_val)
        handles.append(
            mpatches.Patch(
                facecolor=matplotlib.colors.to_rgba(colors[group], 0.35),
                edgecolor="black",
                label=(legend_labels or {}).get(group, group),
            )
        )

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order)
    ax.set_xlim(-0.55, len(order) - 0.45)
    ax.set_ylim(bottom=0, top=max(ymax_candidates) * 1.18 if ymax_candidates else 1.0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0.06)

    if use_compact_ticks:
        ax.yaxis.set_major_formatter(FuncFormatter(compact_number))

    add_legend_outside(ax, handles=handles, fontsize=8.8)


def plot_grouped_summary_bars(
    ax,
    data: pd.DataFrame,
    major_col: str,
    metric: str,
    major_order: list[str],
    hue_col: str,
    hue_order: list[str],
    colors: dict[str, str],
    xlabel: str,
    ylabel: str,
    legend_labels: dict[str, str] | None = None,
    major_labels: list[str] | None = None,
    use_compact_ticks: bool = False,
    agg: str = "mean",
) -> None:
    x = np.arange(len(major_order), dtype=float)
    width = 0.34
    ymax_candidates: list[float] = []
    handles: list[mpatches.Patch] = []

    for hue_idx, hue in enumerate(hue_order):
        offset = (hue_idx - (len(hue_order) - 1) / 2) * (width + 0.03)
        heights: list[float] = []
        positions: list[float] = []
        for major_idx, major in enumerate(major_order):
            vals = data.loc[(data[major_col] == major) & (data[hue_col] == hue), metric].dropna().to_numpy(dtype=float)
            if not len(vals):
                continue
            if agg == "sum":
                bar_val = float(np.sum(vals))
            elif agg == "mean":
                bar_val = float(np.mean(vals))
            else:
                raise ValueError(f"Unsupported aggregation: {agg}")
            heights.append(bar_val)
            positions.append(x[major_idx] + offset)
            ymax_candidates.append(bar_val)

        if positions:
            ax.bar(
                positions,
                heights,
                width=width,
                color=matplotlib.colors.to_rgba(colors[hue], 0.35),
                edgecolor="black",
                linewidth=1.0,
                zorder=2,
            )

        handles.append(
            mpatches.Patch(
                facecolor=matplotlib.colors.to_rgba(colors[hue], 0.35),
                edgecolor="black",
                label=(legend_labels or {}).get(hue, hue),
            )
        )

    ax.set_xticks(x)
    ax.set_xticklabels(major_labels or major_order)
    ax.set_xlim(-0.65, len(major_order) - 0.35)
    ax.set_ylim(bottom=0, top=max(ymax_candidates) * 1.18 if ymax_candidates else 1.0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.margins(x=0.04)

    if use_compact_ticks:
        ax.yaxis.set_major_formatter(FuncFormatter(compact_number))

    add_legend_outside(ax, handles=handles, fontsize=8.8)


def save_summary_bar_plot(
    data: pd.DataFrame,
    group_col: str,
    metric: str,
    order: list[str],
    colors: dict[str, str],
    xlabel: str,
    ylabel: str,
    stem: str,
    legend_labels: dict[str, str] | None = None,
    use_compact_ticks: bool = False,
    agg: str = "mean",
) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE_STANDARD)
    plot_summary_bars(
        ax=ax,
        data=data,
        group_col=group_col,
        metric=metric,
        order=order,
        colors=colors,
        xlabel=xlabel,
        ylabel=ylabel,
        legend_labels=legend_labels,
        use_compact_ticks=use_compact_ticks,
        agg=agg,
    )
    plt.tight_layout(rect=[0, 0, 0.82, 1])
    save_figure(fig, stem)
    plt.close(fig)
    print(f"Saved {stem}")


def save_grouped_summary_bar_plot(
    data: pd.DataFrame,
    major_col: str,
    metric: str,
    major_order: list[str],
    hue_col: str,
    hue_order: list[str],
    colors: dict[str, str],
    xlabel: str,
    ylabel: str,
    stem: str,
    legend_labels: dict[str, str] | None = None,
    major_labels: list[str] | None = None,
    use_compact_ticks: bool = False,
    agg: str = "mean",
) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE_STANDARD)
    plot_grouped_summary_bars(
        ax=ax,
        data=data,
        major_col=major_col,
        metric=metric,
        major_order=major_order,
        hue_col=hue_col,
        hue_order=hue_order,
        colors=colors,
        xlabel=xlabel,
        ylabel=ylabel,
        legend_labels=legend_labels,
        major_labels=major_labels,
        use_compact_ticks=use_compact_ticks,
        agg=agg,
    )
    plt.tight_layout(rect=LEGEND_RECT)
    save_figure(fig, stem)
    plt.close(fig)
    print(f"Saved {stem}")


def build_figures(df: pd.DataFrame) -> None:
    qm_lm = df[(df["Swab Type"] == "Sponge") & df["Treatment"].isin(["Lm2", "Lm4", "Lm6"])].copy()
    qm_0h = df[(df["Sample Type"] == "metagenomics") & (df["Swab Type"] == "Sponge")].copy()
    meta_df = df[df["Sample Type"] == "metagenomics"].copy()
    summary_df = df[~df["Treatment"].isin(["Blank", "Background"])].copy()

    conditions_in_df = {
        str(c) for c in df["Condition"].dropna().astype(str).unique()
    }
    approach_order = [c for c in APPROACH_ORDER if c in conditions_in_df]
    approach_single = len(approach_order) == 1
    approach_has_as = "AS" in approach_order

    # FIG 1 — AS vs N comparison is only meaningful when both conditions are in the data.
    if approach_has_as and not approach_single:
        fig1, ax1 = plt.subplots(figsize=FIGSIZE_STANDARD)
        y_all: list[float] = []
        for i, tp in enumerate(TP_ORDER[1:]):
            sub = qm_lm[qm_lm["Timepoint"] == tp]
            as_v = sub[sub["Condition"] == "AS"]["Lm % Reads"].dropna()
            n_v = sub[sub["Condition"] == "N"]["Lm % Reads"].dropna()
            x_as, x_n = i * 2.0, i * 2.0 + 0.65
            boxplot_manual(ax1, x_as, as_v, COL_AS, width=0.52, marker=COND_MARKERS["AS"], seed=i * 7, use_full_range=True)
            boxplot_manual(ax1, x_n, n_v, COL_N, width=0.52, marker=COND_MARKERS["N"], seed=i * 7 + 1, use_full_range=True)
            y_all.extend(as_v.tolist() + n_v.tolist())

        y_ref = safe_top(y_all, 1.12)
        for i, tp in enumerate(TP_ORDER[1:]):
            sub = qm_lm[qm_lm["Timepoint"] == tp]
            p_v, r_v, _, _ = mwu_pr(sub[sub["Condition"] == "AS"]["Lm % Reads"], sub[sub["Condition"] == "N"]["Lm % Reads"])
            annotate_pr(ax1, i * 2.0, i * 2.0 + 0.65, y_ref, p_v, r_v, dy_frac=0.14)

        n_tps = len(TP_ORDER) - 1
        ax1.set_xticks([i * 2.0 + 0.325 for i in range(n_tps)])
        ax1.set_xticklabels(TP_ORDER[1:])
        ax1.set_xlim(-0.5, (n_tps - 1) * 2.0 + 1.3)
        ax1.set_ylim(bottom=0, top=y_ref * 1.35)
        ax1.set_xlabel("Sponge incubation timepoint")
        ax1.set_ylabel("Lm reads (%)")
        add_legend_outside(
            ax1,
            handles=[
                mpatches.Patch(color=COL_AS, label="Adaptive Sampling (AS)"),
                mpatches.Patch(color=COL_N, label="Native (N)"),
            ],
            fontsize=9,
        )
        plt.tight_layout(rect=LEGEND_RECT)
        save_figure(fig1, "fig1_quasimeta_AS_vs_N")
        plt.close(fig1)
        print("Saved fig1")
    else:
        print("Skipped fig1_quasimeta_AS_vs_N (input has only one Condition)")

    # FIG 2
    fig2, ax2 = plt.subplots(figsize=FIGSIZE_STANDARD)
    base_n = qm_0h[qm_0h["Condition"] == "N"]["Lm % Reads"].dropna()
    bm = float(base_n.mean())
    bse = float(base_n.std(ddof=1) / np.sqrt(len(base_n))) if len(base_n) > 1 else 0.0

    ax2.axhspan(bm - bse, bm + bse, alpha=0.13, color="grey", zorder=0)
    ax2.axhline(bm, color="grey", lw=1.2, ls="--", zorder=1, label="Metagenomics baseline (0 h, mean ± SEM)")

    rng = np.random.default_rng(42)
    ax2.scatter(
        np.zeros(len(base_n)) + rng.uniform(-0.18, 0.18, len(base_n)),
        base_n,
        color="grey",
        s=20,
        alpha=0.55,
        zorder=2,
        linewidths=0.4,
        edgecolors="white",
    )

    sub_n = qm_lm[qm_lm["Condition"] == "N"]
    x_hrs: list[int] = []
    y_means: list[float] = []
    y_sems: list[float] = []
    y_raw: dict[int, np.ndarray] = {}
    for tp, hr in zip(TP_ORDER[1:], TP_HOURS[1:]):
        vals = sub_n[sub_n["Timepoint"] == tp]["Lm % Reads"].dropna().to_numpy()
        if not len(vals):
            continue
        x_hrs.append(hr)
        y_means.append(float(vals.mean()))
        y_sems.append(float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0)
        y_raw[hr] = vals

    ax2.errorbar(
        x_hrs,
        y_means,
        yerr=y_sems,
        color="#2CA02C",
        lw=2.2,
        marker="o",
        markersize=8,
        capsize=4,
        zorder=5,
        label="Lm (pooled Lm2-6)",
        markeredgecolor="white",
        markeredgewidth=0.7,
    )
    for hr, vals in y_raw.items():
        ax2.scatter(
            hr + rng.uniform(-0.28, 0.28, len(vals)),
            vals,
            color="#2CA02C",
            s=20,
            alpha=0.40,
            zorder=3,
            linewidths=0,
            edgecolors="none",
        )

    ax2.set_xticks(TP_HOURS)
    ax2.set_xticklabels(TP_ORDER, rotation=35, ha="right")
    ax2.set_xlim(-1.5, TP_HOURS[-1] + 2)
    ax2.set_ylim(bottom=0)
    ax2.set_xlabel("Sponge incubation timepoint")
    ax2.set_ylabel("Lm reads (%)")
    add_legend_outside(
        ax2,
        handles=[
            Line2D([0], [0], color="grey", lw=1.2, ls="--", label="Metagenomics baseline (0 h, mean ± SEM)"),
            Line2D(
                [0],
                [0],
                color="#2CA02C",
                lw=2.2,
                marker="o",
                markersize=7,
                markeredgecolor="white",
                markeredgewidth=0.7,
                label="Lm (pooled Lm2-6)",
            ),
        ],
        fontsize=9,
    )
    plt.tight_layout(rect=LEGEND_RECT)
    save_figure(fig2, "fig2_quasimeta_timecourse_N")
    plt.close(fig2)
    print("Saved fig2")

    # FIG 3 — AS vs N metagenomic comparison; skipped when only one Condition is present.
    if approach_has_as and not approach_single:
        fig3, ax3 = plt.subplots(figsize=FIGSIZE_STANDARD)
        y_ref3 = safe_top(meta_df["Lm % Reads"].dropna().to_numpy(), 1.0, fallback=1.0)

        for i, swab in enumerate(SWAB_ORDER):
            sub = meta_df[meta_df["Swab Type"] == swab]
            for cond, offset in [("AS", -0.27), ("N", 0.27)]:
                vals = sub[sub["Condition"] == cond]["Lm % Reads"].dropna()
                if len(vals):
                    boxplot_manual(ax3, i + offset, vals, COND_COLORS[cond], width=0.42, marker=COND_MARKERS[cond], seed=i * 13)
            p_v, r_v, _, _ = mwu_pr(sub[sub["Condition"] == "AS"]["Lm % Reads"], sub[sub["Condition"] == "N"]["Lm % Reads"])
            annotate_pr(ax3, i - 0.27, i + 0.27, y_ref3 * 1.05, p_v, r_v, dy_frac=0.18, fontsize=9.0)

        ax3.set_xticks(range(len(SWAB_ORDER)))
        ax3.set_xticklabels(SWAB_ORDER)
        ax3.set_xlim(-0.65, len(SWAB_ORDER) - 0.35)
        ax3.set_ylim(bottom=0, top=y_ref3 * 1.52)
        ax3.set_xlabel("Swab type")
        ax3.set_ylabel("Lm reads (%)")
        add_legend_outside(
            ax3,
            handles=[
                mpatches.Patch(color=COND_COLORS["AS"], label="Adaptive Sampling (AS)"),
                mpatches.Patch(color=COND_COLORS["N"], label="Native (N)"),
            ],
            fontsize=9,
        )
        plt.tight_layout(rect=LEGEND_RECT)
        save_figure(fig3, "fig3_metagenomic_AS_vs_N")
        plt.close(fig3)
        print("Saved fig3")
    else:
        print("Skipped fig3_metagenomic_AS_vs_N (input has only one Condition)")

    # FIG 4
    fig4, ax4 = plt.subplots(figsize=FIGSIZE_STANDARD)
    meta_n = meta_df[meta_df["Condition"] == "N"]
    y_max4 = safe_top(meta_n["Lm % Reads"].dropna().to_numpy(), 1.0, fallback=1.0)

    for i, swab in enumerate(SWAB_ORDER):
        vals = meta_n[meta_n["Swab Type"] == swab]["Lm % Reads"].dropna()
        boxplot_manual(ax4, i, vals, SWAB_COLORS[swab], width=0.50, marker="o", seed=i * 11)

    pairs = list(combinations(range(len(SWAB_ORDER)), 2))
    y_lvls = [y_max4 * 1.12, y_max4 * 1.27, y_max4 * 1.42]
    for (i, j), ylv in zip(pairs, y_lvls):
        s1, s2 = SWAB_ORDER[i], SWAB_ORDER[j]
        g1 = meta_n[meta_n["Swab Type"] == s1]["Lm % Reads"]
        g2 = meta_n[meta_n["Swab Type"] == s2]["Lm % Reads"]
        p_v, r_v, _, _ = mwu_pr(g1, g2)
        annotate_pr(ax4, i, j, ylv, p_v, r_v, dy_frac=0.10, fontsize=9.0)

    ax4.set_xticks(range(len(SWAB_ORDER)))
    ax4.set_xticklabels(SWAB_ORDER)
    ax4.set_xlim(-0.55, len(SWAB_ORDER) - 0.45)
    ax4.set_ylim(bottom=0, top=y_max4 * 1.65)
    ax4.set_xlabel("Swab type")
    ax4.set_ylabel("Lm reads (%)")
    add_legend_outside(
        ax4,
        handles=[mpatches.Patch(color=SWAB_COLORS[swab], label=swab) for swab in SWAB_ORDER],
        fontsize=9,
    )
    plt.tight_layout(rect=LEGEND_RECT)
    save_figure(fig4, "fig4_metagenomic_swab_comparison_N")
    plt.close(fig4)
    print("Saved fig4")

    # FIG 5
    fig5, (ax5l, ax5r) = plt.subplots(1, 2, figsize=FIGSIZE_STANDARD)
    fig5.subplots_adjust(wspace=0.30, right=0.86)

    ax5l.axhspan(bm - bse, bm + bse, alpha=0.13, color="grey", zorder=0)
    ax5l.axhline(bm, color="grey", lw=1.1, ls="--", zorder=1, label="Baseline (0 h)")
    rng5 = np.random.default_rng(99)
    ax5l.scatter(
        np.zeros(len(base_n)) + rng5.uniform(-0.18, 0.18, len(base_n)),
        base_n,
        color="grey",
        s=18,
        alpha=0.5,
        zorder=2,
        linewidths=0.4,
        edgecolors="white",
    )

    sub_n5 = qm_lm[qm_lm["Condition"] == "N"]
    x5: list[int] = []
    ym5: list[float] = []
    ys5: list[float] = []
    yr5: dict[int, np.ndarray] = {}
    for tp, hr in zip(TP_ORDER[1:], TP_HOURS[1:]):
        vals = sub_n5[sub_n5["Timepoint"] == tp]["Lm % Reads"].dropna().to_numpy()
        if not len(vals):
            continue
        x5.append(hr)
        ym5.append(float(vals.mean()))
        ys5.append(float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0)
        yr5[hr] = vals
    ax5l.errorbar(
        x5,
        ym5,
        yerr=ys5,
        color="#2CA02C",
        lw=2.0,
        marker="o",
        markersize=7,
        capsize=3.5,
        zorder=5,
        label="Lm (pooled)",
        markeredgecolor="white",
        markeredgewidth=0.6,
    )
    for hr, vals in yr5.items():
        ax5l.scatter(hr + rng5.uniform(-0.25, 0.25, len(vals)), vals, color="#2CA02C", s=15, alpha=0.40, zorder=3, linewidths=0)
    ax5l.set_xticks(TP_HOURS)
    ax5l.set_xticklabels(TP_ORDER, rotation=35, ha="right")
    ax5l.set_xlim(-1.5, TP_HOURS[-1] + 2)
    ax5l.set_ylim(bottom=0)
    ax5l.set_xlabel("Sponge incubation timepoint", fontsize=9)
    ax5l.set_ylabel("Lm reads (%)", fontsize=9)

    for i, swab in enumerate(SWAB_ORDER):
        vals = meta_n[meta_n["Swab Type"] == swab]["Lm % Reads"].dropna()
        boxplot_manual(ax5r, i, vals, SWAB_COLORS[swab], width=0.50, marker="o", seed=i * 11)
    for (i, j), ylv in zip(pairs, y_lvls):
        s1, s2 = SWAB_ORDER[i], SWAB_ORDER[j]
        g1 = meta_n[meta_n["Swab Type"] == s1]["Lm % Reads"]
        g2 = meta_n[meta_n["Swab Type"] == s2]["Lm % Reads"]
        p_v, r_v, _, _ = mwu_pr(g1, g2)
        annotate_pr(ax5r, i, j, ylv, p_v, r_v, dy_frac=0.10, fontsize=8.5)
    ax5r.set_xticks(range(len(SWAB_ORDER)))
    ax5r.set_xticklabels(SWAB_ORDER)
    ax5r.set_xlim(-0.55, len(SWAB_ORDER) - 0.45)
    ax5r.set_ylim(bottom=0, top=y_max4 * 1.65)
    ax5r.set_xlabel("Swab type", fontsize=9)
    ax5r.set_ylabel("Lm reads (%)", fontsize=9)
    handles5, labels5 = ax5l.get_legend_handles_labels()
    fig5.legend(handles5, labels5, frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.84, 0.98))

    save_figure(fig5, "fig5_combined_panel")
    plt.close(fig5)
    print("Saved fig5")

    # FIG 1 by dose — one panel per Lm level, AS vs N box plots across timepoints
    if approach_has_as and not approach_single:
        fig1d, axes1d = plt.subplots(1, 3, figsize=(16, 5.8), sharey=False)
        tps_full = TP_ORDER[1:]  # 4h, 12h, 24h (1), 24h (2)
        for ax, tr in zip(axes1d, ["Lm2", "Lm4", "Lm6"]):
            sub_tr = qm_lm[qm_lm["Treatment"] == tr]
            y_vals: list[float] = []
            for i, tp in enumerate(tps_full):
                s = sub_tr[sub_tr["Timepoint"] == tp]
                as_v = s[s["Condition"] == "AS"]["Lm % Reads"].dropna()
                n_v = s[s["Condition"] == "N"]["Lm % Reads"].dropna()
                x_as, x_n = i * 2.0, i * 2.0 + 0.65
                boxplot_manual(ax, x_as, as_v, COL_AS, width=0.52, marker=COND_MARKERS["AS"], seed=i * 7)
                boxplot_manual(ax, x_n, n_v, COL_N, width=0.52, marker=COND_MARKERS["N"], seed=i * 7 + 1)
                y_vals.extend(as_v.tolist() + n_v.tolist())
            y_ref_d = safe_top(y_vals, 1.12)
            for i, tp in enumerate(tps_full):
                s = sub_tr[sub_tr["Timepoint"] == tp]
                p_v, r_v, _, _ = mwu_pr(s[s["Condition"] == "AS"]["Lm % Reads"], s[s["Condition"] == "N"]["Lm % Reads"])
                annotate_pr(ax, i * 2.0, i * 2.0 + 0.65, y_ref_d, p_v, r_v, dy_frac=0.14)
            ax.set_xticks([i * 2.0 + 0.325 for i in range(len(tps_full))])
            ax.set_xticklabels(tps_full, rotation=35, ha="right")
            ax.set_xlim(-0.5, (len(tps_full) - 1) * 2.0 + 1.3)
            ax.set_ylim(bottom=0, top=y_ref_d * 1.45 if y_ref_d > 0 else 1.0)
            ax.set_xlabel("Sponge incubation timepoint")
            ax.set_ylabel("Lm reads (%)")
            ax.set_title(tr, fontsize=11)
        fig1d.legend(
            handles=[
                mpatches.Patch(color=COL_AS, label="Adaptive Sampling (AS)"),
                mpatches.Patch(color=COL_N, label="Native (N)"),
            ],
            frameon=False,
            fontsize=9,
            loc="upper right",
            bbox_to_anchor=(0.995, 0.99),
        )
        fig1d.tight_layout(rect=[0, 0, 0.92, 0.96])
        save_figure(fig1d, "fig1_by_spiking_concentration_AS_vs_N")
        plt.close(fig1d)
        print("Saved fig1_by_spiking_concentration")
    else:
        print("Skipped fig1_by_spiking_concentration (no AS samples in input)")

    # FIG 2 by Lm spiking level — ONE STANDALONE FIGURE per Lm level
    base_n_d = qm_0h[qm_0h["Condition"] == "N"]["Lm % Reads"].dropna()
    bm_d = float(base_n_d.mean()) if len(base_n_d) else 0.0
    bse_d = float(base_n_d.std(ddof=1) / np.sqrt(len(base_n_d))) if len(base_n_d) > 1 else 0.0
    for tr_idx, tr in enumerate(["Lm2", "Lm4", "Lm6"]):
        fig2s, ax2s = plt.subplots(figsize=FIGSIZE_STANDARD)
        rng_s = np.random.default_rng(77 + tr_idx)
        ax2s.axhspan(bm_d - bse_d, bm_d + bse_d, alpha=0.13, color="grey", zorder=0)
        ax2s.axhline(bm_d, color="grey", lw=1.2, ls="--", zorder=1, label="Metagenomics baseline (0 h, mean ± SEM)")
        ax2s.scatter(
            np.zeros(len(base_n_d)) + rng_s.uniform(-0.18, 0.18, len(base_n_d)),
            base_n_d,
            color="grey",
            s=20,
            alpha=0.55,
            zorder=2,
            linewidths=0.4,
            edgecolors="white",
        )
        sub_tr = qm_lm[(qm_lm["Treatment"] == tr) & (qm_lm["Condition"] == "N")]
        x_s: list[float] = []
        ym_s: list[float] = []
        ys_s: list[float] = []
        yraw_s: dict[float, np.ndarray] = {}
        for tp, hr in zip(TP_ORDER[1:], TP_HOURS[1:]):
            vals = sub_tr[sub_tr["Timepoint"] == tp]["Lm % Reads"].dropna().to_numpy()
            if not len(vals):
                continue
            x_s.append(hr)
            ym_s.append(float(vals.mean()))
            ys_s.append(float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0)
            yraw_s[hr] = vals
        ax2s.errorbar(
            x_s,
            ym_s,
            yerr=ys_s,
            color="#2CA02C",
            lw=2.2,
            marker="o",
            markersize=8,
            capsize=4,
            zorder=5,
            label=f"{tr} (N, mean ± SEM)",
            markeredgecolor="white",
            markeredgewidth=0.7,
        )
        for hr, vals in yraw_s.items():
            ax2s.scatter(
                hr + rng_s.uniform(-0.28, 0.28, len(vals)),
                vals,
                color="#2CA02C",
                s=20,
                alpha=0.45,
                zorder=3,
                linewidths=0,
                edgecolors="none",
            )
        ax2s.set_xticks(TP_HOURS)
        ax2s.set_xticklabels(TP_ORDER, rotation=0)
        ax2s.set_xlim(-1.5, TP_HOURS[-1] + 2)
        ax2s.set_ylim(bottom=0)
        ax2s.set_xlabel("Sponge incubation timepoint")
        ax2s.set_ylabel("Lm reads (%)")
        ax2s.set_title(f"Listeria time course — {tr}", fontsize=12)
        add_legend_outside(
            ax2s,
            handles=[
                Line2D([0], [0], color="grey", lw=1.2, ls="--", label="Metagenomics baseline (0 h, mean ± SEM)"),
                Line2D(
                    [0],
                    [0],
                    color="#2CA02C",
                    lw=2.2,
                    marker="o",
                    markersize=7,
                    markeredgecolor="white",
                    markeredgewidth=0.7,
                    label=f"{tr} (N, mean ± SEM)",
                ),
            ],
            fontsize=9,
        )
        plt.tight_layout(rect=LEGEND_RECT)
        save_figure(fig2s, f"fig2_timecourse_N_{tr}")
        plt.close(fig2s)
        print(f"Saved fig2_timecourse_N_{tr}")

    summary_approach_labels = {"AS": "Adaptive Sampling (AS)", "N": "Native (N)"}
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="Total Reads",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Total reads",
        stem="fig6_total_reads_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="Total Bases",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Total bases",
        stem="fig7_total_bases_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    summary_n_only = summary_df[summary_df["Condition"] == "N"].copy()
    save_grouped_summary_bar_plot(
        data=summary_n_only,
        major_col="Sample Type",
        metric="Total Reads",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Extraction Kit",
        hue_order=KIT_ORDER,
        colors=KIT_COLORS,
        xlabel="Approach",
        ylabel="Total reads (N only)",
        stem="fig8_total_reads_by_extraction_kit",
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_n_only,
        major_col="Sample Type",
        metric="Total Bases",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Extraction Kit",
        hue_order=KIT_ORDER,
        colors=KIT_COLORS,
        xlabel="Approach",
        ylabel="Total bases (N only)",
        stem="fig9_total_bases_by_extraction_kit",
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="Lm Total Reads (4 strains)",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Lm total reads",
        stem="fig10_lm_total_reads_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="Lm Total Bases",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Lm total bases",
        stem="fig11_lm_total_bases_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="Lm Mean Read Length",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Mean Lm read length",
        stem="fig12_lm_mean_read_length_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        agg="mean",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="# Lm Strains Detected",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Detected Lm strains (mean)",
        stem="fig13_lm_detected_strains_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        agg="mean",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="L. ivanovii Nr26 Reads",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="L. ivanovii reads",
        stem="fig14_ivanovii_reads_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        use_compact_ticks=True,
        agg="sum",
    )
    save_grouped_summary_bar_plot(
        data=summary_df,
        major_col="Sample Type",
        metric="L. ivanovii Nr26 Proportion",
        major_order=APPROACH_SAMPLE_ORDER,
        hue_col="Condition",
        hue_order=approach_order,
        colors=COND_COLORS,
        xlabel="Approach",
        ylabel="Mean L. ivanovii proportion",
        stem="fig15_ivanovii_proportion_by_approach",
        legend_labels=summary_approach_labels,
        major_labels=APPROACH_SAMPLE_LABELS,
        agg="mean",
    )
    print("All done.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the publication-style Listeria figures from a CSV or XLSX input file."
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
    df = load_data()
    build_figures(df)


if __name__ == "__main__":
    main()
