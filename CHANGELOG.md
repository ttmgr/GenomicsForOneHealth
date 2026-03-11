# Changelog
All notable changes to the GenomicsForOneHealth collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-11
### Added
- Root-level `environment.yaml`: unified conda/mamba environment covering all pipelines except Squiggle4Viability.
- `tools/README.md`: index and description of all 43 per-tool reference stubs.
- `CITATION.cff`: machine-readable citation metadata for GitHub's "Cite this repository" button.
- `.gitignore`: prevents accidental commits of raw sequencing data, databases, and system files.
- `CONTRIBUTING.md`: contributor guidelines for bug reports, documentation fixes, and new pipelines.
- Category-level `README.md` files for all top-level pipeline directories.
- `Food_Safety/Listeria-Adaptive-Sampling/manuscript_methods.md`: moved from `nature_methods.md` for clarity.

### Changed
- Removed internal working-note directories (`notes/`, `reading-notes/`, `comparisons/`, `pipelines/`) which were not meaningful to external users.
- Removed `envs/` directory; env files now reside within their respective pipeline directories.
- Removed `generate_pdf.js` (unrelated personal utility).
- Updated `README.md`: removed personal notes section; added unified environment install instructions.
- Fixed 7 broken internal links across `tools/conifer.md`, `tools/mgcalibrator.md`, `tools/anvio.md`, and `Food_Safety/Listeria-Adaptive-Sampling/README.md`.

## [1.0.0] - 2026-03-01
### Added
- Initial public release: unified compilation of 10 bioinformatics pipelines.
- **Environmental Metagenomics**: Air Metagenomics, Wetland Health.
- **eDNA Metabarcoding**: Zambia eDNA (Nanopore + Illumina).
- **Food Safety**: Listeria Adaptive Sampling.
- **Clinical Isolates & Plasmid Profiling**: AMR Nanopore, CRE Plasmid Clustering, Nanopore AMR Host Association.
- **Veterinary & Zoonotic Surveillance**: Avian Influenza Profiling, From Feather to Fur.
- **Viability Assessment**: Squiggle4Viability.
- Centralized execution orchestrator (`run_all.sh`).
- Centralized installation guide (`INSTALL_AND_DATABASES.md`).
- Manual execution guide (`MANUAL_EXECUTION_GUIDE.md`).
- Full tool reference stubs in `tools/` (43 tools).
