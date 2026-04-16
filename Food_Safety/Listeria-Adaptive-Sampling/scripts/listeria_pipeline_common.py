from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT / "listeria_reads.csv"
DEFAULT_INPUT_SHEET = "Data"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"

TIMEPOINT_ORDER = ["0h", "4h", "12h", "24h (1)", "24h (2)"]
TIMEPOINT_DISPLAY_ORDER = ["0h", "4h", "12h", "24h"]
TREATMENT_ORDER = ["Lm2", "Lm4", "Lm6"]
SWAB_ORDER = ["Sponge", "Cotton", "Zymo"]
CONDITION_ORDER = ["N", "AS"]
LM_STRAINS = ["EGDe", "LL195", "LMNC326", "N13-0119"]
OTHER_STRAINS = ["L. innocua J5051", "L. ivanovii Nr26", "L. welshimeri Nr14"]
ALL_STRAINS = LM_STRAINS + OTHER_STRAINS

TIMEPOINT_MAP = {
    "metagenomics": "0h",
    "quasimeta_4h": "4h",
    "quasimeta_12h": "12h",
    "quasimeta_24h_1": "24h (1)",
    "quasimeta_24h_2": "24h (2)",
}

CATEGORICAL_COLUMNS = {
    "Sample Type",
    "Condition",
    "Treatment",
    "Lab ID",
    "Swab Type",
    "Extraction Kit",
    "Detected Strains",
    "Dominant Lm Strain",
}


@dataclass(frozen=True)
class PipelinePaths:
    input_path: Path
    sheet_name: str
    output_root: Path

    @property
    def optional_dir(self) -> Path:
        return self.output_root / "optional"

    @property
    def publication_dir(self) -> Path:
        return self.output_root / "publication_v4"

    @property
    def final_table_path(self) -> Path:
        return self.output_root / "listeria_final_table.xlsx"


def build_pipeline_paths(
    input_path: str | Path | None = None,
    sheet_name: str = DEFAULT_INPUT_SHEET,
    output_root: str | Path | None = None,
) -> PipelinePaths:
    return PipelinePaths(
        input_path=Path(input_path or DEFAULT_INPUT_PATH),
        sheet_name=sheet_name,
        output_root=Path(output_root or DEFAULT_OUTPUT_ROOT),
    )


def load_listeria_input(input_path: str | Path, sheet_name: str = DEFAULT_INPUT_SHEET) -> pd.DataFrame:
    path = Path(input_path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, sheet_name=sheet_name)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported input format: {path}")

    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        if col in CATEGORICAL_COLUMNS:
            df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
        else:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False).str.strip(),
                errors="coerce",
            )
    return df


def annotate_listeria_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timepoint"] = out["Sample Type"].map(TIMEPOINT_MAP)
    if out["timepoint"].isna().any():
        unknown = out.loc[out["timepoint"].isna(), "Sample Type"].dropna().unique().tolist()
        raise ValueError(f"Unknown Sample Type values: {unknown}")

    out["timepoint"] = pd.Categorical(out["timepoint"], TIMEPOINT_ORDER, ordered=True)
    out["timepoint_display"] = out["timepoint"].astype(str).replace(
        {"24h (1)": "24h", "24h (2)": "24h"}
    )
    out["timepoint_display"] = pd.Categorical(
        out["timepoint_display"], TIMEPOINT_DISPLAY_ORDER, ordered=True
    )
    out["is_quasimeta"] = out["Sample Type"] != "metagenomics"
    out["included_in_analysis"] = ~out["Treatment"].isin(["Blank", "Background"])
    out["Swab Type"] = pd.Categorical(out["Swab Type"], SWAB_ORDER, ordered=True)
    out["Condition"] = pd.Categorical(out["Condition"], CONDITION_ORDER, ordered=True)
    return out


def load_listeria_data(
    input_path: str | Path,
    sheet_name: str = DEFAULT_INPUT_SHEET,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows = annotate_listeria_df(load_listeria_input(input_path, sheet_name))
    valid_swab_mask = all_rows["Swab Type"].astype(str).isin(SWAB_ORDER)
    analysis_rows = all_rows[all_rows["included_in_analysis"] & valid_swab_mask].copy()
    return all_rows, analysis_rows


def format_input_label(input_path: str | Path, sheet_name: str = DEFAULT_INPUT_SHEET) -> str:
    path = Path(input_path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return f"{path} (sheet `{sheet_name}`)"
    return str(path)


def describe_filtering(all_rows: pd.DataFrame, analysis_rows: pd.DataFrame) -> str:
    excluded = len(all_rows) - len(analysis_rows)
    return (
        f"Loaded {len(all_rows)} rows in total; retained {len(analysis_rows)} rows for analysis "
        f"after excluding {excluded} Blank/Background rows."
    )


def finite_median(values: pd.Series | np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return np.nan
    return float(np.median(arr))
