#!/usr/bin/env python3
"""Regenerate Fig 5 (AS vs N sponge quasimeta, Lm2-6 pooled) with the
sponge metagenomic baseline (mean ± SEM) as a horizontal reference line.

Outputs only to  outputs/email_package_v4/5_fig_AS_vs_N_sponge_quasimeta.pdf
No other files are touched.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt           # noqa: E402
import matplotlib.patches as mpatches     # noqa: E402
import matplotlib.colors                  # noqa: E402
import matplotlib.lines                   # noqa: E402
import numpy as np                        # noqa: E402

# ── project imports ──────────────────────────────────────────────────────
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from plot_listeria_publication_v4 import boxplot_manual, mwu_pr, safe_top  # noqa: E402
from plot_strain_long_format import (                                       # noqa: E402
    load_strain_long,
    PALETTE_CONDITION, COND_MARKERS, TREATMENT_ORDER, TP_ORDER,
    DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA,
)

warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────
ROOT = SCRIPTS.parent
OUT_DIR = ROOT / "outputs" / "email_package_v4"

# ── rcParams (match plot_strain_long_format.py) ──────────────────────────
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


def main() -> None:
    # Load data (same pipeline as plot_strain_long_format.py)
    _, wide = load_strain_long(DEFAULT_INPUT, DEFAULT_READ_METRICS, DEFAULT_SAMPLE_METADATA)

    # ── metagenomic sponge baseline (0 h, N-only) ───────────────────────
    base_mask = (
        (wide["swab_type"] == "Sponge")
        & (wide["timepoint"] == "0h")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
        & (wide["condition"] == "N")
    )
    base_vals = wide.loc[base_mask, "lm_pct_total_reads"].dropna()
    bm = float(base_vals.mean())
    bse = float(base_vals.std(ddof=1) / np.sqrt(len(base_vals))) if len(base_vals) > 1 else 0.0
    print(f"[baseline] N-only sponge metagenomics 0 h: mean={bm:.4f}%, SEM={bse:.4f}%, n={len(base_vals)}")

    # ── quasimeta subset (same filter as fig_AS_vs_N_sponge_quasimeta) ──
    sub = wide[
        (wide["swab_type"] == "Sponge")
        & (~wide["is_control"].fillna(False))
        & (wide["Treatment"].isin(TREATMENT_ORDER))
        & (wide["timepoint"] != "0h")
    ].copy()

    tps = [tp for tp in TP_ORDER if tp != "0h" and (sub["timepoint"] == tp).any()]
    n_tps = len(tps)

    fig, ax = plt.subplots(figsize=(2.7 * n_tps + 3.2, 6.4))
    y_all: list[float] = []

    for i, tp in enumerate(tps):
        tp_data = sub[sub["timepoint"] == tp]
        as_v = tp_data.loc[tp_data["condition"] == "AS", "lm_pct_total_reads"].dropna()
        n_v  = tp_data.loc[tp_data["condition"] == "N",  "lm_pct_total_reads"].dropna()

        boxplot_manual(
            ax, i - 0.22, as_v, PALETTE_CONDITION["AS"],
            width=0.38, marker=COND_MARKERS["AS"], seed=i * 7,
        )
        boxplot_manual(
            ax, i + 0.22, n_v, PALETTE_CONDITION["N"],
            width=0.38, marker=COND_MARKERS["N"], seed=i * 7 + 1,
        )
        y_all.extend(as_v.tolist() + n_v.tolist())

    # ── draw baseline ────────────────────────────────────────────────────
    ax.axhspan(bm - bse, bm + bse, alpha=0.13, color="grey", zorder=0)
    ax.axhline(bm, color="grey", lw=1.2, ls="--", zorder=1)

    y_max = safe_top(y_all, 1.10)

    ax.set_xticks(range(n_tps))
    ax.set_xticklabels(tps)
    ax.set_xlim(-0.6, n_tps - 0.4)
    ax.set_ylim(bottom=0, top=y_max * 1.12 if y_max > 0 else 1.0)
    ax.set_xlabel("Sponge incubation timepoint")
    ax.set_ylabel("Lm reads (%)")

    # ── legend (AS / N patches + baseline line) ──────────────────────────
    ax.legend(
        handles=[
            mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["AS"], 0.35),
                           label="Adaptive Sampling (AS)"),
            mpatches.Patch(color=matplotlib.colors.to_rgba(PALETTE_CONDITION["N"], 0.35),
                           label="Native (N)"),
            matplotlib.lines.Line2D([], [], color="grey", lw=1.2, ls="--",
                                     label="Metagenomic baseline (0 h, mean ± SEM)"),
        ],
        loc="upper left", bbox_to_anchor=(1.02, 1.0),
        frameon=False, fontsize=9,
    )

    fig.tight_layout(rect=[0, 0, 0.86, 1])

    # ── save ─────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "5_fig_AS_vs_N_sponge_quasimeta.pdf"
    fig.savefig(out_path)
    print(f"[fig] wrote {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
