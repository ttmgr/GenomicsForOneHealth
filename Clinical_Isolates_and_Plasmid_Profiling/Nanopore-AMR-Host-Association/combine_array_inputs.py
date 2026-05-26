#!/usr/bin/env python3
"""Combine per-sample array-run tool outputs into namespaced inputs for the analyzer.

The 17-sample array run (9 wastewater G/R/S{1-3} + 8 rectal-swab RS{1-8}) produces
per-sample ABRicate / IntegronFinder / MOB-suite / ISEScan outputs over FULL metagenome
assemblies (~210-250k contigs each). Each assembly was numbered independently, so contig
IDs (``ctgN``) collide across samples. ``analyze_plasmid_results.py`` keys every tool on a
single contig string, so the inputs must be made globally unique before integration.

This script reads whatever tools are present under ``array_downloads/`` and writes
namespaced inputs into ``array_run/`` in exactly the shapes the analyzer's discovery
expects. Every contig ID is rewritten to ``{SAMPLE}__{contig}``.

Anchoring: ABRicate hits and *real* integrons (IntegronFinder rows with CALIN/complete/In0
> 0) define the contigs of interest. MOB-suite and ISEScan report a row for essentially
every contig, so they are filtered to *annotate the anchor set only* — they never expand
it. This keeps the integrated table at hundreds of contigs, not ~250k. (Scope choice: pure
MOB-replicon contigs without an ABRicate/PlasmidFinder hit are not anchored; adjust here if
that is desired.)

Expected ``array_downloads/`` layout::

    abricate/        {SAMPLE}_{card,vfdb,plasmidfinder}.tsv   (per-sample _summary_ files ignored)
    integronfinder/  .../{SAMPLE}.summary, .../{SAMPLE}.integrons   (any depth)
    mobsuite/        {SAMPLE}_mob_typer.tsv, {SAMPLE}_mob_mge_report.tsv
    isescan/         .../{SAMPLE}.fasta.tsv                          (any depth)

Contig lengths are pulled from the local assemblies (array_downloads/fasta/ or the
wastewater_polished_nanomdbg/ and rectalswab_nanomotif_fasta/ source dirs) — only the
anchor contigs are extracted, so the large assemblies are streamed, not copied.

Idempotent: regenerates the managed ``array_run/`` inputs from whatever is present, so
re-run it each time a new tool's results are downloaded.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parent
DL = Path(os.environ.get("INTEGRATED_DL_DIR", str(ROOT / "array_downloads")))
RUN = Path(os.environ.get("INTEGRATED_RUN_DIR", str(ROOT / "array_run")))

# Per-tool source dirs — each one can be overridden independently so a cluster
# run can point straight at the canonical *_results dirs without symlinks.
ABRICATE_DIR       = Path(os.environ.get("ABRICATE_DIR",       str(DL / "abricate")))
INTEGRONFINDER_DIR = Path(os.environ.get("INTEGRONFINDER_DIR", str(DL / "integronfinder")))
MOBSUITE_DIR       = Path(os.environ.get("MOBSUITE_DIR",       str(DL / "mobsuite")))
ISESCAN_DIR        = Path(os.environ.get("ISESCAN_DIR",        str(DL / "isescan")))

# Where the per-sample assemblies live (for contig-length extraction only).
# Override with FASTA_DIRS=path1:path2:... — colon-separated like $PATH.
FASTA_DIRS = [
    Path(p) for p in os.environ.get(
        "FASTA_DIRS",
        f"{DL / 'fasta'}:{ROOT / 'wastewater_polished_nanomdbg'}:{ROOT / 'rectalswab_nanomotif_fasta'}",
    ).split(":") if p
]

# 12-column long format produced by test.sh and read by analyze_plasmid_results.py.
COMBINED_HEADER = [
    "DB", "FILE", "CONTIG", "START", "END", "STRAND",
    "GENE", "PCT_COV", "PCT_ID", "GAPS", "PRODUCT", "RESISTANCE",
]


def ns(sample: str, contig: str) -> str:
    """Namespace a contig id as ``{sample}__{first-token}``."""
    return f"{sample}__{contig.strip().split()[0]}" if contig.strip() else ""


def read_table(path: Path) -> tuple[list[str], list[str], list[list[str]]]:
    """Read a TSV, returning (leading comment lines, header cells, data rows).

    Mirrors the header detection in ``analyze_plasmid_results.read_tsv_rows``: a header
    is the first non-comment line, or a ``#``-prefixed line that contains tabs (ABRicate).
    Leading ``#`` lines without tabs (IntegronFinder version/cmdline) are returned as comments.
    """
    comments: list[str] = []
    header: list[str] | None = None
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if header is None:
                if not line.strip():
                    comments.append(line)
                    continue
                if line.startswith("#"):
                    body = line[1:]
                    if "\t" in body:
                        header = [c.strip().lstrip("#") for c in body.split("\t")]
                    else:
                        comments.append(line)
                    continue
                header = [c.strip() for c in line.split("\t")]
                continue
            if line.strip():
                rows.append(line.split("\t"))
    return comments, (header or []), rows


def col_index(header: Iterable[str], *names: str) -> int | None:
    """Return the index of the first matching column name (case-insensitive)."""
    lower = [h.strip().lstrip("#").lower() for h in header]
    for name in names:
        if name.lower() in lower:
            return lower.index(name.lower())
    return None


def get(header: list[str], row: list[str], *names: str) -> str:
    idx = col_index(header, *names)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def reset_run_inputs() -> None:
    """Remove the input artifacts this script manages (not the analyzer's outputs)."""
    RUN.mkdir(parents=True, exist_ok=True)
    for name in ("combined_abricate_hits.tsv", "contigs.fasta"):
        (RUN / name).unlink(missing_ok=True)
    for sub in ("integronfinder_results", "isescan_results", "mobsuite_results"):
        shutil.rmtree(RUN / sub, ignore_errors=True)


# --------------------------------------------------------------------------- ABRicate

def combine_abricate(anchors: set[str]) -> int:
    src = ABRICATE_DIR
    files = sorted(src.glob("*.tsv")) if src.is_dir() else []
    pattern = re.compile(r"^(?P<sample>.+)_(?P<db>card|vfdb|plasmidfinder)\.tsv$")
    out_lines = ["\t".join(COMBINED_HEADER)]
    n_rows = 0
    samples: set[str] = set()
    # Names matched by the regex that are actually cross-sample aggregators,
    # not per-sample outputs — e.g. legacy `abricate_card.tsv` / `combined_*.tsv`
    # left over from earlier mock runs at the top of the cluster dir.
    AGGREGATE_SAMPLE_NAMES = {"abricate", "summary", "combined", "all"}
    for path in files:
        if "_summary_" in path.name:
            continue  # per-sample ABRicate summary tables are not hit tables
        match = pattern.match(path.name)
        if not match:
            continue
        sample, db = match.group("sample"), match.group("db")
        if sample.lower() in AGGREGATE_SAMPLE_NAMES:
            continue  # aggregator file masquerading as a sample
        samples.add(sample)
        _, header, rows = read_table(path)
        for row in rows:
            seq = get(header, row, "SEQUENCE", "sequence")
            gene = get(header, row, "GENE", "gene")
            if not seq or not gene:
                continue
            contig = ns(sample, seq)
            anchors.add(contig)
            out_lines.append("\t".join([
                db, sample, contig,
                get(header, row, "START", "start"),
                get(header, row, "END", "end"),
                get(header, row, "STRAND", "strand"),
                gene,
                get(header, row, "%COVERAGE", "PCT_COV", "coverage"),
                get(header, row, "%IDENTITY", "PCT_ID", "identity"),
                get(header, row, "GAPS", "gaps"),
                get(header, row, "PRODUCT", "product"),
                get(header, row, "RESISTANCE", "resistance"),
            ]))
            n_rows += 1
    if n_rows:
        (RUN / "combined_abricate_hits.tsv").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"  ABRicate     : {len(samples):>2} samples, {n_rows} hits"
          + ("" if n_rows else "  (none found)"))
    return n_rows


# ----------------------------------------------------------------------- IntegronFinder

def _has_integron_evidence(header: list[str], row: list[str]) -> bool:
    """True if a .summary row reports any integron structure (CALIN/complete/In0 > 0)."""
    for col in ("CALIN", "complete", "In0"):
        idx = col_index(header, col)
        if idx is not None and idx < len(row):
            try:
                if int(float(row[idx].strip() or 0)) > 0:
                    return True
            except ValueError:
                continue
    return False


def stage_integron(anchors: set[str]) -> int:
    src = INTEGRONFINDER_DIR
    if not src.is_dir():
        print("  IntegronFinder: (none found)")
        return 0
    n_files = 0
    samples: set[str] = set()
    kept_total = 0
    for path in sorted(list(src.rglob("*.summary")) + list(src.rglob("*.integrons"))):
        # On full metagenomes IntegronFinder leaves ~225k per-contig scratch
        # .integrons files per sample alongside the one real {SAMPLE}.summary /
        # {SAMPLE}.integrons aggregate. The aggregate's stem equals the
        # top-level sample directory name; scratch files (ctgN.integrons) do
        # not. Skip non-aggregates without opening them.
        rel_parts = path.relative_to(src).parts
        sample_dir = rel_parts[0] if len(rel_parts) > 1 else ""
        if path.stem != sample_dir:
            continue
        sample = path.stem  # {SAMPLE}.summary / {SAMPLE}.integrons
        samples.add(sample)
        comments, header, rows = read_table(path)
        idx = col_index(header, "ID_replicon", "id_replicon")
        if idx is None:
            print(f"    warning: no ID_replicon column in {path.name}, skipped", file=sys.stderr)
            continue
        is_summary = path.name.endswith(".summary")
        kept: list[list[str]] = []
        for row in rows:
            # .summary lists every contig; keep only those with a real integron.
            if is_summary and not _has_integron_evidence(header, row):
                continue
            if idx < len(row) and row[idx].strip():
                row[idx] = ns(sample, row[idx])
                anchors.add(row[idx])
            kept.append(row)
        kept_total += len(kept)
        dest_dir = RUN / "integronfinder_results" / sample
        dest_dir.mkdir(parents=True, exist_ok=True)
        lines = list(comments) + ["\t".join(header)] + ["\t".join(r) for r in kept]
        (dest_dir / path.name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        n_files += 1
    print(f"  IntegronFinder: {len(samples):>2} samples, {n_files} files, {kept_total} integron rows kept")
    return n_files


# --------------------------------------------------------------------------- MOB-suite

def _concat_mob(suffix: str, out_name: str, contig_cols: tuple[str, ...], anchors: set[str]) -> tuple[int, int]:
    src = MOBSUITE_DIR
    files = sorted(src.glob(f"*{suffix}")) if src.is_dir() else []
    header: list[str] | None = None
    out_rows: list[str] = []
    kept = 0
    for path in files:
        sample = path.name[: -len(suffix)]
        _, hdr, rows = read_table(path)
        if header is None:
            header = hdr
            out_rows.append("\t".join(header))
        idx = col_index(hdr, *contig_cols)
        for row in rows:
            if idx is None or idx >= len(row) or not row[idx].strip():
                continue
            nsid = ns(sample, row[idx])
            if nsid not in anchors:
                continue  # annotate anchor contigs only; do not expand the set
            row[idx] = nsid
            out_rows.append("\t".join(row))
            kept += 1
    if header is not None:
        dest = RUN / "mobsuite_results"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / out_name).write_text("\n".join(out_rows) + "\n", encoding="utf-8")
    return len(files), kept


def stage_mob(anchors: set[str]) -> int:
    # Discovery matches these by EXACT filename, so the per-sample files are concatenated.
    n_typer, kept_typer = _concat_mob("_mob_typer.tsv", "mob_typer.tsv", ("sample_id", "contig_id"), anchors)
    _concat_mob("_mob_mge_report.tsv", "mob_mge_report.tsv", ("contig_id", "sample_id"), anchors)
    print(f"  MOB-suite    : {n_typer:>2} samples, {kept_typer} anchor rows kept"
          + ("" if n_typer else "  (none found)"))
    return n_typer


# ----------------------------------------------------------------------------- ISEScan

def stage_isescan(anchors: set[str]) -> int:
    src = ISESCAN_DIR
    if not src.is_dir():
        print("  ISEScan      : (none found)")
        return 0
    n_files = 0
    samples: set[str] = set()
    kept_total = 0
    for path in sorted(src.rglob("*.tsv")):
        if any(part.lower() in {"proteome", "hmm", "tmp", "temp"} for part in path.relative_to(src).parts):
            continue  # ISEScan working dirs, not final call tables
        match = re.match(r"^(?P<sample>.+?)\.fasta\.tsv$", path.name)
        sample = match.group("sample") if match else (
            path.parent.name if path.parent.name != "isescan" else path.stem)
        samples.add(sample)
        _, header, rows = read_table(path)
        idx = col_index(header, "seqID", "seqid", "seq_id")
        if idx is None:
            print(f"    warning: no seqID column in {path.name}, skipped", file=sys.stderr)
            continue
        kept: list[list[str]] = []
        for row in rows:
            if idx >= len(row) or not row[idx].strip():
                continue
            nsid = ns(sample, row[idx])
            if nsid not in anchors:
                continue  # IS context on anchor contigs only
            row[idx] = nsid
            kept.append(row)
        if not kept:
            continue
        kept_total += len(kept)
        dest_dir = RUN / "isescan_results" / sample
        dest_dir.mkdir(parents=True, exist_ok=True)
        lines = ["\t".join(header)] + ["\t".join(r) for r in kept]
        (dest_dir / path.name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        n_files += 1
    print(f"  ISEScan      : {len(samples):>2} samples, {kept_total} IS rows on anchor contigs")
    return n_files


# ------------------------------------------------------------------------------- FASTA

def iter_fasta(path: Path) -> Iterator[tuple[str, list[str]]]:
    """Yield (first-token-of-header, list-of-record-lines) for each FASTA record."""
    header: str | None = None
    buf: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, buf
                header = line[1:].split()[0] if line[1:].strip() else ""
                buf = []
            elif header is not None:
                buf.append(line)
    if header is not None:
        yield header, buf


def build_contigs_fasta(anchors: set[str]) -> int:
    """Write only the anchor contigs (namespaced headers) for contig lengths.

    Streams the large local assemblies and emits just the anchor records, so the
    full assemblies are read but never copied. Samples whose FASTA is not present
    locally simply contribute no lengths (filled later from MOB-suite size, etc.).
    """
    if not anchors:
        print("  FASTA lengths: (skipped — no anchor contigs yet)")
        return 0
    fastas: dict[str, Path] = {}
    for d in FASTA_DIRS:
        if d.is_dir():
            for path in sorted(d.glob("*.fasta")):
                fastas.setdefault(path.stem, path)  # first dir wins per sample
    if not fastas:
        print("  FASTA lengths: (skipped — no local assemblies found)")
        return 0
    written = 0
    with (RUN / "contigs.fasta").open("w", encoding="utf-8") as fh:
        for sample, path in fastas.items():
            for token, seq_lines in iter_fasta(path):
                contig = ns(sample, token)
                if contig in anchors:
                    fh.write(f">{contig}\n")
                    fh.write("\n".join(seq_lines))
                    fh.write("\n")
                    written += 1
    print(f"  FASTA lengths: {written}/{len(anchors)} anchor contigs found in local assemblies")
    return written


def main() -> int:
    tool_dirs = {
        "ABRicate":       ABRICATE_DIR,
        "IntegronFinder": INTEGRONFINDER_DIR,
        "MOB-suite":      MOBSUITE_DIR,
        "ISEScan":        ISESCAN_DIR,
    }
    present = {name: d for name, d in tool_dirs.items() if d.is_dir()}
    if not present:
        print("error: no per-tool source dirs found. Set ABRICATE_DIR / INTEGRONFINDER_DIR /",
              file=sys.stderr)
        print(f"       MOBSUITE_DIR / ISESCAN_DIR or drop inputs under {DL}/.", file=sys.stderr)
        return 1
    for name, d in tool_dirs.items():
        mark = "✓" if name in present else "·"
        print(f"  {mark} {name:14s} {d}")
    RUN.mkdir(parents=True, exist_ok=True)
    print(f"Writing namespaced inputs to {RUN}")
    reset_run_inputs()
    anchors: set[str] = set()
    combine_abricate(anchors)
    stage_integron(anchors)
    # ABRicate hits + real integrons now define the anchor set; MOB/ISEScan annotate only.
    stage_mob(anchors)
    stage_isescan(anchors)
    build_contigs_fasta(anchors)
    print(f"\nStaged {len(anchors)} anchor contigs (ABRicate + IntegronFinder) into {RUN}")
    print("Next: run the analyzer from the run dir, e.g.")
    print(f"  (cd {RUN.name} && python3 ../analyze_plasmid_results.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
