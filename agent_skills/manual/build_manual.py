#!/usr/bin/env python3
"""Generate the agent_skills usage manual (PDF) with reportlab.

Self-contained: built-in fonts only (Helvetica / Courier), no external services.
Content is grounded in the harness's own files (README.md, core/AGENTS.md,
project/prompts/use_skill_pack.md, core/memory/README.md).

    python agent_skills/manual/build_manual.py
"""

from __future__ import annotations

import datetime
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = os.path.join(os.path.dirname(__file__), "agent_skills_manual.pdf")

INK = colors.HexColor("#1f2d28")
MUTED = colors.HexColor("#5f6f68")
ACCENT = colors.HexColor("#1f6a55")
ACCENT_DK = colors.HexColor("#114b3a")
PANEL = colors.HexColor("#f1f5f1")
LINE = colors.HexColor("#d9e2d8")
CODEBG = colors.HexColor("#122722")
CODEINK = colors.HexColor("#edf6f1")

styles = getSampleStyleSheet()


def ps(name, **kw):
    kw.setdefault("parent", styles["Normal"])
    return ParagraphStyle(name, **kw)


BODY = ps("body", fontName="Helvetica", fontSize=10.5, leading=15.5, textColor=INK,
          spaceAfter=8, alignment=TA_LEFT)
BODY_MUTED = ps("bodymuted", parent=BODY, textColor=MUTED)
H1 = ps("h1", fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=ACCENT_DK, spaceAfter=4)
SUB = ps("sub", fontName="Helvetica", fontSize=12, leading=16, textColor=MUTED, spaceAfter=2)
EYEBROW = ps("eyebrow", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=ACCENT,
             spaceAfter=10)
H2 = ps("h2", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=ACCENT_DK,
        spaceBefore=14, spaceAfter=6)
STEP = ps("step", parent=BODY, leftIndent=2, spaceAfter=6)
BULLET = ps("bullet", parent=BODY, spaceAfter=3)
CODE = ps("code", fontName="Courier", fontSize=8.6, leading=12.5, textColor=CODEINK)
CAPTION = ps("caption", fontName="Helvetica-Oblique", fontSize=9, leading=12, textColor=MUTED,
             spaceAfter=10)


def code_block(text):
    """A dark, padded code panel."""
    p = Preformatted(text, CODE)
    t = Table([[p]], colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def bullets(items, style=BULLET):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=14, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=12,
    )


def numbered(items):
    return ListFlowable(
        [ListItem(Paragraph(t, STEP), leftIndent=18) for t in items],
        bulletType="1", leftIndent=16, bulletFontName="Helvetica-Bold",
    )


def rule():
    return HRFlowable(width="100%", thickness=0.8, color=LINE, spaceBefore=4, spaceAfter=10)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.5 * inch,
                      "agent_skills — Usage Manual")
    canvas.drawRightString(LETTER[0] - doc.rightMargin, 0.5 * inch,
                           f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(doc.leftMargin, 0.68 * inch, LETTER[0] - doc.rightMargin, 0.68 * inch)
    canvas.restoreState()


def layer_table():
    head = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=10, leading=13,
                          textColor=colors.white)
    cell = ParagraphStyle("td", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
    data = [
        [Paragraph("core/", head), Paragraph("adapters/claude_code/", head),
         Paragraph("project/", head)],
        [Paragraph("Project-agnostic engine: hooks (preflight, command_builder, "
                   "audit, generic parsers/validation), the skill schema, the agnostic "
                   "AGENTS.md contract, the memory format spec, and the offline runner.", cell),
         Paragraph("The only Claude-specific part: CLAUDE.md operating rules, an install "
                   "guide, and a sample .claude/settings.json hook wiring.", cell),
         Paragraph("This repository's content: tool-specific parsers and threshold "
                   "validators, the routing prompt, and the benchmark tasks/fixtures.", cell)],
    ]
    t = Table(data, colWidths=[2.3 * inch, 1.95 * inch, 2.25 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("BACKGROUND", (1, 0), (1, 0), ACCENT_DK),
        ("BACKGROUND", (2, 0), (2, 0), ACCENT),
        ("BACKGROUND", (0, 1), (-1, 1), PANEL),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        OUT, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title="agent_skills — Usage Manual",
        author="GenomicsForOneHealth",
    )
    s = []
    today = datetime.date.today().isoformat()

    # ---- Title ----
    s.append(Paragraph("GENOMICSFORONEHEALTH", EYEBROW))
    s.append(Paragraph("agent_skills — Usage Manual", H1))
    s.append(Paragraph("A portable coding-agent harness for documented workflows", SUB))
    s.append(Spacer(1, 4))
    s.append(Paragraph(f"Generated {today}", BODY_MUTED))
    s.append(rule())

    s.append(Paragraph(
        "<b>agent_skills</b> lets an LLM coding agent (Codex, Claude Code, Cursor, Continue, "
        "and similar tools) drive documented workflows: route a project to the right workflow, "
        "validate inputs, build commands <i>only</i> from declared templates, parse outputs, run "
        "sanity checks, and write audit logs and memory &mdash; <b>without inventing commands, "
        "parameters, tools, or databases</b>. It is not a chatbot demo: the hooks and the eval "
        "runner are plain Python you can call directly, useful even with no LLM. The local "
        "repository is always the source of truth.", BODY))

    # ---- Layers ----
    s.append(Paragraph("How it is organised", H2))
    s.append(Paragraph(
        "The pack is a portable harness with a thin project layer on top, so the engine can be "
        "lifted into any repository:", BODY))
    s.append(layer_table())
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "The 13 skill YAMLs in <font face='Courier'>skills/</font> are the <i>optional</i> project "
        "content the harness drives. The legacy <font face='Courier'>hooks/</font> facade and "
        "<font face='Courier'>evals/run_benchmarks.py</font> are kept so existing imports keep "
        "working; new code imports from <font face='Courier'>agent_skills.core.hooks</font> "
        "(portable) or <font face='Courier'>agent_skills.project.hooks</font> (project-specific).",
        CAPTION))

    # ---- Requirements + quick start ----
    s.append(Paragraph("Quick start", H2))
    s.append(Paragraph(
        "Requirements: Python 3 and PyYAML (already in the project's "
        "<font face='Courier'>environment.yaml</font>). No bioinformatics tools are needed to run "
        "the offline checks.", BODY))
    s.append(code_block(
        "git clone https://github.com/ttmgr/GenomicsForOneHealth.git\n"
        "cd GenomicsForOneHealth\n\n"
        "# run the offline check suite (no LLM, no external tools)\n"
        "python agent_skills/evals/run_benchmarks.py\n\n"
        "# inspect a skill from Python\n"
        "python -c \"from agent_skills.hooks import command_builder as cb; \\\n"
        "  print(cb.load_skill_yaml('agent_skills/skills/\\\n"
        "cre_plasmid_clustering.yaml')['skill']['display_name'])\""))
    s.append(Paragraph(
        "A green run prints <font face='Courier'>PASS 18  FAIL 0  SKIP 4</font> (the four skips "
        "are routing tasks a human reviews).", CAPTION))

    # ---- Driving a workflow ----
    s.append(Paragraph("Driving a workflow with a coding agent", H2))
    s.append(Paragraph(
        "Point your agent at the <font face='Courier'>agent_skills/</font> directory. It reads the "
        "pack README, then <font face='Courier'>core/AGENTS.md</font> (the agnostic contract; Claude "
        "Code uses <font face='Courier'>adapters/claude_code/CLAUDE.md</font>), then the relevant "
        "skill. The procedure (from "
        "<font face='Courier'>project/prompts/use_skill_pack.md</font>):", BODY))
    s.append(numbered([
        "<b>Route</b> the request to a single skill by matching molecule/sample type and goal "
        "against each skill's domain, description, and supported inputs. If nothing fits, say so.",
        "<b>Load</b> the skill with <font face='Courier'>command_builder.load_skill_yaml</font>.",
        "<b>Preflight</b>: run the skill's pre-hooks (<font face='Courier'>core/hooks/preflight.py</font>) "
        "against the real inputs, databases, and tools; stop if a check fails.",
        "<b>Validate parameters</b> with <font face='Courier'>validate_required_parameters</font>. Ask "
        "for any missing required parameter; never fill an unprovided value, never accept an "
        "undeclared one.",
        "<b>Build</b> commands with <font face='Courier'>build_commands_for_skill</font> and present "
        "them. Commands are built, not run; destructive ones need explicit confirmation.",
        "<b>Parse</b> outputs with the declared post-hooks (generic in "
        "<font face='Courier'>core/hooks/parsers.py</font>, tool-specific in "
        "<font face='Courier'>project/hooks/parsers_genomics.py</font>).",
        "<b>Validate outputs</b>: run the validation hooks and report every raised flag with its "
        "severity.",
        "<b>Audit &amp; remember</b>: write a JSON audit log, then distil the run into the memory "
        "store with <font face='Courier'>audit.append_run_record('agent_skills/memory', ...)</font>.",
        "<b>Report</b>: what was run, key parsed metrics, validation flags, and explicit caveats.",
    ]))

    # ---- Rules ----
    s.append(Paragraph("The rules that never bend", H2))
    s.append(bullets([
        "<b>The local repository is the source of truth.</b> Use only commands, parameters, tools, "
        "and databases the selected skill declares.",
        "<b>Never invent.</b> If a command is not documented, do not synthesise one &mdash; surface "
        "the skill's <font face='Courier'>needs_review</font> notes instead.",
        "<b>Build, never execute.</b> The hooks return command strings; a human runs them.",
        "<b>External references are for comparison only</b> and never override a local command.",
        "<b>All outputs are suggestions</b>, not biological, clinical, regulatory, or diagnostic "
        "conclusions &mdash; say so in the report.",
    ]))

    # ---- Memory ----
    s.append(Paragraph("Memory", H2))
    s.append(Paragraph(
        "Durable memory persists what code and git history don't: architectural decisions, "
        "distilled run summaries, and operator preferences. The format (in "
        "<font face='Courier'>core/memory/README.md</font>) is one fact per file with frontmatter, a "
        "single <font face='Courier'>MEMORY.md</font> index, and "
        "<font face='Courier'>[[wikilinks]]</font> &mdash; mirroring the Claude Code memory "
        "convention, so the adapter maps onto it with no translation. The live store for this repo is "
        "<font face='Courier'>agent_skills/memory/</font>; "
        "<font face='Courier'>audit.append_run_record</font> writes "
        "<font face='Courier'>type: run</font> entries automatically.", BODY))

    # ---- Extending ----
    s.append(Paragraph("Adding a new skill", H2))
    s.append(Paragraph(
        "Follow <font face='Courier'>core/prompts/extract_new_skill.md</font>: read the workflow's "
        "docs and scripts in full; extract tools (with version pins), every command verbatim, I/O "
        "types, and databases; write a YAML conforming to "
        "<font face='Courier'>core/schemas/skill.schema.json</font>; set "
        "<font face='Courier'>source_files</font> for traceability; flag anything ambiguous in "
        "<font face='Courier'>needs_review</font>; add a benchmark task. Then check it against "
        "<font face='Courier'>core/prompts/validate_skill.md</font> and re-run the offline suite.",
        BODY))

    # ---- Install elsewhere ----
    s.append(Paragraph("Installing the harness in another project", H2))
    s.append(Paragraph(
        "The core has no dependency on this repository's content, so lifting it is a copy plus three "
        "small wirings (see <font face='Courier'>adapters/claude_code/README.md</font>):", BODY))
    s.append(numbered([
        "Copy <font face='Courier'>agent_skills/core/</font> and "
        "<font face='Courier'>agent_skills/adapters/</font> into the target repo.",
        "Add that repo's own skill YAMLs under <font face='Courier'>skills/</font> and any "
        "project-specific parsers/validators under "
        "<font face='Courier'>project/hooks/</font> (the core works with an empty project layer too).",
        "Create a memory directory seeded with a <font face='Courier'>MEMORY.md</font> index and point "
        "<font face='Courier'>append_run_record</font> at it; merge "
        "<font face='Courier'>settings.hooks.sample.json</font> into "
        "<font face='Courier'>.claude/settings.json</font>.",
    ]))

    # ---- Caveats ----
    s.append(Paragraph("Caveats", H2))
    s.append(Paragraph(
        "All model outputs from this pack are suggestions, not biological, clinical, regulatory, or "
        "diagnostic conclusions. Commands are built, not executed; the human remains responsible for "
        "running them and interpreting the results.", BODY_MUTED))

    doc.build(s, onFirstPage=header_footer, onLaterPages=header_footer)
    return OUT


if __name__ == "__main__":
    path = build()
    print("wrote", path)
