#!/usr/bin/env python3
"""Integrate plasmid-derived contig annotations from ABRicate, MOB-suite, and IntegronFinder.

The script discovers result files recursively from the current working directory,
normalizes contig identifiers, and writes both contig-level and feature-level
outputs. ISEScan parsing is optional: if no ISEScan-like files are detected, the
analysis continues and records that IS-element annotation from ISEScan was not
included.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path.cwd()

OUT_CONTIG = ROOT / "final_plasmid_contig_summary.tsv"
OUT_FEATURES = ROOT / "final_plasmid_feature_long_table.tsv"
OUT_HIGH = ROOT / "high_priority_plasmid_contigs.tsv"
OUT_MD = ROOT / "methods_and_results_draft.md"
OUT_LOG = ROOT / "analysis_log.txt"

EMPTY_VALUES = {"", "-", "na", "n/a", "nan", "none", "null", "not_available"}

CONTIG_COLUMNS = [
    "CONTIG",
    "SEQUENCE",
    "sample_id",
    "contig_id",
    "ID_replicon",
    "seqid",
    "seq_id",
    "sequence_id",
]

FEATURE_COLUMNS = [
    "sample",
    "contig",
    "source_tool",
    "source_file",
    "feature_type",
    "database",
    "feature_id",
    "gene_or_feature",
    "product",
    "resistance_or_annotation",
    "start",
    "end",
    "strand",
    "identity",
    "coverage",
    "evalue",
    "notes",
]

CONTIG_COLUMNS_OUT = [
    "sample",
    "contig",
    "contig_length",
    "plasmid_replicons",
    "AMR_genes",
    "high_priority_AMR_genes",
    "virulence_genes",
    "integron_detected",
    "integron_type",
    "integrase_present",
    "attC_count",
    "cassette_array_genes",
    "IS_elements_transposases",
    "MOB_relaxase_type",
    "MOB_mpf_type",
    "MOB_oriT_type",
    "MOB_predicted_mobility",
    "MOB_nearest_neighbor",
    "MOB_host_range",
    "priority_level",
    "priority_reason",
]


def norm_header(value: str) -> str:
    """Normalize a column name for tolerant matching."""
    value = value.strip().lstrip("#").lower()
    value = value.replace("%", "pct")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in EMPTY_VALUES:
        return ""
    return text


def display(value: Any, default: str = "not_available") -> str:
    text = clean(value)
    return text if text else default


def safe_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = "; ".join(str(v) for v in value)
    text = str(value)
    text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_contig(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.lstrip(">")
    text = text.split()[0]
    if "|" in text and text.count("|") >= 2:
        # Keep common ABRicate/FASTA IDs unchanged, but handle path-like tokens.
        text = text.split("|")[-1] or text
    if "/" in text or "\\" in text:
        text = Path(text).name
    return text


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def add_unique(target: list[str], value: Any) -> None:
    text = clean(value)
    if text and text not in target:
        target.append(text)


def split_multi(value: Any) -> list[str]:
    text = clean(value)
    if not text:
        return []
    parts = re.split(r"\s*[,;]\s*", text)
    return [part for part in parts if clean(part)]


def parse_int(value: Any, default: int = 0) -> int:
    text = clean(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def get_value(row: dict[str, Any], candidates: Iterable[str]) -> str:
    by_norm = {norm_header(k): k for k in row.keys()}
    for candidate in candidates:
        key = norm_header(candidate)
        if key in by_norm:
            return clean(row.get(by_norm[key]))
    return ""


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_tsv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read TSV rows while skipping comment lines before the real header.

    ABRicate may write a header beginning with "#FILE". IntegronFinder writes
    metadata comment lines, then an uncommented tabular header.
    """
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith("#"):
                candidate = line[1:]
                if "\t" in candidate:
                    header = [cell.strip().lstrip("#") for cell in candidate.split("\t")]
                    break
                continue
            header = [cell.strip().lstrip("#") for cell in line.split("\t")]
            break

        if header is None:
            return [], []

        for raw in handle:
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < len(header):
                parts.extend([""] * (len(header) - len(parts)))
            elif len(parts) > len(header):
                parts = parts[: len(header) - 1] + [" ".join(parts[len(header) - 1 :])]
            rows.append({header[i]: parts[i] for i in range(len(header))})

    return header, rows


def first_header(path: Path) -> list[str]:
    header, _ = read_tsv_rows(path)
    return header


def discover_files(root: Path) -> dict[str, list[Path]]:
    files = [p for p in root.rglob("*") if p.is_file()]
    discovered: dict[str, list[Path]] = defaultdict(list)

    for path in files:
        lower_path = str(path).lower()
        name = path.name.lower()

        if name in {
            OUT_CONTIG.name.lower(),
            OUT_FEATURES.name.lower(),
            OUT_HIGH.name.lower(),
            OUT_MD.name.lower(),
            OUT_LOG.name.lower(),
        }:
            continue
        if name == Path(__file__).name.lower():
            continue

        if "isescan" in lower_path or "ise_scan" in lower_path:
            relative_parts = path.relative_to(root).parts
            # ISEScan creates proteome/ and hmm/ working files before final IS
            # calls are written. Those intermediates are explicitly not treated
            # as results.
            if any(part.lower() in {"proteome", "hmm", "tmp", "temp"} for part in relative_parts):
                discovered["isescan_intermediate"].append(path)
                continue
            if path.suffix.lower() in {".tsv", ".gff", ".gff3", ".sum", ".raw", ".txt"}:
                discovered["isescan"].append(path)
            continue

        if path.suffix.lower() in {".fasta", ".fa", ".fna"}:
            discovered["fasta"].append(path)
            continue

        if name.startswith("summary_") and path.suffix.lower() == ".tsv":
            discovered["abricate_summary"].append(path)
            continue

        if name == "mob_typer.tsv":
            discovered["mob_typer"].append(path)
            continue

        if name == "mob_mge_report.tsv":
            discovered["mob_mge"].append(path)
            continue

        if name.endswith(".summary") and "integron" in lower_path:
            discovered["integron_summary"].append(path)
            continue

        if name.endswith(".integrons") and "integron" in lower_path:
            discovered["integron_integrons"].append(path)
            continue

        if "integron" in lower_path and name.endswith(".out"):
            discovered["integron_log"].append(path)
            continue

        if path.suffix.lower() == ".tsv":
            header = {norm_header(h) for h in first_header(path)}
            is_full_abricate = (
                "gene" in header
                and {"start", "end"} <= header
                and ({"contig", "sequence"} & header)
                and ({"db", "database"} & header or "coverage" in header or "pctcoverage" in header)
            )
            if name == "combined_abricate_hits.tsv":
                discovered["abricate_combined"].append(path)
            elif is_full_abricate:
                discovered["abricate_full"].append(path)

    for key in discovered:
        discovered[key] = sorted(discovered[key], key=lambda p: relpath(p))
    return dict(discovered)


def isescan_process_running() -> bool:
    """Detect an active local ISEScan run so intermediate files are not parsed."""
    def has_intermediates_without_final_outputs() -> bool:
        isescan_dir = ROOT / "isescan_results"
        if not isescan_dir.exists():
            return False
        final_suffixes = {".tsv", ".gff", ".gff3", ".sum", ".raw", ".txt"}
        final_outputs = [
            path
            for path in isescan_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in final_suffixes
            and not any(part.lower() in {"proteome", "hmm", "tmp", "temp"} for part in path.relative_to(isescan_dir).parts)
        ]
        intermediate_outputs = [
            path
            for path in isescan_dir.rglob("*")
            if path.is_file()
            and any(part.lower() in {"proteome", "hmm"} for part in path.relative_to(isescan_dir).parts)
        ]
        return bool(intermediate_outputs and not final_outputs)

    try:
        completed = subprocess.run(
            ["ps", "-axo", "command"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return has_intermediates_without_final_outputs()
    text = completed.stdout.lower()
    return (
        "isescan.py" in text
        or ("phmmer" in text and "isescan_results" in text)
        or ("isescan" in text and "mock.fasta" in text and "python" in text)
        or has_intermediates_without_final_outputs()
    )


def parse_fasta_lengths(paths: list[Path]) -> dict[str, int]:
    lengths: dict[str, int] = {}
    for path in paths:
        current = ""
        total = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(">"):
                    if current:
                        lengths[current] = total
                    current = normalize_contig(line)
                    total = 0
                else:
                    total += len(line)
            if current:
                lengths[current] = total
    return lengths


def infer_abricate_db(path: Path, row: dict[str, str]) -> str:
    db = get_value(row, ["DB", "DATABASE"])
    if db:
        return db.lower()
    lower = path.name.lower()
    for candidate in ["card", "arg-annot", "argannot", "vfdb", "plasmidfinder", "resfinder"]:
        if candidate in lower:
            return candidate
    return "abricate"


def abricate_feature_type(db: str) -> str:
    db_lower = db.lower()
    if "plasmidfinder" in db_lower:
        return "plasmid_replicon"
    if "vfdb" in db_lower:
        return "virulence_gene"
    if any(token in db_lower for token in ["card", "arg", "resfinder", "ncbi"]):
        return "AMR_gene"
    return "abricate_hit"


def compact_gene_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def is_generic_low_specificity_amr(gene: str) -> bool:
    key = compact_gene_key(gene)
    generic_prefixes = (
        "acr",
        "emr",
        "mdt",
        "mar",
        "crp",
        "hns",
        "arn",
        "baca",
        "cpx",
        "ept",
        "evg",
        "gad",
        "kdpe",
        "leuo",
        "msba",
        "ompa",
        "omp",
        "pmr",
        "tolc",
        "yoji",
        "ugd",
        "lptd",
        "klebsiellapneumoniaekpn",
        "escherichiacoliacr",
        "escherichicolimdf",
    )
    return key.startswith(generic_prefixes)


def is_high_priority_amr_gene(gene: str, resistance: str = "", product: str = "") -> bool:
    # Use the gene name plus resistance class for this rule. Product text often
    # contains broad words such as "tetracycline", "aminoglycoside", or
    # "antimicrobial" in explanatory descriptions and can otherwise promote
    # generic regulators into the high-priority list.
    del product
    text = " ".join([gene, resistance]).lower()
    compact = compact_gene_key(gene)
    patterns = [
        r"ndm",
        r"kpc",
        r"oxa[-_ ]?48",
        r"vim",
        r"\bimp\b",
        r"ctx[-_ ]?m",
        r"cmy",
        r"\barm[a-z0-9]*\b",
        r"\baac",
        r"\baph",
        r"\bant",
        r"aada",
        r"\bqnr",
        r"oqx",
        r"\bsul[0-9]*\b",
        r"\bdfra?[0-9]*\b",
        r"\btet[\(\-_a-z0-9]*",
        r"\bmph[a-z0-9]*\b",
        r"\bmsr[a-z0-9]*\b",
        r"qacedelta1",
        r"\bcat[a-z0-9]*\b",
        r"\barr[-_0-9a-z]*\b",
    ]
    if compact == "qacedelta1":
        return True
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def is_carbapenemase_or_major_esbl(gene: str) -> bool:
    text = gene.lower()
    patterns = [
        r"ndm",
        r"kpc",
        r"oxa[-_ ]?48",
        r"vim",
        r"\bimp\b",
        r"ctx[-_ ]?m",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def parse_abricate(
    discovered: dict[str, list[Path]],
    feature_rows: list[dict[str, str]],
) -> tuple[dict[str, dict[str, list[str]]], list[Path], list[Path]]:
    combined = discovered.get("abricate_combined", [])
    full = discovered.get("abricate_full", [])
    use_files = combined or full
    skipped = full if combined else []
    by_contig: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {
            "amr_genes": [],
            "specific_amr_genes": [],
            "high_priority_amr_genes": [],
            "major_amr_genes": [],
            "virulence_genes": [],
            "replicons": [],
        }
    )

    seen: set[tuple[str, str, str, str, str, str]] = set()
    for path in use_files:
        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, CONTIG_COLUMNS))
            gene = get_value(row, ["GENE", "gene", "locus", "feature"])
            if not contig or not gene:
                continue
            db = infer_abricate_db(path, row)
            start = get_value(row, ["START", "start"])
            end = get_value(row, ["END", "end"])
            strand = get_value(row, ["STRAND", "strand"])
            key = (db, contig, start, end, strand, gene)
            if key in seen:
                continue
            seen.add(key)

            feature_type = abricate_feature_type(db)
            product = get_value(row, ["PRODUCT", "product"])
            resistance = get_value(row, ["RESISTANCE", "resistance"])
            pct_id = get_value(row, ["PCT_ID", "%IDENTITY", "percent_identity", "identity"])
            pct_cov = get_value(row, ["PCT_COV", "%COVERAGE", "percent_coverage", "coverage"])
            gaps = get_value(row, ["GAPS", "gaps"])

            feature_rows.append(
                {
                    "contig": contig,
                    "source_tool": "ABRicate",
                    "source_file": relpath(path),
                    "feature_type": feature_type,
                    "database": db,
                    "feature_id": get_value(row, ["ACCESSION", "accession"]),
                    "gene_or_feature": gene,
                    "product": product,
                    "resistance_or_annotation": resistance,
                    "start": start,
                    "end": end,
                    "strand": strand,
                    "identity": pct_id,
                    "coverage": pct_cov,
                    "evalue": "",
                    "notes": f"gaps={gaps}" if gaps else "",
                }
            )

            data = by_contig[contig]
            if feature_type == "AMR_gene":
                add_unique(data["amr_genes"], gene)
                if not is_generic_low_specificity_amr(gene):
                    add_unique(data["specific_amr_genes"], gene)
                if not is_generic_low_specificity_amr(gene) and is_high_priority_amr_gene(gene, resistance, product):
                    add_unique(data["high_priority_amr_genes"], gene)
                if is_carbapenemase_or_major_esbl(gene):
                    add_unique(data["major_amr_genes"], gene)
            elif feature_type == "virulence_gene":
                add_unique(data["virulence_genes"], gene)
            elif feature_type == "plasmid_replicon":
                add_unique(data["replicons"], gene)

    return by_contig, use_files, skipped


def parse_mob_typer(
    paths: list[Path],
    feature_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    by_contig: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "length": "",
            "replicons": [],
            "relaxase": [],
            "mpf": [],
            "orit": [],
            "predicted_mobility": "",
            "nearest_neighbor": "",
            "host_range": "",
            "mobility_evidence": False,
            "plasmid_evidence": False,
        }
    )

    for path in paths:
        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, ["sample_id", "contig_id", "ID_replicon"]))
            if not contig:
                continue
            data = by_contig[contig]
            length = get_value(row, ["size", "length", "contig_length"])
            if length:
                data["length"] = length

            for value in split_multi(get_value(row, ["rep_type(s)", "rep_type", "replicon_type"])):
                add_unique(data["replicons"], value)
            for value in split_multi(get_value(row, ["relaxase_type(s)", "relaxase_type"])):
                add_unique(data["relaxase"], value)
            for value in split_multi(get_value(row, ["mpf_type", "mpf_type(s)"])):
                add_unique(data["mpf"], value)
            for value in split_multi(get_value(row, ["orit_type(s)", "oriT_type(s)", "orit_type"])):
                add_unique(data["orit"], value)

            mobility = get_value(row, ["predicted_mobility"])
            if mobility:
                data["predicted_mobility"] = mobility

            nearest_accession = get_value(row, ["mash_nearest_neighbor"])
            nearest_ident = get_value(row, ["mash_neighbor_identification"])
            nearest_distance = get_value(row, ["mash_neighbor_distance"])
            nearest_parts = []
            if nearest_ident:
                nearest_parts.append(nearest_ident)
            if nearest_accession:
                nearest_parts.append(nearest_accession)
            if nearest_distance:
                nearest_parts.append(f"distance={nearest_distance}")
            if nearest_parts:
                data["nearest_neighbor"] = " | ".join(nearest_parts)

            host_parts = []
            for label, rank_col, name_col in [
                (
                    "predicted",
                    "predicted_host_range_overall_rank",
                    "predicted_host_range_overall_name",
                ),
                ("observed", "observed_host_range_ncbi_rank", "observed_host_range_ncbi_name"),
                ("reported", "reported_host_range_lit_rank", "reported_host_range_lit_name"),
            ]:
                rank = get_value(row, [rank_col])
                name = get_value(row, [name_col])
                if name:
                    host_parts.append(f"{label}: {rank} {name}".strip())
            if host_parts:
                data["host_range"] = "; ".join(host_parts)

            has_mobility = bool(
                data["relaxase"]
                or data["mpf"]
                or data["orit"]
                or (mobility and mobility.lower() not in {"non-mobilizable", "non mobilizable"})
            )
            has_replicon = bool(data["replicons"])
            data["mobility_evidence"] = data["mobility_evidence"] or has_mobility
            data["plasmid_evidence"] = data["plasmid_evidence"] or has_replicon or has_mobility

            feature_rows.append(
                {
                    "contig": contig,
                    "source_tool": "MOB-suite mob_typer",
                    "source_file": relpath(path),
                    "feature_type": "mob_typer_record",
                    "database": "MOB-suite",
                    "feature_id": get_value(row, ["primary_cluster_id"]),
                    "gene_or_feature": display(mobility, "mob_typer"),
                    "product": nearest_ident,
                    "resistance_or_annotation": "; ".join(
                        item
                        for item in [
                            f"replicons={','.join(data['replicons'])}" if data["replicons"] else "",
                            f"relaxase={','.join(data['relaxase'])}" if data["relaxase"] else "",
                            f"mpf={','.join(data['mpf'])}" if data["mpf"] else "",
                            f"oriT={','.join(data['orit'])}" if data["orit"] else "",
                        ]
                        if item
                    ),
                    "start": "",
                    "end": "",
                    "strand": "",
                    "identity": "",
                    "coverage": "",
                    "evalue": "",
                    "notes": data["nearest_neighbor"],
                }
            )

    return by_contig


def is_is_or_transposase(mge_type: str, mge_subtype: str, note: str = "") -> bool:
    text = " ".join([mge_type, mge_subtype, note]).lower()
    return bool(
        mge_type.startswith("IS")
        or mge_subtype.startswith("IS")
        or mge_type.startswith("Tn")
        or mge_subtype.startswith("Tn")
        or "transpos" in text
        or "insertion sequence" in text
    )


def parse_mob_mge(
    paths: list[Path],
    feature_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    by_contig: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"is_elements": [], "mobile_element_evidence": False}
    )

    for path in paths:
        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, ["contig_id", "sample_id", "ID_replicon"]))
            if not contig:
                continue
            mge_type = get_value(row, ["mge_type"])
            mge_subtype = get_value(row, ["mge_subtype"])
            mge_id = get_value(row, ["mge_id"])
            mge_acs = get_value(row, ["mge_acs"])
            label = mge_type or mge_subtype or mge_id or "MGE"
            start = get_value(row, ["contig_start", "start"])
            end = get_value(row, ["contig_end", "end"])
            identity = get_value(row, ["pident", "identity"])
            coverage = get_value(row, ["qcovhsp", "coverage"])
            strand = get_value(row, ["sstrand", "strand"])

            is_element = is_is_or_transposase(mge_type, mge_subtype)
            if is_element:
                detail = label
                if mge_subtype and mge_subtype != label:
                    detail = f"{detail}({mge_subtype})"
                add_unique(by_contig[contig]["is_elements"], detail)
                by_contig[contig]["mobile_element_evidence"] = True
            elif clean(label) and label.lower() not in {"16s-rrna", "rrna", "trna"}:
                by_contig[contig]["mobile_element_evidence"] = True

            feature_rows.append(
                {
                    "contig": contig,
                    "source_tool": "MOB-suite MGE report",
                    "source_file": relpath(path),
                    "feature_type": "mobile_element" if not is_element else "IS_or_transposase",
                    "database": "MOB-suite MGE",
                    "feature_id": mge_acs or mge_id,
                    "gene_or_feature": label,
                    "product": mge_subtype,
                    "resistance_or_annotation": get_value(row, ["molecule_type"]),
                    "start": start,
                    "end": end,
                    "strand": strand,
                    "identity": identity,
                    "coverage": coverage,
                    "evalue": get_value(row, ["evalue"]),
                    "notes": f"bitscore={get_value(row, ['bitscore'])}" if get_value(row, ["bitscore"]) else "",
                }
            )

    return by_contig


def parse_integronfinder(
    summary_paths: list[Path],
    integron_paths: list[Path],
    feature_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    by_contig: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "calin": 0,
            "complete": 0,
            "in0": 0,
            "topology": "",
            "size": "",
            "types": [],
            "integrase_present": False,
            "attc_count": 0,
            "cassette_by_integron": defaultdict(list),
            "feature_rows_seen": 0,
        }
    )

    for path in summary_paths:
        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, ["ID_replicon", "contig", "sequence"]))
            if not contig:
                continue
            data = by_contig[contig]
            data["calin"] += parse_int(get_value(row, ["CALIN"]))
            data["complete"] += parse_int(get_value(row, ["complete"]))
            data["in0"] += parse_int(get_value(row, ["In0", "in0"]))
            topology = get_value(row, ["topology"])
            size = get_value(row, ["size"])
            if topology:
                data["topology"] = topology
            if size:
                data["size"] = size

    for path in integron_paths:
        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, ["ID_replicon", "contig", "sequence"]))
            if not contig:
                continue
            data = by_contig[contig]
            data["feature_rows_seen"] += 1

            integron_id = get_value(row, ["ID_integron"]) or "integron"
            element = get_value(row, ["element"])
            start = get_value(row, ["pos_beg", "start"])
            end = get_value(row, ["pos_end", "end"])
            strand = get_value(row, ["strand"])
            evalue = get_value(row, ["evalue"])
            type_elt = get_value(row, ["type_elt"])
            annotation = get_value(row, ["annotation"])
            model = get_value(row, ["model"])
            integron_type = get_value(row, ["type"])
            if integron_type in {"complete", "In0", "CALIN"}:
                add_unique(data["types"], integron_type)

            if type_elt == "attC":
                data["attc_count"] += 1
                feature_type = "integron_attC"
            elif annotation == "intI":
                data["integrase_present"] = True
                feature_type = "integron_integrase"
            elif type_elt == "protein" and annotation and annotation not in {"protein", "attC", "intI"}:
                feature_type = "integron_cassette_annotation"
                data["cassette_by_integron"][integron_id].append((parse_int(start), annotation))
            else:
                feature_type = "integron_feature"

            feature_rows.append(
                {
                    "contig": contig,
                    "source_tool": "IntegronFinder",
                    "source_file": relpath(path),
                    "feature_type": feature_type,
                    "database": "IntegronFinder",
                    "feature_id": f"{contig}:{integron_id}:{element}",
                    "gene_or_feature": annotation or type_elt or element,
                    "product": model,
                    "resistance_or_annotation": integron_type,
                    "start": start,
                    "end": end,
                    "strand": strand,
                    "identity": "",
                    "coverage": "",
                    "evalue": evalue,
                    "notes": f"distance_2attC={get_value(row, ['distance_2attC'])}",
                }
            )

    for contig, data in by_contig.items():
        counted_types: list[str] = []
        if data["complete"] > 0:
            add_unique(counted_types, f"complete({data['complete']})")
        if data["in0"] > 0:
            add_unique(counted_types, f"In0({data['in0']})")
        if data["calin"] > 0:
            add_unique(counted_types, f"CALIN({data['calin']})")
        if counted_types:
            data["types"] = counted_types

    return by_contig


def parse_isescan(
    paths: list[Path],
    feature_rows: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    by_contig: dict[str, dict[str, Any]] = defaultdict(lambda: {"is_elements": []})
    call_tables = [path for path in paths if path.suffix.lower() == ".tsv"]
    parse_paths = call_tables or [path for path in paths if path.suffix.lower() in {".gff", ".gff3"}]
    seen_features: set[tuple[str, str, str, str]] = set()

    for path in parse_paths:
        suffix = path.suffix.lower()
        if suffix in {".gff", ".gff3"}:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    if not raw.strip() or raw.startswith("#"):
                        continue
                    parts = raw.rstrip("\n").split("\t")
                    if len(parts) < 9:
                        continue
                    contig = normalize_contig(parts[0])
                    if parts[2] != "insertion_sequence":
                        continue
                    attrs = parts[8]
                    family_match = re.search(r"family=([^;]+)", attrs)
                    cluster_match = re.search(r"cluster=([^;]+)", attrs)
                    id_match = re.search(r"ID=([^;]+)", attrs)
                    family = family_match.group(1) if family_match else ""
                    cluster = cluster_match.group(1) if cluster_match else ""
                    label = family or cluster or (id_match.group(1) if id_match else parts[2])
                    if family and cluster:
                        label = f"{family}({cluster})"
                    key = (contig, parts[3], parts[4], label)
                    if key in seen_features:
                        continue
                    seen_features.add(key)
                    add_unique(by_contig[contig]["is_elements"], label)
                    feature_rows.append(
                        {
                            "contig": contig,
                            "source_tool": "ISEScan",
                            "source_file": relpath(path),
                            "feature_type": "ISEScan_insertion_sequence",
                            "database": "ISEScan",
                            "feature_id": id_match.group(1) if id_match else label,
                            "gene_or_feature": label,
                            "product": family,
                            "resistance_or_annotation": attrs,
                            "start": parts[3],
                            "end": parts[4],
                            "strand": parts[6],
                            "identity": "",
                            "coverage": "",
                            "evalue": "",
                            "notes": "",
                        }
                    )
            continue

        _, rows = read_tsv_rows(path)
        for row in rows:
            contig = normalize_contig(get_value(row, CONTIG_COLUMNS))
            if not contig:
                continue
            family = get_value(row, ["family"])
            cluster = get_value(row, ["cluster"])
            label = family or cluster or get_value(row, ["isName", "IS_name", "Name", "type"]) or "ISEScan_feature"
            if family and cluster:
                label = f"{family}({cluster})"
            start = get_value(row, ["isBegin", "begin", "start"])
            end = get_value(row, ["isEnd", "end", "stop"])
            key = (contig, start, end, label)
            if key in seen_features:
                continue
            seen_features.add(key)
            add_unique(by_contig[contig]["is_elements"], label)
            feature_rows.append(
                {
                    "contig": contig,
                    "source_tool": "ISEScan",
                    "source_file": relpath(path),
                    "feature_type": "ISEScan_insertion_sequence",
                    "database": "ISEScan",
                    "feature_id": label,
                    "gene_or_feature": label,
                    "product": family,
                    "resistance_or_annotation": f"cluster={cluster}; type={get_value(row, ['type'])}",
                    "start": start,
                    "end": end,
                    "strand": get_value(row, ["strand", "orientation"]),
                    "identity": "",
                    "coverage": "",
                    "evalue": "",
                    "notes": f"isLen={get_value(row, ['isLen'])}; ncopy4is={get_value(row, ['ncopy4is'])}",
                }
            )

    return by_contig


def format_list(values: Iterable[str], default: str = "none") -> str:
    clean_values = [clean(v) for v in values if clean(v)]
    return "; ".join(clean_values) if clean_values else default


def format_replicons(abricate_reps: list[str], mob_reps: list[str]) -> str:
    parts = []
    if abricate_reps:
        parts.append("ABRicate=" + ",".join(abricate_reps))
    if mob_reps:
        parts.append("MOB-suite=" + ",".join(mob_reps))
    return "; ".join(parts) if parts else "none"


def format_cassettes(cassette_by_integron: dict[str, list[tuple[int, str]]]) -> str:
    parts = []
    for integron_id in sorted(cassette_by_integron.keys(), key=natural_key):
        genes = [gene for _, gene in sorted(cassette_by_integron[integron_id], key=lambda item: item[0])]
        if genes:
            parts.append(f"{integron_id}:{','.join(genes)}")
    return " | ".join(parts) if parts else "none"


def has_plasmid_evidence(
    abricate_data: dict[str, list[str]],
    mob_data: dict[str, Any],
) -> bool:
    # For priority assignment, "plasmid evidence" is kept conservative and
    # means an ABRicate PlasmidFinder or MOB-suite replicon call. Mobility
    # markers are evaluated separately so mobility-only contigs are not promoted
    # to High without explicit replicon evidence.
    return bool(abricate_data.get("replicons") or mob_data.get("replicons"))


def compute_priority(
    abricate_data: dict[str, list[str]],
    mob_data: dict[str, Any],
    integron_data: dict[str, Any],
    mge_data: dict[str, Any],
) -> tuple[str, str]:
    """Return priority level and reason.

    Explicit rules:
    - High: contig has plasmid evidence plus carbapenemase/major ESBL gene, or
      plasmid evidence plus AMR and virulence genes, or plasmid evidence plus
      mobility/conjugation evidence and AMR.
    - Medium: contig has plasmid evidence plus AMR genes, or AMR genes plus
      integron/mobile-element evidence.
    - Low: contig has only replicon evidence, only low-specificity virulence
      hits, or isolated generic efflux/regulatory genes.
    """
    amr_genes = abricate_data.get("amr_genes", [])
    specific_amr = abricate_data.get("specific_amr_genes", [])
    high_priority_amr = abricate_data.get("high_priority_amr_genes", [])
    major_amr = abricate_data.get("major_amr_genes", [])
    virulence = abricate_data.get("virulence_genes", [])
    plasmid = has_plasmid_evidence(abricate_data, mob_data)
    mobility = bool(mob_data.get("mobility_evidence"))
    integron = bool(
        integron_data.get("feature_rows_seen", 0)
        or integron_data.get("complete", 0)
        or integron_data.get("calin", 0)
        or integron_data.get("in0", 0)
    )
    mobile_element = bool(mge_data.get("mobile_element_evidence") or mge_data.get("is_elements"))

    if plasmid and major_amr:
        return "High", "plasmid evidence plus carbapenemase/major ESBL gene(s): " + ", ".join(major_amr)
    if plasmid and specific_amr and virulence:
        return (
            "High",
            "plasmid evidence plus AMR and VFDB virulence-associated hit(s): "
            + ", ".join(specific_amr[:8]),
        )
    if plasmid and mobility and specific_amr:
        return (
            "High",
            "plasmid evidence plus MOB-suite mobility/conjugation evidence and AMR gene(s): "
            + ", ".join(specific_amr[:8]),
        )
    if plasmid and specific_amr:
        return "Medium", "plasmid evidence plus AMR gene(s): " + ", ".join(specific_amr[:8])
    if (specific_amr or high_priority_amr) and (integron or mobile_element):
        return (
            "Medium",
            "AMR gene(s) plus integron/mobile-element evidence: "
            + ", ".join((specific_amr or high_priority_amr)[:8]),
        )
    if plasmid:
        return "Low", "replicon or MOB-suite plasmid evidence without high-priority AMR context"
    if virulence and not amr_genes:
        return "Low", "VFDB virulence-associated hit(s) only"
    if amr_genes and not specific_amr:
        return "Low", "only generic or low-specificity efflux/regulatory AMR hits detected"
    if amr_genes:
        return "Low", "AMR gene(s) detected without plasmid, integron, or mobility context"
    return "Low", "no priority plasmid AMR pattern detected"


def build_contig_rows(
    contigs: set[str],
    fasta_lengths: dict[str, int],
    abricate: dict[str, dict[str, list[str]]],
    mob: dict[str, dict[str, Any]],
    mge: dict[str, dict[str, Any]],
    integron: dict[str, dict[str, Any]],
    isescan: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for contig in sorted(contigs, key=natural_key):
        ab = abricate.get(contig, defaultdict(list))
        mob_data = mob.get(contig, {})
        mge_data = mge.get(contig, {})
        int_data = integron.get(contig, {})
        ise_data = isescan.get(contig, {})

        int_detected = bool(
            int_data.get("feature_rows_seen", 0)
            or int_data.get("complete", 0)
            or int_data.get("calin", 0)
            or int_data.get("in0", 0)
        )
        integron_types = list(int_data.get("types", []))
        if not integron_types:
            if int_data.get("complete", 0):
                add_unique(integron_types, f"complete({int_data.get('complete')})")
            if int_data.get("in0", 0):
                add_unique(integron_types, f"In0({int_data.get('in0')})")
            if int_data.get("calin", 0):
                add_unique(integron_types, f"CALIN({int_data.get('calin')})")

        is_elements = []
        for value in mge_data.get("is_elements", []):
            add_unique(is_elements, value)
        for value in ise_data.get("is_elements", []):
            add_unique(is_elements, f"ISEScan={value}")

        priority, reason = compute_priority(ab, mob_data, int_data, mge_data)

        length = (
            clean(mob_data.get("length"))
            or clean(int_data.get("size"))
            or (str(fasta_lengths[contig]) if contig in fasta_lengths else "")
        )

        rows.append(
            {
                "contig": contig,
                "contig_length": display(length),
                "plasmid_replicons": format_replicons(ab.get("replicons", []), mob_data.get("replicons", [])),
                "AMR_genes": format_list(ab.get("amr_genes", [])),
                "high_priority_AMR_genes": format_list(ab.get("high_priority_amr_genes", [])),
                "virulence_genes": format_list(ab.get("virulence_genes", [])),
                "integron_detected": "yes" if int_detected else "no",
                "integron_type": format_list(integron_types, default="none"),
                "integrase_present": "yes" if int_data.get("integrase_present") else "no",
                "attC_count": str(int_data.get("attc_count", 0)),
                "cassette_array_genes": format_cassettes(int_data.get("cassette_by_integron", {})),
                "IS_elements_transposases": format_list(is_elements),
                "MOB_relaxase_type": format_list(mob_data.get("relaxase", [])),
                "MOB_mpf_type": format_list(mob_data.get("mpf", [])),
                "MOB_oriT_type": format_list(mob_data.get("orit", [])),
                "MOB_predicted_mobility": display(mob_data.get("predicted_mobility")),
                "MOB_nearest_neighbor": display(mob_data.get("nearest_neighbor")),
                "MOB_host_range": display(mob_data.get("host_range")),
                "priority_level": priority,
                "priority_reason": reason,
            }
        )

    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: safe_cell(row.get(column, "")) for column in columns})


def summarize_counts(contig_rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "contigs": len(contig_rows),
        "amr": sum(row["AMR_genes"] != "none" for row in contig_rows),
        "virulence": sum(row["virulence_genes"] != "none" for row in contig_rows),
        "replicons": sum(row["plasmid_replicons"] != "none" for row in contig_rows),
        "mobility": sum(
            row["MOB_predicted_mobility"] not in {"not_available", "non-mobilizable"}
            or row["MOB_relaxase_type"] != "none"
            or row["MOB_mpf_type"] != "none"
            or row["MOB_oriT_type"] != "none"
            for row in contig_rows
        ),
        "integrons": sum(row["integron_detected"] == "yes" for row in contig_rows),
        "high": sum(row["priority_level"] == "High" for row in contig_rows),
        "medium": sum(row["priority_level"] == "Medium" for row in contig_rows),
        "low": sum(row["priority_level"] == "Low" for row in contig_rows),
    }


def high_priority_rank(row: dict[str, str]) -> tuple[int, int, int, int, int]:
    major_terms = ["NDM", "KPC", "OXA-48", "VIM", "IMP", "CTX-M"]
    text = " ".join([row["AMR_genes"], row["high_priority_AMR_genes"], row["cassette_array_genes"]]).upper()
    major_count = sum(term in text for term in major_terms)
    amr_count = 0 if row["AMR_genes"] == "none" else len(row["AMR_genes"].split("; "))
    has_mobility = int(
        row["MOB_predicted_mobility"] not in {"not_available", "non-mobilizable"}
        or row["MOB_relaxase_type"] != "none"
        or row["MOB_mpf_type"] != "none"
        or row["MOB_oriT_type"] != "none"
    )
    has_integron = int(row["integron_detected"] == "yes")
    has_virulence = int(row["virulence_genes"] != "none")
    return (major_count, amr_count, has_mobility, has_integron, has_virulence)


def top_high_priority(contig_rows: list[dict[str, str]], limit: int = 12) -> list[dict[str, str]]:
    high = [row for row in contig_rows if row["priority_level"] == "High"]
    return sorted(high, key=lambda row: high_priority_rank(row), reverse=True)[:limit]


def find_carbapenemase_candidates(
    contig_rows: list[dict[str, str]],
    plasmid_replicon_only: bool = False,
) -> dict[str, list[str]]:
    terms = ["NDM", "KPC", "OXA-48", "VIM"]
    found: dict[str, list[str]] = defaultdict(list)
    for row in contig_rows:
        if plasmid_replicon_only and row["plasmid_replicons"] == "none":
            continue
        text = " ".join([row["AMR_genes"], row["high_priority_AMR_genes"], row["cassette_array_genes"]])
        for term in terms:
            if re.search(re.escape(term), text, flags=re.IGNORECASE):
                found[term].append(row["contig"])
    return {term: sorted(set(contigs), key=natural_key) for term, contigs in found.items()}


def make_methods_and_results(
    contig_rows: list[dict[str, str]],
    discovered: dict[str, list[Path]],
    isescan_included: bool,
    isescan_active: bool,
) -> str:
    counts = summarize_counts(contig_rows)
    plasmid_carbapenemases = find_carbapenemase_candidates(contig_rows, plasmid_replicon_only=True)
    all_carbapenemases = find_carbapenemase_candidates(contig_rows, plasmid_replicon_only=False)

    if isescan_included:
        methods_isescan = "ISEScan outputs were detected and included to annotate insertion sequences/transposases and IS-family context."
    elif isescan_active:
        methods_isescan = "ISEScan intermediate files were detected, but ISEScan was still running or not finalized; ISEScan-derived IS-element annotation was not included."
    else:
        methods_isescan = "ISEScan result files were not detected, so ISEScan-derived IS-element annotation was not included; mobile-element context was summarized from the MOB-suite MGE report where available."

    methods = (
        "Nanopore-derived plasmid contigs/plasmid FASTA records were screened for antimicrobial resistance genes, "
        "virulence-associated genes, plasmid replicons, integron structures, and plasmid mobility markers. ABRicate "
        "was used with CARD/ARG-ANNOT-like AMR databases, PlasmidFinder, and VFDB to identify AMR genes, plasmid "
        "replicons, and virulence-associated database matches. MOB-suite mob_typer was run with --multi so that each "
        "FASTA record was treated as an independent plasmid-derived sequence; MOB-suite output was used to annotate "
        "replicon type, relaxase type, mate-pair formation type, oriT type, predicted mobility, nearest-neighbor "
        "plasmid information, and host-range fields where available. IntegronFinder was used to identify integron "
        "integrases, attC recombination sites, and integron/cassette structures. "
        f"{methods_isescan} Contig identifiers were used as join keys, and percent identity/coverage fields and "
        "plasmid/mobility fields were retained in the output tables where available."
    )

    if plasmid_carbapenemases:
        carb_text = "; ".join(
            f"{term}: {', '.join(contigs)}" for term, contigs in plasmid_carbapenemases.items()
        )
    else:
        carb_text = "No NDM, KPC, OXA-48, or VIM candidates with replicon-level plasmid evidence were detected."

    additional_carb: dict[str, list[str]] = {}
    for term, contigs in all_carbapenemases.items():
        plasmid_contigs = set(plasmid_carbapenemases.get(term, []))
        additional = [contig for contig in contigs if contig not in plasmid_contigs]
        if additional:
            additional_carb[term] = additional
    if additional_carb:
        additional_carb_text = "; additional carbapenemase matches without replicon-level plasmid evidence were: "
        additional_carb_text += "; ".join(
            f"{term}: {', '.join(contigs)}" for term, contigs in additional_carb.items()
        )
    else:
        additional_carb_text = ""

    integron_amr = [
        row
        for row in contig_rows
        if row["integron_detected"] == "yes"
        and (row["AMR_genes"] != "none" or row["cassette_array_genes"] != "none")
    ]
    if integron_amr:
        integron_text = "; ".join(
            f"{row['contig']} ({row['integron_type']}; attC={row['attC_count']}; cassettes={row['cassette_array_genes']})"
            for row in integron_amr
        )
    else:
        integron_text = "No contig had both AMR and integron evidence in the parsed files."

    results = (
        f"Across {counts['contigs']} contigs/FASTA records, the integrated analysis found {counts['amr']} contigs with "
        f"AMR gene hits, {counts['virulence']} contigs with VFDB virulence-associated hits, {counts['replicons']} contigs "
        f"with plasmid replicon evidence, {counts['mobility']} contigs with MOB-suite mobility evidence, and "
        f"{counts['integrons']} contigs with IntegronFinder integron/CALIN/In0 evidence. Carbapenemase gene groups with "
        f"replicon-level plasmid evidence were detected as follows: {carb_text}{additional_carb_text}. "
        f"Integron/cassette evidence and AMR genes or AMR-like cassette annotations were present on the same contig in "
        f"{len(integron_amr)} contigs: {integron_text}. VFDB rows are listed as database hits in the output tables."
    )

    input_lines = []
    for key in [
        "abricate_combined",
        "abricate_full",
        "abricate_summary",
        "mob_typer",
        "mob_mge",
        "integron_summary",
        "integron_integrons",
        "integron_log",
        "isescan",
        "fasta",
    ]:
        for path in discovered.get(key, []):
            input_lines.append(f"- {key}: `{relpath(path)}`")
    if not input_lines:
        input_lines.append("- No input files were detected.")

    return (
        "# Methods and Results Draft\n\n"
        "## Methods\n\n"
        f"{methods}\n\n"
        "## Results\n\n"
        f"{results}\n\n"
        "## Input Files Used\n\n"
        + "\n".join(input_lines)
        + "\n"
    )


def make_log(
    discovered: dict[str, list[Path]],
    used_abricate: list[Path],
    skipped_abricate: list[Path],
    contig_rows: list[dict[str, str]],
    feature_rows: list[dict[str, str]],
    fasta_lengths: dict[str, int],
    isescan_included: bool,
    isescan_active: bool,
) -> str:
    counts = summarize_counts(contig_rows)
    lines = [
        "Plasmid result integration log",
        f"Working directory: {ROOT}",
        "",
        "Input files used:",
    ]
    for path in used_abricate:
        lines.append(f"- ABRicate evidence: {relpath(path)}")
    for key, label in [
        ("abricate_summary", "ABRicate summary"),
        ("mob_typer", "MOB-suite mob_typer"),
        ("mob_mge", "MOB-suite MGE report"),
        ("integron_summary", "IntegronFinder summary"),
        ("integron_integrons", "IntegronFinder integrons"),
        ("integron_log", "IntegronFinder log"),
        ("isescan", "ISEScan"),
        ("fasta", "FASTA"),
    ]:
        for path in discovered.get(key, []):
            lines.append(f"- {label}: {relpath(path)}")

    if skipped_abricate:
        lines.append("")
        lines.append("Detected ABRicate full files not used as primary evidence because combined_abricate_hits.tsv was present:")
        for path in skipped_abricate:
            lines.append(f"- {relpath(path)}")

    if discovered.get("isescan_intermediate"):
        lines.append("")
        if isescan_active:
            lines.append("ISEScan intermediate files detected but not included because an ISEScan/phmmer process is still running:")
        else:
            lines.append("ISEScan intermediate files detected but not included as final IS-element annotations:")
        for path in discovered.get("isescan_intermediate", []):
            lines.append(f"- {relpath(path)}")

    lines.extend(
        [
            "",
            "Missing expected/optional inputs:",
        ]
    )
    if not discovered.get("integron_summary") or not discovered.get("integron_integrons"):
        lines.append("- IntegronFinder output not fully detected.")
    if not isescan_included:
        if isescan_active:
            lines.append("- ISEScan is still running; ISEScan-derived IS-element annotation was not included.")
        else:
            lines.append("- ISEScan output not detected; ISEScan-derived IS-element annotation was not included.")
    if not discovered.get("mob_typer"):
        lines.append("- MOB-suite mob_typer.tsv not detected.")
    if not discovered.get("mob_mge"):
        lines.append("- MOB-suite mob_mge_report.tsv not detected.")
    if not used_abricate:
        lines.append("- ABRicate full hit table not detected.")

    lines.extend(
        [
            "",
            "Counts:",
            f"- FASTA records with lengths: {len(fasta_lengths)}",
            f"- Contigs in integrated summary: {counts['contigs']}",
            f"- Feature-level rows: {len(feature_rows)}",
            f"- Contigs with AMR genes: {counts['amr']}",
            f"- Contigs with VFDB hits: {counts['virulence']}",
            f"- Contigs with plasmid replicon evidence: {counts['replicons']}",
            f"- Contigs with MOB-suite mobility evidence: {counts['mobility']}",
            f"- Contigs with integron evidence: {counts['integrons']}",
            "",
            "Outputs generated:",
            f"- {OUT_CONTIG.name}",
            f"- {OUT_FEATURES.name}",
            f"- {OUT_MD.name}",
            f"- {OUT_LOG.name}",
        ]
    )
    return "\n".join(lines) + "\n"


def collect_contig_ids(
    fasta_lengths: dict[str, int],
    *maps: dict[str, Any],
) -> set[str]:
    contigs = set(fasta_lengths)
    for mapping in maps:
        contigs.update(mapping.keys())
    return {contig for contig in contigs if contig}


def main() -> int:
    discovered = discover_files(ROOT)
    isescan_active = isescan_process_running()
    if isescan_active and discovered.get("isescan"):
        discovered.setdefault("isescan_intermediate", []).extend(discovered["isescan"])
        discovered["isescan"] = []
    feature_rows: list[dict[str, str]] = []

    fasta_lengths = parse_fasta_lengths(discovered.get("fasta", []))
    abricate, used_abricate, skipped_abricate = parse_abricate(discovered, feature_rows)
    mob = parse_mob_typer(discovered.get("mob_typer", []), feature_rows)
    mge = parse_mob_mge(discovered.get("mob_mge", []), feature_rows)
    integron = parse_integronfinder(
        discovered.get("integron_summary", []),
        discovered.get("integron_integrons", []),
        feature_rows,
    )
    isescan = parse_isescan(discovered.get("isescan", []), feature_rows)
    isescan_included = bool(discovered.get("isescan"))

    contigs = collect_contig_ids(fasta_lengths, abricate, mob, mge, integron, isescan)
    contig_rows = build_contig_rows(contigs, fasta_lengths, abricate, mob, mge, integron, isescan)
    high_rows = [row for row in contig_rows if row["priority_level"] == "High"]
    high_rows = sorted(high_rows, key=lambda row: high_priority_rank(row), reverse=True)

    # Derive a sample column from the namespaced contig id ("{SAMPLE}__{contig}").
    # high_rows references the same dict objects as contig_rows, so it is covered.
    for row in contig_rows:
        row["sample"] = row["contig"].split("__", 1)[0]
    for row in feature_rows:
        row["sample"] = row["contig"].split("__", 1)[0]

    write_tsv(OUT_CONTIG, contig_rows, CONTIG_COLUMNS_OUT)
    write_tsv(OUT_FEATURES, feature_rows, FEATURE_COLUMNS)
    write_tsv(OUT_HIGH, high_rows, CONTIG_COLUMNS_OUT)
    OUT_MD.write_text(make_methods_and_results(contig_rows, discovered, isescan_included, isescan_active), encoding="utf-8")
    OUT_LOG.write_text(
        make_log(
            discovered,
            used_abricate,
            skipped_abricate,
            contig_rows,
            feature_rows,
            fasta_lengths,
            isescan_included,
            isescan_active,
        ),
        encoding="utf-8",
    )

    counts = summarize_counts(contig_rows)
    print("Input files used:")
    for path in used_abricate:
        print(f"- ABRicate: {relpath(path)}")
    for key in ["mob_typer", "mob_mge", "integron_summary", "integron_integrons", "fasta"]:
        for path in discovered.get(key, []):
            print(f"- {key}: {relpath(path)}")
    if isescan_included:
        for path in discovered.get("isescan", []):
            print(f"- ISEScan: {relpath(path)}")
    elif isescan_active:
        print("- ISEScan: running; intermediate files were not incorporated")
    else:
        print("- ISEScan: not detected; ISEScan-derived IS-element annotation was not included")

    print("\nOutput files generated:")
    for path in [OUT_CONTIG, OUT_FEATURES, OUT_MD, OUT_LOG]:
        print(f"- {path.name}")

    print("\nSummary:")
    print(
        f"- {counts['contigs']} contigs; {counts['amr']} with AMR; {counts['virulence']} with VFDB hits; "
        f"{counts['replicons']} with replicons; {counts['mobility']} with MOB mobility evidence; "
        f"{counts['integrons']} with integron evidence"
    )

    missing = []
    if not discovered.get("isescan"):
        missing.append("ISEScan outputs")
    if not discovered.get("integron_summary") or not discovered.get("integron_integrons"):
        missing.append("complete IntegronFinder outputs")
    if not used_abricate:
        missing.append("ABRicate full hit tables")
    if not discovered.get("mob_typer"):
        missing.append("MOB-suite mob_typer.tsv")
    if not discovered.get("mob_mge"):
        missing.append("MOB-suite mob_mge_report.tsv")
    print("- Missing expected inputs: " + (", ".join(missing) if missing else "none"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
