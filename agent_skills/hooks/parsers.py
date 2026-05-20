"""Lightweight parsers for documented workflow outputs.

Covers the output formats that appear across the repository's skills:
  - NanoStat summary text   (Air, Listeria QC)
  - Kraken2 report          (every taxonomic-classification skill)
  - AMRFinderPlus table     (AMR/virulence skills)
  - VCF / VCF-like records  (Avian Influenza, From Feather to Fur, Wetland AIV)
  - generic TSV             (seqkit stats, idxstats, summary tables)

Every parser returns a dict and is robust to a missing file or malformed
lines: it never raises on bad input, it reports the problem in the result.
No pandas; standard library only.
"""

from __future__ import annotations

import os
from typing import Any


def _missing(path: str) -> dict:
    return {"ok": False, "path": path, "error": f"File not found: {path}"}


def _to_number(token: str):
    """Best-effort numeric parse; tolerates thousands separators and %."""
    cleaned = token.strip().replace(",", "").rstrip("%")
    try:
        if cleaned.lower() in ("", "nan", "na"):
            return None
        value = float(cleaned)
        return int(value) if value.is_integer() else value
    except ValueError:
        return None


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


def parse_vcf(path: str) -> dict:
    """Parse a (plain-text) VCF into records, skipping header lines.

    Reads the leading '##' meta lines and the '#CHROM' column header, then
    parses data rows into {chrom, pos, id, ref, alt, qual, filter, info}.
    Gzipped VCFs are reported as needing decompression first (no gzip work is
    done here to keep the parser dependency-free and predictable).
    """
    if not path or not os.path.isfile(path):
        return _missing(path)
    if path.lower().endswith(".gz"):
        return {
            "ok": False,
            "path": path,
            "error": "Gzipped VCF: decompress (e.g. bcftools view) before parsing.",
        }
    records: list[dict] = []
    meta: list[str] = []
    columns: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("##"):
                    meta.append(line.rstrip("\n"))
                    continue
                if line.startswith("#CHROM"):
                    columns = line.rstrip("\n").lstrip("#").split("\t")
                    continue
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 8:
                    continue
                records.append(
                    {
                        "chrom": fields[0],
                        "pos": _to_number(fields[1]),
                        "id": fields[2],
                        "ref": fields[3],
                        "alt": fields[4],
                        "qual": fields[5],
                        "filter": fields[6],
                        "info": fields[7],
                    }
                )
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc)}
    return {
        "ok": True,
        "path": path,
        "n_meta_lines": len(meta),
        "columns": columns,
        "records": records,
        "n_variants": len(records),
    }


def parse_generic_tsv(path: str, comment_prefix: str = "#") -> dict:
    """Parse a generic tab-separated table into a list of dicts.

    The first non-comment, non-empty line is the header. Useful for seqkit
    stats output, samtools idxstats, and the various summary tables.
    """
    if not path or not os.path.isfile(path):
        return _missing(path)
    header: list[str] = []
    rows: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if comment_prefix and line.startswith(comment_prefix):
                    continue
                if not line.strip():
                    continue
                fields = line.rstrip("\n").split("\t")
                if not header:
                    header = [h.strip() for h in fields]
                    continue
                rows.append(dict(zip(header, fields)))
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc)}
    return {"ok": True, "path": path, "header": header, "rows": rows, "n_rows": len(rows)}
