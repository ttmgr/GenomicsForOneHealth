"""Project-agnostic parsers for standard, tool-independent output formats.

Covers formats that are not specific to any one project's tool stack:
  - VCF / VCF-like records  (a standard genomics interchange format)
  - generic TSV             (any tab-separated summary table)

Plus the small numeric/missing-file helpers shared by all parsers (including
the project-specific parsers layered on top of this module). Tool-specific
parsers (NanoStat, Kraken2 report, AMRFinderPlus, ...) live in the project
layer, e.g. agent_skills/project/hooks/parsers_genomics.py.

Every parser returns a dict and is robust to a missing file or malformed
lines: it never raises on bad input, it reports the problem in the result.
No third-party dependencies; standard library only.
"""

from __future__ import annotations

import os


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

    The first non-comment, non-empty line is the header. Useful for any
    summary table (seqkit stats output, samtools idxstats, and the like).
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
