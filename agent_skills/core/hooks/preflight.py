"""Preflight checks: verify inputs, outputs, databases, and tools exist.

Every function returns a structured dict:
    {"ok": True,  "message": "..."}
    {"ok": False, "message": "..."}

These checks are read-only. check_output_dir does not create directories; it
only reports whether the path exists or could be created. They mirror the
informal ``command -v`` and directory prompts already used by the repository's
run_pipeline.sh launchers, made reusable for any coding agent.
"""

from __future__ import annotations

import os
import shutil
from typing import Iterable

# Accepted extensions, matched case-insensitively. Compound extensions
# (".fastq.gz") are checked before their single suffix.
_FASTQ_EXTS = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
_FASTA_EXTS = (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fa", ".fna", ".faa", ".frn")
_BAM_EXTS = (".bam",)
_VCF_EXTS = (".vcf.gz", ".vcf", ".bcf")


def _ok(message: str) -> dict:
    return {"ok": True, "message": message}


def _fail(message: str) -> dict:
    return {"ok": False, "message": message}


def _has_ext(path: str, exts: Iterable[str]) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(ext) for ext in exts)


def check_file_exists(path: str) -> dict:
    """Return ok if ``path`` exists and is a regular file."""
    if not path:
        return _fail("No file path provided.")
    if not os.path.exists(path):
        return _fail(f"File does not exist: {path}")
    if not os.path.isfile(path):
        return _fail(f"Path exists but is not a regular file: {path}")
    return _ok(f"File exists: {path}")


def check_dir_exists(path: str) -> dict:
    """Return ok if ``path`` exists and is a directory."""
    if not path:
        return _fail("No directory path provided.")
    if not os.path.exists(path):
        return _fail(f"Directory does not exist: {path}")
    if not os.path.isdir(path):
        return _fail(f"Path exists but is not a directory: {path}")
    return _ok(f"Directory exists: {path}")


def check_output_dir(path: str) -> dict:
    """Report whether an output directory exists or could be created.

    Does not create anything. Ok when the directory already exists and is
    writable, or when it does not exist yet but its nearest existing parent is
    writable (so the workflow could create it).
    """
    if not path:
        return _fail("No output directory path provided.")
    if os.path.isdir(path):
        if os.access(path, os.W_OK):
            return _ok(f"Output directory exists and is writable: {path}")
        return _fail(f"Output directory exists but is not writable: {path}")
    if os.path.exists(path):
        return _fail(f"Output path exists but is not a directory: {path}")
    parent = os.path.dirname(os.path.abspath(path))
    while parent and not os.path.exists(parent):
        new_parent = os.path.dirname(parent)
        if new_parent == parent:
            break
        parent = new_parent
    if parent and os.path.isdir(parent) and os.access(parent, os.W_OK):
        return _ok(f"Output directory does not exist yet but can be created under: {parent}")
    return _fail(f"Output directory cannot be created (no writable parent): {path}")


def check_fastq_extension(path: str) -> dict:
    """Return ok if ``path`` has a FASTQ extension (.fastq/.fq, optionally .gz)."""
    if not path:
        return _fail("No path provided.")
    if _has_ext(path, _FASTQ_EXTS):
        return _ok(f"FASTQ extension recognized: {path}")
    return _fail(f"Not a FASTQ extension ({', '.join(_FASTQ_EXTS)}): {path}")


def check_fasta_extension(path: str) -> dict:
    """Return ok if ``path`` has a FASTA extension."""
    if not path:
        return _fail("No path provided.")
    if _has_ext(path, _FASTA_EXTS):
        return _ok(f"FASTA extension recognized: {path}")
    return _fail(f"Not a FASTA extension ({', '.join(_FASTA_EXTS)}): {path}")


def check_bam_extension(path: str) -> dict:
    """Return ok if ``path`` has a .bam extension."""
    if not path:
        return _fail("No path provided.")
    if _has_ext(path, _BAM_EXTS):
        return _ok(f"BAM extension recognized: {path}")
    return _fail(f"Not a BAM extension (.bam): {path}")


def check_vcf_extension(path: str) -> dict:
    """Return ok if ``path`` has a VCF/BCF extension (optionally .gz)."""
    if not path:
        return _fail("No path provided.")
    if _has_ext(path, _VCF_EXTS):
        return _ok(f"VCF/BCF extension recognized: {path}")
    return _fail(f"Not a VCF/BCF extension ({', '.join(_VCF_EXTS)}): {path}")


def check_database_exists(path: str) -> dict:
    """Return ok if a database path exists and is non-empty.

    A database may be a directory (e.g. a Kraken2 index) or a single file
    (e.g. a DIAMOND .dmnd or a MIDORI2 FASTA). Emptiness is checked shallowly.
    """
    if not path:
        return _fail("No database path provided.")
    if not os.path.exists(path):
        return _fail(f"Database path does not exist: {path}")
    if os.path.isdir(path):
        if any(os.scandir(path)):
            return _ok(f"Database directory exists and is non-empty: {path}")
        return _fail(f"Database directory exists but is empty: {path}")
    if os.path.isfile(path):
        if os.path.getsize(path) > 0:
            return _ok(f"Database file exists and is non-empty: {path}")
        return _fail(f"Database file exists but is empty: {path}")
    return _fail(f"Database path is neither a file nor a directory: {path}")


def check_command_available(command: str) -> dict:
    """Return ok if ``command`` is found on PATH (via shutil.which)."""
    if not command:
        return _fail("No command name provided.")
    resolved = shutil.which(command)
    if resolved:
        return _ok(f"Command available: {command} -> {resolved}")
    return _fail(f"Command not found on PATH: {command}")


def check_any_command_available(commands: Iterable[str]) -> dict:
    """Return ok if at least one of ``commands`` is found on PATH.

    Useful for skills that document interchangeable tools (e.g. metaMDBG OR
    metaFlye for assembly).
    """
    commands = list(commands or [])
    if not commands:
        return _fail("No command names provided.")
    found = [c for c in commands if shutil.which(c)]
    if found:
        return _ok(f"Available: {', '.join(found)} (of: {', '.join(commands)})")
    return _fail(f"None of the alternatives are on PATH: {', '.join(commands)}")
