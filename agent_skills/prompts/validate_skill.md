# Prompt: validate a skill

Use this prompt to check whether a skill in `agent_skills/skills/` is traceable,
non-invented, and executable. Validate against the skill's source files, not from
memory.

## Checklist

1. Source-backed commands: every entry in `command_templates` appears, verbatim, in
   one of the files listed in `source_files` (or in MANUAL_EXECUTION_GUIDE.md /
   docs in the repository). No command is invented. Literal shell braces are
   doubled (`{{`, `}}`).
2. Declared parameters: every `{placeholder}` used in any template is declared under
   `parameters`. No template references an undeclared placeholder.
   (`hooks/command_builder.build_commands_for_skill` should build every template
   given the declared parameters.)
3. Documented tools: every tool in `tools` is one the workflow actually invokes;
   version pins match the repository env files where available.
4. Databases: every required database is documented in the repository
   (INSTALL_AND_DATABASES.md or a script) or marked `needs_review`.
5. Hooks: `pre_hooks`, `post_hooks`, and `validation_hooks` reference functions that
   exist in the `hooks/` package, or are explicitly marked TODO.
6. Outputs: every declared output is documented in the source, or marked
   `needs_review`.
7. External references: `external_references` are used only for comparison or
   traceability; no upstream command has been copied into `command_templates`.
   `external_reference_notes` records the relationship and affirms the local
   repository as source of truth.
8. Traceability: `source_files` is non-empty and lists real repository-relative
   paths.
9. needs_review: anything partial, ambiguous, or conflicting is flagged with a
   specific note (not silently resolved).
10. Caveats: `caveats` includes the standing note that model outputs are
    suggestions, not biological, clinical, regulatory, or diagnostic conclusions,
    and no un-caveated final biological/clinical claim is made anywhere in the skill.

## Output

Report each item as pass/fail with a one-line reason. List every command that could
not be matched to a source file, and every placeholder that is not declared.
