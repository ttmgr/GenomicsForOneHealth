# Contributing to GenomicsForOneHealth

Thank you for your interest in contributing! This project is developed by the [Urban Lab](https://sites.google.com/view/urban-lab/home) at the University of Zurich and Helmholtz Munich.

## Ways to Contribute

- **Bug reports** — If a script fails or documentation is unclear, please open an issue.
- **Documentation improvements** — Corrections, clarifications, and additional usage examples are always welcome.
- **New pipeline contributions** — If you have developed a pipeline in the context of our group's research that you would like to add, please get in touch first before opening a pull request.
- **Tool updates** — If a pinned tool version is outdated or a better alternative exists, open an issue to discuss.

## Workflow

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b fix/my-bugfix
   ```
2. **Make your changes.** Please keep commits focused and descriptive.
3. **Run the link checker** to make sure no internal links are broken:
   ```bash
   python verify_links.py
   ```
4. **Open a Pull Request** against `main` with a clear description of what changed and why.

## Style Guidelines

- **Markdown**: Use ATX-style headers (`#`, `##`). Keep line lengths reasonable. Do not use emojis in pipeline documentation.
- **Shell scripts**: Use `#!/usr/bin/env bash`. Include a comment above every major step. Use `/path/to/...` placeholders — never hardcode absolute paths from a specific machine.
- **Python scripts**: Follow PEP 8. Include a docstring at the top of each script describing its purpose and usage.
- **Environment files**: If your contribution introduces a new tool, add it to both the pipeline-specific `env/environment.yaml` **and** the root-level `environment.yaml`.

## Scope

This repository contains pipelines directly associated with publications from the Urban Lab. Contributions that introduce entirely new, unrelated pipelines are unlikely to be accepted. If in doubt, open an issue before investing effort.

## Contact

For questions beyond GitHub issues, please contact [Lara Urban](https://sites.google.com/view/urban-lab/home).
