"""GenomicsForOneHealth tool-specific output parsers.

These parse the tool outputs that appear across this repository's skills and are
specific to its Nanopore/metagenomics tool stack:
  - NanoStat summary text   (Air, Listeria QC)
  - Kraken2 report          (every taxonomic-classification skill)
  - AMRFinderPlus table     (AMR/virulence skills)

Generic, tool-independent parsers (VCF, generic TSV) and the shared numeric
helpers live in the agnostic core (agent_skills/core/hooks/parsers.py); this
module reuses them rather than duplicating.

Every parser returns a dict and is robust to a missing file or malformed lines:
it never raises on bad input, it reports the problem in the result. No pandas;
standard library only.
"""

from __future__ import annotations

import os
from typing import Any

from agent_skills.core.hooks.parsers import _missing, _to_number


def parse_nanostat(path: str) -> dict:
    """Parse a NanoStat summary file into {metric: value} pairs.

    NanoStat writes "Label:   value" lines (values may carry thousands
    separators). Recognized numeric metrics are also exposed, lower-cased and
    underscored, under "metrics".
    """
    if not path or not os.path.isfile(path):
        return _missing(path)
    raw: dict[str, str] = {}
    metrics: dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if not key or not value:
                    continue
                raw[key] = value
                number = _to_number(value.split()[0]) if value.split() else None
                if number is not None:
                    metrics[key.lower().replace(" ", "_")] = number
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc)}
    return {"ok": True, "path": path, "raw": raw, "metrics": metrics}


def parse_kraken2_report(path: str) -> dict:
    """Parse a Kraken2 report (the --report file).

    Columns: percent, clade_fragments, taxon_fragments, rank_code, taxid, name.
    Returns the rows plus a summary with the classified percentage, derived
    from the unclassified ("U") line when present.
    """
    if not path or not os.path.isfile(path):
        return _missing(path)
    rows: list[dict] = []
    unclassified_pct = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 6:
                    continue
                pct = _to_number(fields[0])
                row = {
                    "percent": pct,
                    "clade_fragments": _to_number(fields[1]),
                    "taxon_fragments": _to_number(fields[2]),
                    "rank_code": fields[3].strip(),
                    "taxid": fields[4].strip(),
                    "name": fields[5].strip(),
                }
                rows.append(row)
                if row["rank_code"] == "U" and pct is not None:
                    unclassified_pct = pct
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc)}
    classified_pct = None
    if unclassified_pct is not None:
        classified_pct = round(100.0 - unclassified_pct, 4)
    return {
        "ok": True,
        "path": path,
        "rows": rows,
        "summary": {
            "n_rows": len(rows),
            "unclassified_percent": unclassified_pct,
            "classified_percent": classified_pct,
        },
    }


def parse_amrfinder_table(path: str) -> dict:
    """Parse an AMRFinderPlus output table (TSV).

    Leading comment lines starting with '#' are skipped; the first remaining
    line is treated as the header. Returns records as dicts and, when a gene
    symbol column is present, the list of detected gene symbols.
    """
    if not path or not os.path.isfile(path):
        return _missing(path)
    records: list[dict] = []
    header: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("#"):
                    continue
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if not header:
                    header = [h.strip() for h in fields]
                    continue
                if len(fields) != len(header):
                    # Tolerate ragged rows by zipping to the shorter length.
                    pass
                records.append(dict(zip(header, fields)))
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc)}

    symbol_col = None
    for candidate in ("Gene symbol", "Element symbol", "gene_symbol"):
        if candidate in header:
            symbol_col = candidate
            break
    gene_symbols = []
    if symbol_col:
        gene_symbols = sorted({r.get(symbol_col, "").strip() for r in records if r.get(symbol_col, "").strip()})

    return {
        "ok": True,
        "path": path,
        "header": header,
        "records": records,
        "n_hits": len(records),
        "gene_symbols": gene_symbols,
    }
