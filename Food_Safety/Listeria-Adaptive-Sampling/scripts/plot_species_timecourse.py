#!/usr/bin/env python3
"""Listeria species-level time-course figures.

Generates line graphs comparing L. monocytogenes, L. innocua, L. welshimeri,
and L. ivanovii abundance over the sponge quasi-metagenomic enrichment timeline.

Layout matches the email_package_v4 timecourse style:
- Evenly spaced categorical x positions (not numeric hours)
- 0h metagenomic baseline as grey dashed line + SEM band + scattered dots
- Species lines from 4h onward
- 24h (1) and 24h (2) as clearly separated positions

Outputs to  outputs/species_timecourse/  (never overwrites existing folders).

Usage:
    python scripts/plot_species_timecourse.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import matplotlib.lines as mlines        # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402

# ── project imports ──────────────────────────────────────────────────────
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from plot_strain_long_format import (    # noqa: E402
    load_strain_long,
    LM_STRAINS, NONMONO_SPECIES, TREATMENT_ORDER, TP_ORDER,
    DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA,
)

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────
ROOT = SCRIPTS.parent
OUT_DIR = ROOT / "outputs" / "species_timecourse"
OUT_DIR_V7 = ROOT / "outputs" / "email_package_v7"
OUT_DIR_V8 = ROOT / "outputs" / "email_package_v8"
SAVE_FORMATS = ("png", "pdf")

# Log y-axis convention shared with plot_boxplots_logscale.py:
# plain log10 with values clipped to FLOOR_PCT = 1 % so ticks bottom at 10⁰.
# No log10(x + c) pseudocount (overruled by Lara 2026-04-18).
# Symlog uses LINTHRESH = 1.0 — linear 0→1 %, log above.
FLOOR_PCT = 1.0
LINTHRESH = 1.0

# ── rcParams (match email_package_v4 / plot_fig5_with_baseline.py) ──────
plt.rcParams.update({
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
})

# ── Evenly spaced categorical x positions ────────────────────────────────
# Quasimeta timepoints only (line connects these); 0h handled as baseline
QUASIMETA_TPS = ["4h", "12h", "24h (1)", "24h (2)"]
QUASIMETA_X = [1, 2, 3, 4]  # evenly spaced, well separated

# ── Okabe-Ito species palette (colourblind-safe) ────────────────────────
SPECIES_CONFIG = {
    "L. monocytogenes": {
        "col": "lm_pct_total_reads",
        "color": "#D55E00",     # vermillion
        "marker": "o",
    },
    "L. innocua": {
        "col": "innocua_pct_total_reads",
        "color": "#0072B2",     # blue
        "marker": "s",
    },
    "L. welshimeri": {
        "col": "welshimeri_pct_total_reads",
        "color": "#009E73",     # bluish-green
        "marker": "D",
    },
    "L. ivanovii": {
        "col": "ivanovii_pct_total_reads",
        "color": "#CC79A7",     # reddish-purple
        "marker": "^",
    },
}


def _save(fig: plt.Figure, stem: str, out_dir: Path | None = None) -> None:
    target = out_dir if out_dir is not None else OUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    for ext in SAVE_FORMATS:
        fig.savefig(target / f"{stem}.{ext}")
    print(f"[fig] wrote {target / stem}.{{png,pdf}}")


def _add_species_pcts(wide: pd.DataFrame) -> pd.DataFrame:
    """Add per-species pct_total_reads AND pct_sample_bases columns to the
    wide frame. lm_pct_sample_bases is already set in load_strain_long."""
    w = wide.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        # Per-read
        w["innocua_pct_total_reads"] = 100.0 * w["L_innocua_J5051"] / w["total_sample_reads"]
        w["welshimeri_pct_total_reads"] = 100.0 * w["L_welshimeri_Nr14"] / w["total_sample_reads"]
        w["ivanovii_pct_total_reads"] = 100.0 * w["L_ivanovii_Nr26"] / w["total_sample_reads"]
        # Per-base (mirrors the per-read set; requires _bases columns from loader)
        if "L_innocua_J5051_bases" in w.columns and "total_sample_bases" in w.columns:
            w["innocua_pct_sample_bases"] = 100.0 * w["L_innocua_J5051_bases"] / w["total_sample_bases"]
            w["welshimeri_pct_sample_bases"] = 100.0 * w["L_welshimeri_Nr14_bases"] / w["total_sample_bases"]
            w["ivanovii_pct_sample_bases"] = 100.0 * w["L_ivanovii_Nr26_bases"] / w["total_sample_bases"]
    w = w.replace([np.inf, -np.inf], np.nan)
    return w


# Per-base counterpart to SPECIES_CONFIG (same colours and markers).
SPECIES_CONFIG_BASES = {
    "L. monocytogenes": {"col": "lm_pct_sample_bases",       "color": "#D55E00", "marker": "o"},
    "L. innocua":       {"col": "innocua_pct_sample_bases",  "color": "#0072B2", "marker": "s"},
    "L. welshimeri":    {"col": "welshimeri_pct_sample_bases","color": "#009E73", "marker": "D"},
    "L. ivanovii":      {"col": "ivanovii_pct_sample_bases", "color": "#CC79A7", "marker": "^"},
}


def _base_filter(wide: pd.DataFrame) -> pd.DataFrame:
    """Sponge, N condition, non-control, Lm-spiked samples."""
    return wide[
        (wide["swab_type"] == "Sponge")
        & (wide["condition"] == "N")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()


def _draw_baseline(ax: plt.Axes, sub: pd.DataFrame, species_keys: list[str],
                   rng: np.random.Generator) -> None:
    """Draw 0h metagenomic baseline as grey dots + dashed line + SEM band.

    Baseline is shown at x=0 for all species combined (Lm baseline).
    """
    base = sub[sub["timepoint"] == "0h"]
    if base.empty:
        return

    # Use the first species (Lm) for the baseline reference line
    lm_col = SPECIES_CONFIG["L. monocytogenes"]["col"]
    base_vals = base[lm_col].dropna().to_numpy()
    if not len(base_vals):
        return

    bm = float(base_vals.mean())
    bse = float(base_vals.std(ddof=1) / np.sqrt(len(base_vals))) if len(base_vals) > 1 else 0.0

    # SEM band + dashed line
    ax.axhspan(bm - bse, bm + bse, alpha=0.13, color="grey", zorder=0)
    ax.axhline(bm, color="grey", lw=1.2, ls="--", zorder=1)

    # Scatter 0h dots for each species at x=0
    for sp_name in species_keys:
        cfg = SPECIES_CONFIG[sp_name]
        vals = base[cfg["col"]].dropna().to_numpy()
        if not len(vals):
            continue
        jitter = rng.uniform(-0.18, 0.18, size=len(vals))
        ax.scatter(
            np.zeros(len(vals)) + jitter,
            vals,
            color="grey",
            s=20,
            alpha=0.45,
            zorder=2,
            linewidths=0.4,
            edgecolors="white",
        )


def _draw_species_lines(
    ax: plt.Axes,
    sub: pd.DataFrame,
    species_keys: list[str],
    rng: np.random.Generator,
) -> None:
    """Draw mean +/- SEM lines for quasimeta timepoints (4h-24h) with jittered raw points."""
    for sp_name in species_keys:
        cfg = SPECIES_CONFIG[sp_name]
        col = cfg["col"]
        colour = cfg["color"]
        marker = cfg["marker"]

        xs: list[int] = []
        means: list[float] = []
        sems: list[float] = []

        for x_pos, tp in zip(QUASIMETA_X, QUASIMETA_TPS):
            vals = sub.loc[sub["timepoint"] == tp, col].dropna().to_numpy()
            if not len(vals):
                continue
            xs.append(x_pos)
            means.append(float(vals.mean()))
            sems.append(
                float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            )
            jitter = rng.uniform(-0.12, 0.12, size=len(vals))
            ax.scatter(
                np.full(len(vals), x_pos) + jitter,
                vals,
                color=colour,
                s=20,
                alpha=0.40,
                zorder=3,
                linewidths=0,
                edgecolors="none",
            )

        if xs:
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2,
                marker=marker, markersize=8,
                capsize=4, zorder=5,
                markeredgecolor="white", markeredgewidth=0.7,
                label=sp_name,
            )


def _format_ax(ax: plt.Axes) -> None:
    """Set up the x-axis with evenly spaced categorical labels."""
    all_x = [0] + QUASIMETA_X
    all_labels = ["0h"] + QUASIMETA_TPS
    ax.set_xticks(all_x)
    ax.set_xticklabels(all_labels, rotation=35, ha="right")
    ax.set_xlim(-0.6, QUASIMETA_X[-1] + 0.8)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Sponge incubation timepoint")


def fig_lm_vs_innocua_per_spiking(wide: pd.DataFrame) -> None:
    """Figure A: 3 panels (Lm2/Lm4/Lm6) — L. monocytogenes vs L. innocua over time."""
    sub = _base_filter(wide)
    species_keys = ["L. monocytogenes", "L. innocua"]

    fig, axes = plt.subplots(1, 3, figsize=(20, 7), sharey=False)
    rng = np.random.default_rng(42)

    for ax, tr in zip(axes, TREATMENT_ORDER):
        tr_data = sub[sub["Treatment"] == tr]
        _draw_baseline(ax, tr_data, species_keys, rng)
        _draw_species_lines(ax, tr_data, species_keys, rng)
        _format_ax(ax)
        ax.set_title(tr, fontsize=11, fontweight="bold")
        ax.set_ylabel("Reads (% of total sample)")

        n_samples = tr_data["basename"].nunique()
        ax.text(
            0.97, 0.97, f"n = {n_samples}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="#444",
        )

    # Build legend with baseline entry
    handles, labels = axes[-1].get_legend_handles_labels()
    handles.insert(0, mlines.Line2D([], [], color="grey", lw=1.2, ls="--",
                                     label="Metagenomics baseline\n(0 h, Lm mean \u00b1 SEM)"))
    axes[-1].legend(
        handles=handles,
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    fig.suptitle(
        "L. monocytogenes vs L. innocua enrichment over time (sponge, N)",
        fontsize=13, y=1.02,
    )
    fig.tight_layout(rect=[0, 0, 0.88, 1])
    _save(fig, "fig_lm_vs_innocua_per_spiking")
    plt.close(fig)


def fig_all_listeria_species_timecourse(wide: pd.DataFrame) -> None:
    """Figure B: single panel — all 4 Listeria species over time (Lm2-6 pooled)."""
    sub = _base_filter(wide)
    species_keys = list(SPECIES_CONFIG.keys())

    fig, ax = plt.subplots(figsize=(10, 7.5))
    rng = np.random.default_rng(77)

    _draw_baseline(ax, sub, species_keys, rng)
    _draw_species_lines(ax, sub, species_keys, rng)
    _format_ax(ax)
    ax.set_ylabel("Reads (% of total sample)")

    n_samples = sub["basename"].nunique()
    ax.text(
        0.97, 0.97, f"n = {n_samples} (Lm2-6 pooled)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8, color="#444",
    )

    # Build legend with baseline entry
    handles, labels = ax.get_legend_handles_labels()
    handles.insert(0, mlines.Line2D([], [], color="grey", lw=1.2, ls="--",
                                     label="Metagenomics baseline\n(0 h, Lm mean \u00b1 SEM)"))
    ax.legend(
        handles=handles,
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    fig.tight_layout(rect=[0, 0, 0.82, 1])
    _save(fig, "fig_all_listeria_species_timecourse")
    plt.close(fig)


def fig_all_species_per_spiking(wide: pd.DataFrame) -> None:
    """Figure C: 3 panels (Lm2/Lm4/Lm6) — all 4 Listeria species over time."""
    sub = _base_filter(wide)
    species_keys = list(SPECIES_CONFIG.keys())

    fig, axes = plt.subplots(1, 3, figsize=(20, 7), sharey=False)
    rng = np.random.default_rng(99)

    for ax, tr in zip(axes, TREATMENT_ORDER):
        tr_data = sub[sub["Treatment"] == tr]
        _draw_baseline(ax, tr_data, species_keys, rng)
        _draw_species_lines(ax, tr_data, species_keys, rng)
        _format_ax(ax)
        ax.set_title(tr, fontsize=11, fontweight="bold")
        ax.set_ylabel("Reads (% of total sample)")

        n_samples = tr_data["basename"].nunique()
        ax.text(
            0.97, 0.97, f"n = {n_samples}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="#444",
        )

    handles, labels = axes[-1].get_legend_handles_labels()
    handles.insert(0, mlines.Line2D([], [], color="grey", lw=1.2, ls="--",
                                     label="Metagenomics baseline\n(0 h, Lm mean \u00b1 SEM)"))
    axes[-1].legend(
        handles=handles,
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    fig.suptitle(
        "Listeria species enrichment over time (sponge, N)",
        fontsize=13, y=1.02,
    )
    fig.tight_layout(rect=[0, 0, 0.88, 1])
    _save(fig, "fig_all_species_per_spiking")
    plt.close(fig)


def _draw_baseline_colored(ax: plt.Axes, sub: pd.DataFrame, species_keys: list[str],
                            rng: np.random.Generator) -> None:
    """Per-species coloured 0h scatter at x=0. No axhline / axhspan."""
    base = sub[sub["timepoint"] == "0h"]
    if base.empty:
        return
    for sp_name in species_keys:
        cfg = SPECIES_CONFIG[sp_name]
        vals = base[cfg["col"]].dropna().to_numpy()
        if not len(vals):
            continue
        jitter = rng.uniform(-0.18, 0.18, size=len(vals))
        ax.scatter(
            np.zeros(len(vals)) + jitter,
            vals,
            color=cfg["color"],
            marker=cfg["marker"],
            s=22,
            alpha=0.45,
            zorder=2,
            linewidths=0.4,
            edgecolors="white",
        )


def _draw_species_lines_with_0h(
    ax: plt.Axes,
    sub: pd.DataFrame,
    species_keys: list[str],
    rng: np.random.Generator,
) -> None:
    """Mean +/- SEM lines that include 0h as the first point, connecting 0h -> 24h(2)."""
    tp_x_pairs = [("0h", 0)] + list(zip(QUASIMETA_TPS, QUASIMETA_X))
    for sp_name in species_keys:
        cfg = SPECIES_CONFIG[sp_name]
        col = cfg["col"]
        colour = cfg["color"]
        marker = cfg["marker"]

        xs: list[int] = []
        means: list[float] = []
        sems: list[float] = []

        for tp, x_pos in tp_x_pairs:
            vals = sub.loc[sub["timepoint"] == tp, col].dropna().to_numpy()
            if not len(vals):
                continue
            xs.append(x_pos)
            means.append(float(vals.mean()))
            sems.append(
                float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            )
            if tp != "0h":
                # 0h points are drawn by _draw_baseline_colored to keep the x=0 jitter
                # consistent with the existing baseline look; avoid double-plotting here.
                jitter = rng.uniform(-0.12, 0.12, size=len(vals))
                ax.scatter(
                    np.full(len(vals), x_pos) + jitter,
                    vals,
                    color=colour,
                    s=20,
                    alpha=0.40,
                    zorder=3,
                    linewidths=0,
                    edgecolors="none",
                )

        if xs:
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2,
                marker=marker, markersize=8,
                capsize=4, zorder=5,
                markeredgecolor="white", markeredgewidth=0.7,
                label=sp_name,
            )


def _clip_species_for_log(sub: pd.DataFrame, species_keys: list[str]) -> pd.DataFrame:
    """For the log10 variant: clip per-species % values < FLOOR_PCT up to the floor
    so they render at the bottom of the axis instead of falling off."""
    out = sub.copy()
    for sp_name in species_keys:
        col = SPECIES_CONFIG[sp_name]["col"]
        if col in out.columns:
            out.loc[out[col] < FLOOR_PCT, col] = FLOOR_PCT
    return out


def _build_species_timecourse_colored0h(
    wide: pd.DataFrame,
    *,
    yscale: str = "linear",
    out_dir: Path | None = None,
    stem: str = "fig_all_listeria_species_timecourse_colored0h",
) -> None:
    """Inner builder for the colored-0h species timecourse line plot.

    Three y-scale variants share this code path:
      yscale='linear' → published default; ymin=0
      yscale='log'    → log10 with FLOOR_PCT=1 % clipping; ticks at 10⁰/10¹/10²
      yscale='symlog' → linear 0→1 %, log above; handles true zeros without clipping
    """
    sub = _base_filter(wide)
    species_keys = list(SPECIES_CONFIG.keys())
    if yscale == "log":
        sub = _clip_species_for_log(sub, species_keys)

    fig, ax = plt.subplots(figsize=(10, 7.5))
    rng = np.random.default_rng(77)

    _draw_baseline_colored(ax, sub, species_keys, rng)
    _draw_species_lines_with_0h(ax, sub, species_keys, rng)
    _format_ax(ax)
    ax.set_ylabel("Reads (% of total sample)")

    if yscale in ("log", "symlog"):
        # Override the linear ylim from _format_ax. Top = 1.3× max observed
        # across all species.
        ymax = float(
            np.nanmax([
                sub[SPECIES_CONFIG[sp]["col"]].max() for sp in species_keys
                if SPECIES_CONFIG[sp]["col"] in sub.columns
            ])
        )
        if yscale == "log":
            ax.set_yscale("log")
            ax.set_ylim(bottom=FLOOR_PCT, top=max(ymax * 1.3, FLOOR_PCT * 100))
            ax.set_ylabel("Reads (% of total sample)  [log10, floor 1 %]")
        else:  # symlog
            ax.set_yscale("symlog", linthresh=LINTHRESH, linscale=0.4)
            ax.set_ylim(bottom=0, top=max(ymax * 1.3, LINTHRESH * 10))
            ax.set_ylabel("Reads (% of total sample)  [symlog, linthresh 1 %]")

    n_samples = sub["basename"].nunique()
    ax.text(
        0.97, 0.97, f"n = {n_samples} (Lm2-6 pooled)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=8, color="#444",
    )

    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    fig.tight_layout(rect=[0, 0, 0.82, 1])
    _save(fig, stem, out_dir=out_dir)
    plt.close(fig)


def fig_all_listeria_species_timecourse_colored0h(wide: pd.DataFrame) -> None:
    """Revised Figure 2 (line plot, linear). Published default; preserved
    byte-stable for the v5 bundle."""
    _build_species_timecourse_colored0h(
        wide, yscale="linear",
        stem="fig_all_listeria_species_timecourse_colored0h",
    )


def fig_all_listeria_species_timecourse_colored0h_log10(wide: pd.DataFrame) -> None:
    """Figure 2 log10 variant for v7 (FLOOR_PCT = 1 %). Stays a LINE plot
    per co-author spec (do NOT convert to boxplot)."""
    _build_species_timecourse_colored0h(
        wide, yscale="log",
        out_dir=OUT_DIR_V7,
        stem="2_fig_all_listeria_species_timecourse_colored0h_log10",
    )


def fig_all_listeria_species_timecourse_colored0h_log10_v8(wide: pd.DataFrame) -> None:
    """Figure 2 log10 variant for v8 — same plot as v7 but inherits the larger
    rcParams font sizes set at module load time."""
    _build_species_timecourse_colored0h(
        wide, yscale="log",
        out_dir=OUT_DIR_V8,
        stem="2_fig_all_listeria_species_timecourse_colored0h_log10",
    )


def _build_greybaseline_species_timecourse(
    wide: pd.DataFrame,
    *,
    species_config: dict,
    ylabel: str,
    suptitle: str,
    stem: str,
    out_dir: Path,
) -> None:
    """Grey 0 h baseline (mean ± SEM of Lm) + 4 Listeria species lines from
    4 h onwards with jittered replicates. Legend centered below. Shared
    builder for the per-read and per-base v8 variants."""
    sub = _base_filter(wide)
    species_keys = list(species_config.keys())

    fig, ax = plt.subplots(figsize=(11, 7.2))
    rng = np.random.default_rng(77)

    # ── Grey baseline at 0 h (uses Lm as the reference metric) ──────────
    base = sub[sub["timepoint"] == "0h"]
    lm_col = species_config["L. monocytogenes"]["col"]
    base_vals = base[lm_col].dropna().to_numpy() if not base.empty else np.array([])
    if len(base_vals):
        bm = float(base_vals.mean())
        bse = float(base_vals.std(ddof=1) / np.sqrt(len(base_vals))) if len(base_vals) > 1 else 0.0
        ax.axhspan(bm - bse, bm + bse, alpha=0.13, color="grey", zorder=0)
        ax.axhline(bm, color="grey", lw=1.2, ls="--", zorder=1)
        for sp_name in species_keys:
            vals = base[species_config[sp_name]["col"]].dropna().to_numpy()
            if not len(vals):
                continue
            jitter = rng.uniform(-0.18, 0.18, size=len(vals))
            ax.scatter(
                np.zeros(len(vals)) + jitter, vals,
                color="grey", s=20, alpha=0.45, zorder=2,
                linewidths=0.4, edgecolors="white",
            )

    # ── Species lines from 4 h onwards ──────────────────────────────────
    for sp_name in species_keys:
        cfg = species_config[sp_name]
        col, colour, marker = cfg["col"], cfg["color"], cfg["marker"]
        xs, means, sems = [], [], []
        for x_pos, tp in zip(QUASIMETA_X, QUASIMETA_TPS):
            vals = sub.loc[sub["timepoint"] == tp, col].dropna().to_numpy()
            if not len(vals):
                continue
            xs.append(x_pos)
            means.append(float(vals.mean()))
            sems.append(float(vals.std(ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0)
            jitter = rng.uniform(-0.12, 0.12, size=len(vals))
            ax.scatter(
                np.full(len(vals), x_pos) + jitter, vals,
                color=colour, s=20, alpha=0.40, zorder=3,
                linewidths=0, edgecolors="none",
            )
        if xs:
            ax.errorbar(
                xs, means, yerr=sems,
                color=colour, lw=2.2, marker=marker, markersize=8,
                capsize=4, zorder=5,
                markeredgecolor="white", markeredgewidth=0.7,
                label=sp_name,
            )

    _format_ax(ax)
    ax.set_ylabel(ylabel)

    # ── Legend below, baseline handle prepended ─────────────────────────
    n_samples = sub["basename"].nunique()
    baseline_handle = mlines.Line2D(
        [], [], color="grey", lw=1.2, ls="--",
        label="Metagenomics baseline (0 h, Lm mean ± SEM)",
    )
    handles, labels = ax.get_legend_handles_labels()
    handles = [baseline_handle] + handles
    labels = [baseline_handle.get_label()] + labels

    fig.legend(
        handles, labels,
        title=f"Listeria species  (n = {n_samples}, Lm2-6 pooled)",
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=len(labels),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    fig.suptitle(suptitle, fontsize=14)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.20)
    _save(fig, stem, out_dir=out_dir)
    plt.close(fig)


def fig_all_listeria_species_timecourse_greybaseline_v8(wide: pd.DataFrame) -> None:
    """Per-read species timecourse with grey 0 h baseline + legend below."""
    _build_greybaseline_species_timecourse(
        wide,
        species_config=SPECIES_CONFIG,
        ylabel="Reads (% of total sample)",
        suptitle="Listeria species dynamics during sponge quasimetagenomic enrichment",
        stem="2b_fig_all_listeria_species_timecourse_greybaseline",
        out_dir=OUT_DIR_V8,
    )


def fig_all_listeria_species_timecourse_greybaseline_bases_v8(wide: pd.DataFrame) -> None:
    """Per-base counterpart with the same grey baseline + legend-below layout."""
    _build_greybaseline_species_timecourse(
        wide,
        species_config=SPECIES_CONFIG_BASES,
        ylabel="Bases (% of total sample)",
        suptitle="Listeria species dynamics during sponge quasimetagenomic enrichment (bases)",
        stem="2c_fig_all_listeria_species_timecourse_greybaseline_bases",
        out_dir=OUT_DIR_V8,
    )


def fig_all_listeria_species_timecourse_colored0h_symlog(wide: pd.DataFrame) -> None:
    """Figure 2 symlog variant for v7_symlog (LINTHRESH = 1 %). Keeps true
    zeros visible on the linear stub instead of clipping to 1 %."""
    out_dir_symlog = ROOT / "outputs" / "email_package_v7_symlog"
    _build_species_timecourse_colored0h(
        wide, yscale="symlog",
        out_dir=out_dir_symlog,
        stem="2_fig_all_listeria_species_timecourse_colored0h_symlog",
    )


def main() -> None:
    _, wide = load_strain_long(DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA)
    wide = _add_species_pcts(wide)

    print(f"\n{'='*60}")
    print("Species time-course figures")
    print(f"{'='*60}\n")

    # Published PDFs are preserved per co-author review; only the revision
    # variant is written. Set FOODSAFETY_RERUN_ALL=1 to regenerate the
    # originals as well (they will render byte-identically given the seeded RNGs).
    import os
    if os.environ.get("FOODSAFETY_RERUN_ALL") == "1":
        fig_lm_vs_innocua_per_spiking(wide)
        fig_all_listeria_species_timecourse(wide)
        fig_all_species_per_spiking(wide)
        fig_all_listeria_species_timecourse_colored0h(wide)

    # v7 paper-ready variant — log10 line plot (Fig 2 in the manuscript)
    fig_all_listeria_species_timecourse_colored0h_log10(wide)
    # v7 symlog sibling (Fig 2 on a symlog line, for co-author comparison)
    fig_all_listeria_species_timecourse_colored0h_symlog(wide)
    # v8 paper-ready variant — same log10 line plot with updated fonts
    fig_all_listeria_species_timecourse_colored0h_log10_v8(wide)
    # v8 grey-baseline variants — 0h as grey mean ± SEM, species lines from 4h onwards
    fig_all_listeria_species_timecourse_greybaseline_v8(wide)
    fig_all_listeria_species_timecourse_greybaseline_bases_v8(wide)

    print(f"\nDone. Linear default: {OUT_DIR}")
    print(f"      log10 v7:         {OUT_DIR_V7}")
    print(f"      log10 v8:         {OUT_DIR_V8}")
    print(f"      symlog v7 sibling: {ROOT / 'outputs' / 'email_package_v7_symlog'}")


if __name__ == "__main__":
    main()
