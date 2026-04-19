#!/usr/bin/env python3
"""Boxplot + log-scale variants of the paper figures.

Default ``main()`` writes the v7 paper-ready set to ``outputs/email_package_v7/``:
median/IQR boxplots with read-based % only, replicates as independent points,
Lm2+Lm4+Lm6 pooled, blanks/backgrounds excluded.

Log y-axis convention (locked 2026-04-18 after Lara's review): plain ``log10``
with values clipped to ``FLOOR_PCT = 1.0`` so the y-axis bottoms out at 10⁰ = 1 %.
**No** ``log10(x + c)`` pseudocount — the 0.001 / 0.01 floors were overruled as
scientifically unsound for this dataset. Linear variants apply no clipping.

Figures (paper-figure numbering):
  1. Fig 1 — AS vs N sponge quasimeta (0h + 4h/12h/24h(1)/24h(2)), log10
  2. Fig 2 — All Listeria species timecourse (line plot, in plot_species_timecourse.py)
  3. Fig 3 — AS vs N per swab type, metagenomic, log10 + linear
  4. Fig 4 — Swab comparison N only, metagenomic, log10 + linear
  5. Fig 5 — Per-strain timecourse, mixed scales (Panel A log10 abs, Panel B linear rel)

Legacy v6/v8 entrypoints (``build_v6``-style symlog variants) are retained
for reproducibility but no longer wired into ``main()``.

Boxplots with n < 3 observations per cell collapse to a median bar + jittered
points (IQR/whiskers would mislead at tiny n).
"""
from __future__ import annotations

import sys
import warnings
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt           # noqa: E402
import matplotlib.patches as mpatches     # noqa: E402
import matplotlib.colors                  # noqa: E402
import matplotlib.lines                   # noqa: E402
import numpy as np                        # noqa: E402
import pandas as pd                       # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from plot_strain_long_format import (     # noqa: E402
    load_strain_long,
    LM_STRAINS, PALETTE_LM_STRAIN, LM_STRAIN_MARKERS,
    TREATMENT_ORDER, TP_ORDER, SWAB_ORDER,
    PALETTE_CONDITION, COND_MARKERS, PALETTE_SWAB,
    DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA,
)
from plot_species_timecourse import _add_species_pcts, SPECIES_CONFIG  # noqa: E402

warnings.filterwarnings("ignore")

ROOT = SCRIPTS.parent
OUT_DIR = ROOT / "outputs" / "email_package_v6"   # legacy default for v6 builders
OUT_DIR_V7 = ROOT / "outputs" / "email_package_v7"

FLOOR_PCT = 1.0    # hard-floor for log-scale (% reads); below this clipped
                   # so the y-axis starts at 10^0 = 1 % (convention: tick
                   # labels 10^0, 10^1, 10^2 — never 10^-1 / 10^-2).
LINTHRESH = 1.0    # symlog linear threshold (% reads); 0 -> 1 % rendered on a
                   # linear stub, log above 1 %. Keeps tick labels at 10^0+.

plt.rcParams.update({
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
})


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _save(fig: plt.Figure, stem: str, out_dir: Path | None = None) -> None:
    target = out_dir if out_dir is not None else OUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(target / f"{stem}.{ext}")
    print(f"[fig] wrote {target / stem}.{{pdf,png}}")


def _apply_scale(ax: plt.Axes, scale: str, y_max: float) -> None:
    """Apply ``linear``, ``symlog`` or ``log`` y-scale.

    Log axis convention: major ticks at 10^0, 10^1, 10^2 — never 10^-N.
    For ``log``: bottom fixed at 10^0 = 1 %; sub-1 % values clipped to
    the floor so they sit on the 1 % line. For ``symlog``: linear stub
    covers 0 -> 1 %, log region above. For ``linear``: plain [0, 1.1*max].
    """
    if scale == "symlog":
        ax.set_yscale("symlog", linthresh=LINTHRESH, linscale=0.4)
        top = max(y_max * 1.3, LINTHRESH * 10)
        ax.set_ylim(bottom=0, top=top)
    elif scale == "log":
        ax.set_yscale("log")
        top = max(y_max * 1.3, FLOOR_PCT * 100)
        ax.set_ylim(bottom=FLOOR_PCT, top=top)
    elif scale == "linear":
        ax.set_yscale("linear")
        ax.set_ylim(bottom=0, top=max(y_max * 1.15, 1.0))
    else:
        raise ValueError(f"Unknown scale: {scale}")


def _clip_for_log(vals: np.ndarray, scale: str) -> np.ndarray:
    """For the ``log`` variant, clip non-positive values to ``FLOOR_PCT`` so
    they render at the bottom of the axis instead of being dropped."""
    if scale == "log":
        out = np.asarray(vals, dtype=float).copy()
        out[out < FLOOR_PCT] = FLOOR_PCT
        return out
    return np.asarray(vals, dtype=float)


def _draw_box_or_point(
    ax: plt.Axes,
    x: float,
    vals: np.ndarray,
    color: str,
    marker: str,
    width: float,
    seed: int,
) -> None:
    """Draw a median/IQR box with jittered points on top.

    At n < 3 the box collapses visually, so fall back to a short median bar
    plus the individual points — honest at very small sample sizes.
    """
    vals = np.asarray(vals, dtype=float)
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return

    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-width * 0.35, width * 0.35, size=len(vals))

    if len(vals) >= 3:
        q1, med, q3 = np.percentile(vals, [25, 50, 75])
        iqr = q3 - q1
        lo = max(vals.min(), q1 - 1.5 * iqr)
        hi = min(vals.max(), q3 + 1.5 * iqr)

        half = width / 2
        box = plt.Rectangle(
            (x - half, q1), width, max(iqr, 1e-12),
            facecolor=matplotlib.colors.to_rgba(color, 0.25),
            edgecolor="black", linewidth=1.0, zorder=2,
        )
        ax.add_patch(box)
        ax.plot([x - half, x + half], [med, med], color="black", lw=2.0,
                zorder=4, solid_capstyle="butt")
        ax.plot([x, x], [q1, lo], color="black", lw=0.9, zorder=3)
        ax.plot([x, x], [q3, hi], color="black", lw=0.9, zorder=3)
        cap_w = half * 0.5
        ax.plot([x - cap_w, x + cap_w], [lo, lo], color="black", lw=0.9, zorder=3)
        ax.plot([x - cap_w, x + cap_w], [hi, hi], color="black", lw=0.9, zorder=3)
    else:
        med = float(np.median(vals))
        half = width / 2
        ax.plot([x - half, x + half], [med, med], color=color, lw=2.2,
                zorder=4, solid_capstyle="butt")

    ax.scatter(
        x + jitter, vals,
        color=color, marker=marker, s=22, alpha=0.75,
        zorder=5, linewidths=0.3, edgecolors="white",
    )


def _legend(ax, handles, **kwargs) -> None:
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
              frameon=False, fontsize=9, **kwargs)


# --------------------------------------------------------------------------- #
# Data filters                                                                #
# --------------------------------------------------------------------------- #
def _sponge_lm_nonctrl(wide: pd.DataFrame) -> pd.DataFrame:
    return wide[
        (wide["swab_type"] == "Sponge")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()


def _sponge_N(wide: pd.DataFrame) -> pd.DataFrame:
    sub = _sponge_lm_nonctrl(wide)
    return sub[sub["condition"] == "N"].copy()


def _metagenomic(wide: pd.DataFrame) -> pd.DataFrame:
    return wide[
        (wide["round"] == 1)
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
    ].copy()


# --------------------------------------------------------------------------- #
# Fig 1 — AS vs N sponge quasimeta, boxplots incl. 0h, log y                  #
# --------------------------------------------------------------------------- #
def fig1_AS_vs_N_sponge_quasimeta(
    wide: pd.DataFrame,
    scale: str,
    *,
    out_dir: Path | None = None,
    stem: str | None = None,
) -> None:
    sub = _sponge_lm_nonctrl(wide)
    tps = [tp for tp in TP_ORDER if (sub["timepoint"] == tp).any()]
    n_tps = len(tps)

    fig, ax = plt.subplots(figsize=(2.7 * n_tps + 3.2, 6.4))
    y_all: list[float] = []

    for i, tp in enumerate(tps):
        tp_data = sub[sub["timepoint"] == tp]
        for cond, offset, seed_off in [("AS", -0.22, 0), ("N", 0.22, 1)]:
            vals = tp_data.loc[tp_data["condition"] == cond, "lm_pct_total_reads"].dropna().to_numpy()
            if not len(vals):
                continue
            y_all.extend(vals.tolist())
            vals_plot = _clip_for_log(vals, scale)
            _draw_box_or_point(
                ax, i + offset, vals_plot,
                PALETTE_CONDITION[cond], COND_MARKERS[cond],
                width=0.38, seed=i * 7 + seed_off,
            )

    ax.set_xticks(range(n_tps))
    ax.set_xticklabels(tps)
    ax.set_xlim(-0.6, n_tps - 0.4)
    ax.set_xlabel("Sponge incubation timepoint")
    ax.set_ylabel("Lm reads (%)")
    _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    _legend(ax, [
        mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["AS"], 0.35),
                       label="Adaptive Sampling (AS)"),
        mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["N"], 0.35),
                       label="Native (N)"),
    ])
    fig.tight_layout(rect=[0, 0, 0.86, 1])
    _save(fig, stem or f"1_fig_AS_vs_N_sponge_quasimeta_boxplot_{scale}", out_dir=out_dir)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 2 — Per-Lm (Lm2 / Lm4 / Lm6) sponge N timecourse, boxplots, log y       #
# --------------------------------------------------------------------------- #
def fig2_per_Lm_timecourse(wide: pd.DataFrame, scale: str) -> None:
    sub = _sponge_N(wide)
    tps = TP_ORDER

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8), sharey=(scale != "log"))
    panel_colours = {"Lm2": "#2E75B6", "Lm4": "#2CA02C", "Lm6": "#D55E00"}

    y_max_global = 0.0
    for tr in TREATMENT_ORDER:
        vals = sub.loc[sub["Treatment"] == tr, "lm_pct_total_reads"].dropna().to_numpy()
        if len(vals):
            y_max_global = max(y_max_global, float(vals.max()))

    for ax, tr in zip(axes, TREATMENT_ORDER):
        tr_data = sub[sub["Treatment"] == tr]
        colour = panel_colours[tr]
        n_basenames = tr_data["basename"].nunique()
        for i, tp in enumerate(tps):
            vals = tr_data.loc[tr_data["timepoint"] == tp, "lm_pct_total_reads"].dropna().to_numpy()
            if not len(vals):
                continue
            vals_plot = _clip_for_log(vals, scale)
            _draw_box_or_point(
                ax, i, vals_plot, colour, marker="o",
                width=0.55, seed=i * 11,
            )

        ax.set_xticks(range(len(tps)))
        ax.set_xticklabels(tps, rotation=30, ha="right")
        ax.set_xlim(-0.55, len(tps) - 0.45)
        ax.set_xlabel("Sponge quasimeta timepoint")
        ax.set_ylabel("Lm reads (%)")
        ax.set_title(f"{tr} (N, sponge)  n={n_basenames}", fontsize=11)
        _apply_scale(ax, scale, y_max_global if scale != "log" else y_max_global)

    fig.suptitle(
        "Sponge quasimetagenomic timecourse, N only — stratified by Lm spiking level",
        fontsize=12, y=1.02,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, f"2_fig_timecourse_N_sponge_per_Lm_boxplot_{scale}")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 3 — All 4 Listeria species timecourse, grouped boxplots, log y          #
# --------------------------------------------------------------------------- #
def fig3_all_species_timecourse(wide: pd.DataFrame, scale: str) -> None:
    sub = _sponge_N(wide)
    tps = TP_ORDER
    species_keys = list(SPECIES_CONFIG.keys())
    n_species = len(species_keys)

    # Offsets: distribute species within [-0.36, +0.36] window per timepoint.
    span = 0.72
    offsets = np.linspace(-span / 2, span / 2, n_species)
    width = 0.15

    fig, ax = plt.subplots(figsize=(12, 6.5))
    y_all: list[float] = []

    for i, tp in enumerate(tps):
        tp_data = sub[sub["timepoint"] == tp]
        for sp_idx, sp_name in enumerate(species_keys):
            cfg = SPECIES_CONFIG[sp_name]
            vals = tp_data[cfg["col"]].dropna().to_numpy()
            if not len(vals):
                continue
            y_all.extend(vals.tolist())
            vals_plot = _clip_for_log(vals, scale)
            _draw_box_or_point(
                ax, i + offsets[sp_idx], vals_plot,
                cfg["color"], cfg["marker"],
                width=width, seed=i * 17 + sp_idx,
            )

    ax.set_xticks(range(len(tps)))
    ax.set_xticklabels(tps)
    ax.set_xlim(-0.55, len(tps) - 0.45)
    ax.set_xlabel("Sponge quasimeta timepoint")
    ax.set_ylabel("Reads (% of total sample)")
    _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    n_basenames = sub["basename"].nunique()
    ax.text(0.99, 0.99, f"n = {n_basenames} (Lm2-6 pooled)",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="#444")

    _legend(ax, [
        matplotlib.lines.Line2D(
            [], [], color=SPECIES_CONFIG[sp]["color"], lw=0,
            marker=SPECIES_CONFIG[sp]["marker"], markersize=8,
            markeredgecolor="white", markeredgewidth=0.7,
            label=sp,
        )
        for sp in species_keys
    ])
    fig.tight_layout(rect=[0, 0, 0.84, 1])
    _save(fig, f"3_fig_all_species_timecourse_boxplot_{scale}")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 4 — Swab-type comparison, metagenomic N, boxplots, log y                #
# --------------------------------------------------------------------------- #
def fig4_swab_comparison_N(
    wide: pd.DataFrame,
    scale: str,
    *,
    out_dir: Path | None = None,
    stem: str | None = None,
) -> None:
    meta_n = _metagenomic(wide)
    meta_n = meta_n[meta_n["condition"] == "N"].copy()

    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    y_all: list[float] = []
    for i, swab in enumerate(SWAB_ORDER):
        vals = meta_n.loc[meta_n["swab_type"] == swab, "lm_pct_total_reads"].dropna().to_numpy()
        if not len(vals):
            continue
        y_all.extend(vals.tolist())
        vals_plot = _clip_for_log(vals, scale)
        _draw_box_or_point(
            ax, i, vals_plot, PALETTE_SWAB[swab], marker="o",
            width=0.55, seed=i * 11,
        )

    ax.set_xticks(range(len(SWAB_ORDER)))
    ax.set_xticklabels(SWAB_ORDER)
    ax.set_xlim(-0.6, len(SWAB_ORDER) - 0.4)
    ax.set_xlabel("Swab type")
    ax.set_ylabel("Lm reads / total sample reads (%)")
    _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    _legend(ax, [mpatches.Patch(color=PALETTE_SWAB[s], label=s) for s in SWAB_ORDER])
    fig.tight_layout(rect=[0, 0, 0.85, 1])
    _save(fig, stem or f"4_fig_swab_comparison_N_only_boxplot_{scale}", out_dir=out_dir)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 5 — Per-strain timecourse (4 Lm strains), grouped boxplots, 2 panels    #
# --------------------------------------------------------------------------- #
def fig5_per_strain_timecourse(wide: pd.DataFrame, scale: str) -> None:
    sub = _sponge_N(wide)
    tps = TP_ORDER
    n_strains = len(LM_STRAINS)
    span = 0.72
    offsets = np.linspace(-span / 2, span / 2, n_strains)
    width = 0.15

    fig, (ax_abs, ax_rel) = plt.subplots(1, 2, figsize=(16, 5.8))

    def _draw_panel(ax: plt.Axes, metric_tpl: str, ylabel: str, title: str) -> None:
        y_all: list[float] = []
        for i, tp in enumerate(tps):
            tp_data = sub[sub["timepoint"] == tp]
            for s_idx, strain in enumerate(LM_STRAINS):
                col = metric_tpl.format(strain=strain)
                if col not in tp_data.columns:
                    continue
                vals = tp_data[col].dropna().to_numpy()
                if not len(vals):
                    continue
                y_all.extend(vals.tolist())
                vals_plot = _clip_for_log(vals, scale)
                _draw_box_or_point(
                    ax, i + offsets[s_idx], vals_plot,
                    PALETTE_LM_STRAIN[strain], LM_STRAIN_MARKERS[strain],
                    width=width, seed=i * 17 + s_idx,
                )
        ax.set_xticks(range(len(tps)))
        ax.set_xticklabels(tps, rotation=30, ha="right")
        ax.set_xlim(-0.55, len(tps) - 0.45)
        ax.set_xlabel("Sponge quasimeta timepoint (N samples)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    _draw_panel(
        ax_abs, "{strain}_pct_sample_total",
        "Strain reads / total sample reads (%)",
        "Absolute strain abundance",
    )
    _draw_panel(
        ax_rel, "{strain}_pct_within_lm",
        "Strain reads / Lm-mapped reads (%)",
        "Relative strain composition (within Lm pool)",
    )
    ax_rel.legend(
        handles=[
            matplotlib.lines.Line2D(
                [], [], color=PALETTE_LM_STRAIN[s], lw=0,
                marker=LM_STRAIN_MARKERS[s], markersize=8,
                markeredgecolor="white", markeredgewidth=0.7,
                label=s,
            ) for s in LM_STRAINS
        ],
        title="L. monocytogenes strain",
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9, title_fontsize=10,
    )

    n_basenames = sub["basename"].nunique()
    ax_rel.text(0.99, 0.99, f"n = {n_basenames}",
                transform=ax_rel.transAxes, ha="right", va="top",
                fontsize=8, color="#444")

    fig.suptitle(
        "Per-strain relative abundance across the quasimetagenomic timeline",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 0.90, 0.96])
    _save(fig, f"5_fig_strain_timecourse_boxplot_{scale}")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 5 — right panel only (relative within-Lm composition), pure log10       #
# Carved out as a standalone: it's the only panel in the whole paper where    #
# 100% of data points sit >= 1 %, so pure log10 is scientifically appropriate.#
# --------------------------------------------------------------------------- #
def fig5_right_panel_log10_only(wide: pd.DataFrame) -> None:
    sub = _sponge_N(wide)
    tps = TP_ORDER
    span = 0.72
    offsets = np.linspace(-span / 2, span / 2, len(LM_STRAINS))
    width = 0.15

    fig, ax = plt.subplots(figsize=(10, 6.2))

    y_all: list[float] = []
    for i, tp in enumerate(tps):
        tp_data = sub[sub["timepoint"] == tp]
        for s_idx, strain in enumerate(LM_STRAINS):
            col = f"{strain}_pct_within_lm"
            if col not in tp_data.columns:
                continue
            vals = tp_data[col].dropna().to_numpy()
            if not len(vals):
                continue
            y_all.extend(vals.tolist())
            vals_plot = _clip_for_log(vals, "log")
            _draw_box_or_point(
                ax, i + offsets[s_idx], vals_plot,
                PALETTE_LM_STRAIN[strain], LM_STRAIN_MARKERS[strain],
                width=width, seed=i * 17 + s_idx,
            )

    ax.set_xticks(range(len(tps)))
    ax.set_xticklabels(tps)
    ax.set_xlim(-0.55, len(tps) - 0.45)
    ax.set_xlabel("Sponge quasimeta timepoint (N samples)")
    ax.set_ylabel("Strain reads / Lm-mapped reads (%)")
    ax.set_title("Relative strain composition within Lm pool", fontsize=11)
    _apply_scale(ax, "log", max(y_all) if y_all else 1.0)

    n_basenames = sub["basename"].nunique()
    ax.text(0.99, 0.99, f"n = {n_basenames}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color="#444")

    ax.legend(
        handles=[
            matplotlib.lines.Line2D(
                [], [], color=PALETTE_LM_STRAIN[s], lw=0,
                marker=LM_STRAIN_MARKERS[s], markersize=8,
                markeredgecolor="white", markeredgewidth=0.7,
                label=s,
            ) for s in LM_STRAINS
        ],
        title="L. monocytogenes strain",
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9, title_fontsize=10,
    )
    fig.tight_layout(rect=[0, 0, 0.83, 1])

    # Separate output dir — this is the *only* pure-log10 plot that is
    # scientifically appropriate for this dataset.
    out = ROOT / "outputs" / "email_package_v6_log10_only"
    out.mkdir(parents=True, exist_ok=True)
    stem = "5_fig_strain_composition_within_Lm_boxplot_log10"
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{stem}.{ext}")
    print(f"[fig] wrote {out / stem}.{{pdf,png}}")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 3 (paper) — AS vs N per swab type, metagenomic, boxplots                #
# Distinct from the v6 ``fig3_all_species_timecourse`` (which is the species  #
# boxplot variant of Fig 2 and is *not* used in v7).                          #
# --------------------------------------------------------------------------- #
def fig3_AS_vs_N_per_swab_metagenomic(
    wide: pd.DataFrame,
    scale: str,
    *,
    out_dir: Path | None = None,
    stem: str | None = None,
) -> None:
    meta = _metagenomic(wide)

    fig, ax = plt.subplots(figsize=(2.7 * len(SWAB_ORDER) + 3.2, 6.4))
    y_all: list[float] = []

    for i, swab in enumerate(SWAB_ORDER):
        swab_data = meta[meta["swab_type"] == swab]
        for cond, offset, seed_off in [("AS", -0.22, 0), ("N", 0.22, 1)]:
            vals = swab_data.loc[swab_data["condition"] == cond, "lm_pct_total_reads"].dropna().to_numpy()
            if not len(vals):
                continue
            y_all.extend(vals.tolist())
            vals_plot = _clip_for_log(vals, scale)
            _draw_box_or_point(
                ax, i + offset, vals_plot,
                PALETTE_CONDITION[cond], COND_MARKERS[cond],
                width=0.38, seed=i * 13 + seed_off,
            )

    ax.set_xticks(range(len(SWAB_ORDER)))
    ax.set_xticklabels(SWAB_ORDER)
    ax.set_xlim(-0.6, len(SWAB_ORDER) - 0.4)
    ax.set_xlabel("Swab type (metagenomic, 0h baseline)")
    ax.set_ylabel("Lm reads (%)")
    _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    _legend(ax, [
        mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["AS"], 0.35),
                       label="Adaptive Sampling (AS)"),
        mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["N"], 0.35),
                       label="Native (N)"),
    ])
    fig.tight_layout(rect=[0, 0, 0.86, 1])
    _save(fig, stem or f"3_fig_AS_vs_N_per_swab_metagenomic_boxplot_{scale}", out_dir=out_dir)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Fig 5 (paper) — Per-strain timecourse, mixed-scale two-panel                #
# Panel A: absolute strain abundance (% of total sample reads) — log10        #
# Panel B: within-Lm composition (% of Lm-mapped reads)         — linear      #
# Distinct from ``fig5_per_strain_timecourse`` which forces same scale on     #
# both panels.                                                                #
# --------------------------------------------------------------------------- #
def fig5_per_strain_timecourse_mixed(
    wide: pd.DataFrame,
    *,
    out_dir: Path | None = None,
    stem: str | None = None,
) -> None:
    sub = _sponge_N(wide)
    tps = TP_ORDER
    n_strains = len(LM_STRAINS)
    span = 0.72
    offsets = np.linspace(-span / 2, span / 2, n_strains)
    width = 0.15

    fig, (ax_abs, ax_rel) = plt.subplots(1, 2, figsize=(16, 5.8))

    def _draw_panel(ax: plt.Axes, metric_tpl: str, ylabel: str, title: str, scale: str) -> None:
        y_all: list[float] = []
        for i, tp in enumerate(tps):
            tp_data = sub[sub["timepoint"] == tp]
            for s_idx, strain in enumerate(LM_STRAINS):
                col = metric_tpl.format(strain=strain)
                if col not in tp_data.columns:
                    continue
                vals = tp_data[col].dropna().to_numpy()
                if not len(vals):
                    continue
                y_all.extend(vals.tolist())
                vals_plot = _clip_for_log(vals, scale)
                _draw_box_or_point(
                    ax, i + offsets[s_idx], vals_plot,
                    PALETTE_LM_STRAIN[strain], LM_STRAIN_MARKERS[strain],
                    width=width, seed=i * 17 + s_idx,
                )
        ax.set_xticks(range(len(tps)))
        ax.set_xticklabels(tps, rotation=30, ha="right")
        ax.set_xlim(-0.55, len(tps) - 0.45)
        ax.set_xlabel("Sponge quasimeta timepoint (N samples)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        _apply_scale(ax, scale, max(y_all) if y_all else 1.0)

    _draw_panel(
        ax_abs, "{strain}_pct_sample_total",
        "Strain reads / total sample reads (%)  [log10]",
        "Absolute strain abundance",
        scale="log",
    )
    _draw_panel(
        ax_rel, "{strain}_pct_within_lm",
        "Strain reads / Lm-mapped reads (%)  [linear]",
        "Relative strain composition (within Lm pool)",
        scale="linear",
    )
    ax_rel.legend(
        handles=[
            matplotlib.lines.Line2D(
                [], [], color=PALETTE_LM_STRAIN[s], lw=0,
                marker=LM_STRAIN_MARKERS[s], markersize=8,
                markeredgecolor="white", markeredgewidth=0.7,
                label=s,
            ) for s in LM_STRAINS
        ],
        title="L. monocytogenes strain",
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9, title_fontsize=10,
    )

    n_basenames = sub["basename"].nunique()
    ax_rel.text(0.99, 0.99, f"n = {n_basenames}",
                transform=ax_rel.transAxes, ha="right", va="top",
                fontsize=8, color="#444")

    fig.suptitle(
        "Per-strain abundance across the quasimetagenomic timeline "
        "(Panel A log10, Panel B linear)",
        fontsize=13,
    )
    fig.tight_layout(rect=[0, 0, 0.90, 0.96])
    _save(fig, stem or "5_fig_strain_timecourse_boxes_log10", out_dir=out_dir)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# v7 build driver — paper-ready bundle for email_package_v7/                  #
# --------------------------------------------------------------------------- #
def build_v7(wide: pd.DataFrame) -> None:
    """Final paper figure set per 2026-04-19 co-author spec.

    Floor convention: log y-axis bottoms at FLOOR_PCT = 1 % (Lara 2026-04-18).
    No log10(x + c) pseudocount. Linear variants are unclipped.

    Outputs (all to outputs/email_package_v7/):
      1_fig_AS_vs_N_sponge_quasimeta_boxes_log10              — Fig 1, log10
      3_fig_AS_vs_N_per_swab_metagenomic_boxes_log10          — Fig 3, log10
      3_fig_AS_vs_N_per_swab_metagenomic_boxes_linear         — Fig 3, linear
      4_fig_swab_comparison_N_only_boxes_log10                — Fig 4, log10
      4_fig_swab_comparison_N_only_boxes_linear               — Fig 4, linear
      5_fig_strain_timecourse_boxes_log10                     — Fig 5, mixed scales

    Fig 2 (line plot, log10) is built by plot_species_timecourse.py.
    """
    out = OUT_DIR_V7

    fig1_AS_vs_N_sponge_quasimeta(
        wide, "log",
        out_dir=out,
        stem="1_fig_AS_vs_N_sponge_quasimeta_boxes_log10",
    )
    fig3_AS_vs_N_per_swab_metagenomic(
        wide, "log",
        out_dir=out,
        stem="3_fig_AS_vs_N_per_swab_metagenomic_boxes_log10",
    )
    fig3_AS_vs_N_per_swab_metagenomic(
        wide, "linear",
        out_dir=out,
        stem="3_fig_AS_vs_N_per_swab_metagenomic_boxes_linear",
    )
    fig4_swab_comparison_N(
        wide, "log",
        out_dir=out,
        stem="4_fig_swab_comparison_N_only_boxes_log10",
    )
    fig4_swab_comparison_N(
        wide, "linear",
        out_dir=out,
        stem="4_fig_swab_comparison_N_only_boxes_linear",
    )
    fig5_per_strain_timecourse_mixed(
        wide,
        out_dir=out,
        stem="5_fig_strain_timecourse_boxes_log10",
    )


# --------------------------------------------------------------------------- #
# Entrypoint                                                                  #
# --------------------------------------------------------------------------- #
def _save_v8(fig: plt.Figure, stem: str) -> None:
    out = ROOT / "outputs" / "email_package_v8"
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{stem}.{ext}")
    print(f"[v8] wrote {out / stem}.{{pdf,png}}")


def build_v8(wide: pd.DataFrame) -> None:
    """Trimmed deliverable per Lara's 2026-04-17 email:
       convert the remaining mean/SEM plots (Fig 2, Fig 3, Fig 5) to boxplots;
       apply log only where the data range justifies it.
    """
    # Fig 2 — per-Lm timecourse, linear (narrow per-panel ranges)
    fig2_per_Lm_timecourse(wide, "linear")
    # The existing fig2 saves to OUT_DIR (email_package_v6); move/copy to v8:
    for ext in ("pdf", "png"):
        src = OUT_DIR / f"2_fig_timecourse_N_sponge_per_Lm_boxplot_linear.{ext}"
        dst = ROOT / "outputs" / "email_package_v8" / f"Fig2_per_Lm_timecourse_boxplot_linear.{ext}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            dst.write_bytes(src.read_bytes())
    print(f"[v8] Fig 2 (linear) -> email_package_v8/")

    # Fig 3 — species timecourse, symlog (spans 0.05 -> 40 %)
    fig3_all_species_timecourse(wide, "symlog")
    for ext in ("pdf", "png"):
        src = OUT_DIR / f"3_fig_all_species_timecourse_boxplot_symlog.{ext}"
        dst = ROOT / "outputs" / "email_package_v8" / f"Fig3_species_timecourse_boxplot_symlog.{ext}"
        if src.exists():
            dst.write_bytes(src.read_bytes())
    print(f"[v8] Fig 3 (symlog) -> email_package_v8/")

    # Fig 5 — per-strain timecourse, symlog (abs panel mostly sub-1 %; rel 4-70 %)
    fig5_per_strain_timecourse(wide, "symlog")
    for ext in ("pdf", "png"):
        src = OUT_DIR / f"5_fig_strain_timecourse_boxplot_symlog.{ext}"
        dst = ROOT / "outputs" / "email_package_v8" / f"Fig5_per_strain_boxplot_symlog.{ext}"
        if src.exists():
            dst.write_bytes(src.read_bytes())
    print(f"[v8] Fig 5 (symlog) -> email_package_v8/")

    # Fig 5 right panel standalone, pure log10 (all cells >= 1 %)
    fig5_right_panel_log10_only(wide)
    for ext in ("pdf", "png"):
        src = ROOT / "outputs" / "email_package_v6_log10_only" / f"5_fig_strain_composition_within_Lm_boxplot_log10.{ext}"
        dst = ROOT / "outputs" / "email_package_v8" / f"Fig5_strain_composition_boxplot_log10.{ext}"
        if src.exists():
            dst.write_bytes(src.read_bytes())
    print(f"[v8] Fig 5 right panel (log10) -> email_package_v8/")


def main() -> None:
    _, wide = load_strain_long(DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA)
    wide = _add_species_pcts(wide)

    print(f"\n{'='*60}")
    print("v7 paper-ready bundle (FLOOR_PCT=1.0, no pseudocount)")
    print(f"{'='*60}\n")
    build_v7(wide)
    print(f"\nDone. Output: {OUT_DIR_V7}")
    print("Fig 2 (line plot, log10) is built by plot_species_timecourse.py.")


if __name__ == "__main__":
    main()
