#!/usr/bin/env python3
"""GenomicsForOneHealth wiring for the offline benchmark runner.

Thin project shim: it points the project-agnostic runner
(agent_skills/core/eval/run_harness_checks.py) at this repository's skills,
benchmark tasks, fixtures, and hooks facade. The runner itself is content-free.

Usage:
    python agent_skills/evals/run_benchmarks.py

Exit code 0 if all offline-checkable tasks pass, 1 otherwise, 2 if PyYAML is
missing.
"""

from __future__ import annotations

import os
import sys

# Make the repository root importable so `agent_skills` resolves.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import agent_skills.hooks as hooks  # facade: core engine + project parsers/validators
from agent_skills.core.eval import run_harness_checks
from agent_skills.project.eval.fixtures import FIXTURES

SKILLS_DIR = os.path.join(_REPO_ROOT, "agent_skills", "skills")
TASKS_FILE = os.path.join(_REPO_ROOT, "agent_skills", "project", "eval", "benchmark_tasks.yaml")


def main() -> int:
    return run_harness_checks.run(TASKS_FILE, SKILLS_DIR, FIXTURES, hooks)


if __name__ == "__main__":
    sys.exit(main())
