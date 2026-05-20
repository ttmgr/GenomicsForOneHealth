#!/usr/bin/env python3
"""Offline runner for the skill-pack benchmark tasks.

Executes the tasks in benchmark_tasks.yaml that are marked offline_checkable
against the hooks package. Requires no LLM runtime and no bioinformatics tools;
parsing tasks use small inline fixtures written to a temporary directory.

Usage:
    python agent_skills/evals/run_benchmarks.py

Exit code 0 if all offline-checkable tasks pass, 1 otherwise. Routing/reporting
tasks (offline_checkable: false) are listed as skipped for human review.
"""

from __future__ import annotations

import os
import sys
import glob
import json
import tempfile

# Make the repository root importable so `agent_skills` resolves.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agent_skills.hooks import preflight, command_builder, parsers, validation, audit

SKILLS_DIR = os.path.join(_REPO_ROOT, "agent_skills", "skills")
TASKS_FILE = os.path.join(_REPO_ROOT, "agent_skills", "evals", "benchmark_tasks.yaml")

FIXTURES = {
    "nanostat": (
        "General summary:\n"
        "Mean read length:\t2,450.0\n"
        "Number of reads:\t820.0\n"
        "Read length N50:\t3,100.0\n"
        "Total bases:\t2,009,000.0\n"
    ),
    "kraken2": (
        " 38.20\t38200\t38200\tU\t0\tunclassified\n"
        " 61.80\t61800\t120\tR\t1\troot\n"
        " 30.40\t30400\t1200\tG\t561\t    Escherichia\n"
    ),
    "amrfinder": (
        "Protein identifier\tContig id\tGene symbol\tElement type\tClass\n"
        "NA\tcontig_3\tfosX\tAMR\tFOSFOMYCIN\n"
        "NA\tcontig_7\tlmo0919_fam\tAMR\tLINCOSAMIDE\n"
    ),
    "vcf": (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "HA\t512\t.\tA\tG\t.\tPASS\tDP=120;AF=0.98\n"
    ),
}


class Runner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures: list[str] = []
        self._skill_cache: dict[str, dict] = {}

    def load_skill(self, name: str) -> dict:
        if name not in self._skill_cache:
            path = os.path.join(SKILLS_DIR, f"{name}.yaml")
            self._skill_cache[name] = command_builder.load_skill_yaml(path)["skill"]
        return self._skill_cache[name]

    def check(self, task_id: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"  PASS  {task_id}")
        else:
            self.failed += 1
            self.failures.append(f"{task_id}: {detail}")
            print(f"  FAIL  {task_id}  -- {detail}")

    def run_task(self, task: dict, tmpdir: str) -> None:
        if not task.get("offline_checkable", False):
            self.skipped += 1
            print(f"  SKIP  {task['id']} (review manually: {task['category']})")
            return

        cat = task.get("category")
        tid = task["id"]

        if cat == "preflight":
            func = getattr(preflight, task["hook"].split(".")[1])
            ok = func(task["arg"])["ok"]
            self.check(tid, ok == task["expect_ok"], f"got ok={ok}")

        elif cat == "command_building":
            if "template" in task:
                res = command_builder.build_command(task["template"], task["parameters"])
                self.check(tid, task["expect_contains"] in (res.get("command") or ""), f"cmd={res.get('command')}")
            elif "command_id" in task:
                skill = self.load_skill(task["skill"])
                tmpl = next(c["template"] for c in skill["command_templates"] if c["id"] == task["command_id"])
                res = command_builder.build_command(tmpl, task["parameters"])
                self.check(tid, res["ok"] == task["expect_ok"], res.get("message", ""))
            else:
                skill = self.load_skill(task["skill"])
                res = command_builder.validate_required_parameters(skill, task["parameters"])
                self.check(tid, res["ok"] == task["expect_validate_ok"], res["message"])

        elif cat == "parsing":
            fixture_path = os.path.join(tmpdir, f"{task['fixture']}.txt")
            with open(fixture_path, "w", encoding="utf-8") as fh:
                fh.write(FIXTURES[task["fixture"]])
            result = getattr(parsers, task["parser"])(fixture_path)
            if "expect_metric" in task:
                self.check(tid, task["expect_metric"] in result.get("metrics", {}), str(result.get("metrics")))
            elif "expect_classified_percent" in task:
                got = result.get("summary", {}).get("classified_percent")
                self.check(tid, got == task["expect_classified_percent"], f"got {got}")
            elif "expect_min_hits" in task:
                self.check(tid, result.get("n_hits", 0) >= task["expect_min_hits"], str(result.get("n_hits")))
            elif "expect_min_variants" in task:
                self.check(tid, result.get("n_variants", 0) >= task["expect_min_variants"], str(result.get("n_variants")))
            else:
                self.check(tid, result.get("ok", False), "parser did not return ok")

        elif cat == "validation":
            res = getattr(validation, task["validator"])(**task.get("kwargs", {}))
            ok = res["flag"] == task["expect_flag"]
            if "expect_severity" in task:
                ok = ok and res["severity"] == task["expect_severity"]
            self.check(tid, ok, str(res))

        elif cat == "audit":
            path = os.path.join(tmpdir, "audit.json")
            audit.write_audit_log(
                path, "test_skill", {"in": "x"}, {"p": 1}, ["cmd"], {"r": 1}, [{"flag": False}],
                source_files=["a/b.sh"], external_references=["https://example.org"],
            )
            with open(path, encoding="utf-8") as fh:
                rec = json.load(fh)
            needed = {"timestamp_utc", "skill_name", "inputs", "parameters", "commands",
                      "results", "flags", "source_files", "external_references"}
            self.check(tid, needed.issubset(rec), f"missing {needed - set(rec)}")

        elif cat == "traceability":
            ok = True
            detail = ""
            for path in glob.glob(os.path.join(SKILLS_DIR, "*.yaml")):
                skill = command_builder.load_skill_yaml(path)["skill"]
                if tid == "every_skill_has_source_files":
                    if not skill.get("source_files"):
                        ok, detail = False, f"{os.path.basename(path)} has no source_files"
                        break
                elif tid == "every_skill_has_caveats_and_external_notes":
                    if not skill.get("caveats") or "external_reference_notes" not in skill:
                        ok, detail = False, f"{os.path.basename(path)} missing caveats/external_reference_notes"
                        break
            self.check(tid, ok, detail)

        elif cat == "review":
            if tid == "ambiguous_behavior_marked_needs_review":
                ok, detail = True, ""
                for name in task["expect_needs_review_skills"]:
                    nr = self.load_skill(name).get("needs_review")
                    if not nr:
                        ok, detail = False, f"{name} has empty needs_review"
                        break
                self.check(tid, ok, detail)
            elif tid == "external_refs_do_not_overwrite_local":
                ok = True
                detail = ""
                for path in glob.glob(os.path.join(SKILLS_DIR, "*.yaml")):
                    skill = command_builder.load_skill_yaml(path)["skill"]
                    notes = (skill.get("external_reference_notes") or "").lower()
                    if skill.get("external_references") and "source of truth" not in notes and "comparison" not in notes:
                        ok, detail = False, f"{os.path.basename(path)} external notes do not affirm local source of truth"
                        break
                self.check(tid, ok, detail)
            else:
                self.check(tid, False, "unknown review task")
        else:
            self.check(tid, False, f"unknown category {cat}")


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("PyYAML is required: pip install pyyaml", file=sys.stderr)
        return 2

    with open(TASKS_FILE, encoding="utf-8") as fh:
        tasks = yaml.safe_load(fh)["tasks"]

    runner = Runner()
    print(f"Running {len(tasks)} benchmark tasks ({SKILLS_DIR})\n")
    with tempfile.TemporaryDirectory() as tmpdir:
        for task in tasks:
            try:
                runner.run_task(task, tmpdir)
            except Exception as exc:  # a task should fail loudly, not crash the suite
                runner.check(task.get("id", "?"), False, f"exception: {exc}")

    print(f"\nPASS {runner.passed}  FAIL {runner.failed}  SKIP {runner.skipped}")
    if runner.failures:
        print("\nFailures:")
        for line in runner.failures:
            print(f"  - {line}")
    return 1 if runner.failed else 0


if __name__ == "__main__":
    sys.exit(main())
