# External Nanopore and EPI2ME reference inventory

This document compares the local GenomicsForOneHealth workflows against current
public Oxford Nanopore (ONT) and EPI2ME Labs references. The local repository is
the source of truth for this project. Upstream references are used only for
comparison, completeness, current parameter awareness, and design inspiration.
Upstream content has not been copied into the skills; where upstream differs from
local behavior, the difference is recorded here and flagged, not silently applied.

Upstream sources were crawled live (web and GitHub) on 2026-05-20. Versions and
release dates reflect that date and will drift; re-crawl before relying on them.

---

## 1. Facts derived from the local GenomicsForOneHealth repository

Source of truth. Each maps to a skill in `agent_skills/skills/`.

| Skill | Domain | Key tools (local) | Primary local sources |
| --- | --- | --- | --- |
| air_metagenomics | Environmental | Dorado/Guppy, Porechop, NanoFilt, NanoStat, Kraken2, Flye --meta, Minimap2, Racon, assembly-stats, MetaWRAP, Prokka, Bakta, Prodigal, eggNOG-mapper, ABRicate, AMRFinderPlus | Air_Metagenomics/bash_scripts/01-04, config/config.yaml |
| wetland_dna_shotgun_metagenomics | Environmental | Dorado, samtools, Porechop, NanoFilt, Seqkit, Kraken2 (nt_core), nanoMDBG, Minimap2, MEGAN-CE, AMRFinderPlus, Prodigal, PlasmidFinder, DIAMOND (VFDB) | Wetland_Health/dna_shotgun_analysis_pipeline.md, align_megan.sh |
| wetland_aiv_rna_consensus | Environmental | Dorado (RNA004), Filtlong, Minimap2, samtools, Clair3, BCFtools | Wetland_Health/virus_analysis_pipeline.md (Part A) |
| wetland_viral_metagenomics | Environmental | Filtlong, Seqkit, DIAMOND BLASTx (NR) | Wetland_Health/virus_analysis_pipeline.md (Part B) |
| wetland_12s_vertebrate_metabarcoding | Environmental | OBITools4 (obimultiplex), Cutadapt, VSEARCH, MIDORI2 | Wetland_Health/rrna_vertebrate_analysis.md |
| zambia_edna_metabarcoding | eDNA | OBITools4 (obipairing/obigrep/obimultiplex), Cutadapt, VSEARCH, MIDORI2 | eDNA_Metabarcoding/README.md, MANUAL_EXECUTION_GUIDE.md |
| listeria_adaptive_sampling | Food Safety | samtools, Porechop, NanoFilt, NanoStat, Kraken2, Seqtk, Seqkit, metaMDBG/Myloasm/Flye, Dorado polish, AMRFinderPlus | Food_Safety/Listeria-Adaptive-Sampling/scripts, docs |
| amr_nanopore | Clinical | Guppy (R9.4.1), Porechop, NanoFilt, Flye, Minimap2, Racon | AMR_nanopore/README.md, run_pipeline.sh |
| cre_plasmid_clustering | Clinical | Dorado (SUP), Porechop, NanoFilt, Seqkit, Flye, Medaka --bacteria, Minimap2, samtools, MOB-suite, AMRFinderPlus, Mash, Pling; HPC: Rasusa, CheckM2, MLST, GTDB-Tk | CRE-Plasmid-clustering/README.md, run_pipeline.sh, run_full_pipeline.sh |
| nanopore_amr_host_association | Clinical | Dorado (methylation), samtools, Chopper, metaMDBG/Flye, Modkit, Nanomotif, MOB-suite, AMRFinderPlus, Kraken2 | Nanopore-AMR-Host-Association/*.sh, *.py |
| avian_influenza_profiling | Veterinary | Dorado/Guppy, Seqkit, Flye, Minimap2, Racon, samtools, BCFtools, iVar, IRMA, blastn | Avian-Influenza-Profiling/*.sh |
| from_feather_to_fur | Veterinary | Filtlong, Porechop, Minimap2, samtools, Clair3, BCFtools, FluSurver (web) | From_feather_to_fur/variant_calling.sh, process_vcf.py |
| squiggle4viability | Viability | PyTorch (ResNet/Transformer), pod5, Dorado, Porechop, NanoFilt, Flye, Minimap2, Racon, samtools, Kraken2 | Squiggle4Viability/AI_scripts, metagenomics_analysis |

Local databases referenced: Kraken2 (standard / NCBI nt_core), AMRFinderPlus,
DIAMOND NR, MIDORI2, Bakta, eggNOG; plus CheckM2 / GTDB-Tk for the CRE HPC arm.
Tool versions are pinned in `environment.yaml` and per-project env files; see each
skill's `tools` block.

The repository already curates a small set of upstream pointers for its public
Pipeline Advisor in `docs/data/external_workflows.json`
(EPI2ME wf-bacterial-genomes, wf-metagenomics, wf-16s, and CZ ID), and Dorado
model/kit profiles in `docs/data/nanopore_profiles.json`.

---

## 2. Facts derived from EPI2ME / Oxford Nanopore upstream sources

For comparison only. Licenses: ONT-maintained tools and EPI2ME workflows are
distributed under the Oxford Nanopore Technologies Public License v1.0, except
where noted (Pomoxis and Pore-C are MPL-2.0). EPI2ME workflows are Nextflow
pipelines, invoked as `nextflow run epi2me-labs/<wf> ... -profile <docker|singularity>`,
and use sample sheets with `barcode`, `alias`, and optional `type` / `analysis_group`
columns (per wf-template).

### 2a. EPI2ME workflow index (github.com/epi2me-labs)

| Workflow | Purpose | Latest (as of 2026-05-20) | Most relevant local skill(s) |
| --- | --- | --- | --- |
| wf-basecalling | Dorado basecalling helper (duplex, modbases, alignment) | v1.5.9 | all basecalling steps |
| wf-metagenomics | Taxonomic classification (Kraken2/Minimap2) + optional AMR | v2.14.2 | air, wetland DNA, nanopore AMR host assoc, listeria |
| wf-16s | 16S/18S/ITS amplicon taxonomy (Minimap2/Kraken2) | v1.6.1 | wetland 12S, zambia eDNA |
| wf-amplicon | Haploid amplicon variant calling / de novo consensus | v1.2.2 | wetland 12S, zambia eDNA |
| wf-bacterial-genomes | Bacterial/fungal assembly + annotation + AMR (Flye/Medaka, ResFinder, MOB-suite, MLST, Sourmash, Bakta) | v2.0.2 | amr_nanopore, cre_plasmid_clustering, listeria |
| wf-clone-validation | De novo plasmid reconstruction for cloning validation | v1.8.4 | cre_plasmid_clustering |
| wf-flu | Influenza A/B typing (IRMA consensus, INSaFLU typing) | v1.4.0 | avian influenza, wetland AIV, feather to fur |
| wf-alignment | Read alignment + mapping stats (Minimap2) | v1.2.6 | (general QC) |
| wf-human-variation | Human diploid SNV/SV/CNV/STR + modbases | v2.8.0 | not applicable (One Health, non-human focus) |
| wf-transcriptomes | cDNA/direct-RNA transcript assembly + DE/DTU | v1.7.2 | not applicable |
| wf-single-cell, wf-teloseq, wf-trio, wf-cas9*, wf-mpx*, wf-artic* | single-cell, telomere, trio, Cas9, mpox, SARS-CoV-2 | (*archived/deprecated: wf-artic, wf-cas9, wf-mpx) | not applicable |

### 2b. ONT-maintained command-line tools (github.com/nanoporetech)

- Dorado (v2.0.0; v6.0 basecalling models): `dorado basecaller|aligner|demux|polish|duplex|correct|summary|download`. DNA R10.4.1 E8.2 models `dna_r10.4.1_e8.2_400bps_{fast,hac,sup}@vX`; RNA004 models `rna004_130bps_{fast,hac,sup}@vX`. DNA modification tokens: `4mC_5mC`, `5mCG_5hmCG`, `5mC_5hmC`, `6mA`; RNA: `m6A_DRACH`, `m5C`, `pseU`, etc. Replaces Guppy. R9.4.1 and RNA002 deprecated as of Dorado v1.0.0.
- Modkit (v0.6.2): `modkit pileup <bam> <out.bed> --ref <fasta> [--cpg|--combine-mods|--phased] --log ...`.
- Medaka (v2+): `medaka_consensus -i <reads> -d <draft> -o <out> -t <threads>`; `--bacteria` activates a bacterial/plasmid model. Diploid variant calling deprecated in favor of Clair3.
- Remora: modified-base model training/inference (`remora dataset|model|infer ...`).
- pod5-file-format (v0.3.x): `pip install pod5`; Apache-Arrow-based POD5 format and CLI/Python tools.
- Kit names: SQK-RBK114-24/96 (rapid barcoding), SQK-NBD114-24 (native barcoding), SQK-LSK114 (ligation). Flow cells: FLO-MIN114 (MinION), FLO-PRO114M (PromethION), FLO-FLG114 (Flongle).
- Guppy: deprecated, no longer supported; replaced by Dorado (legacy R9.4.1/R10.3 only).

---

## 3. Differences and conflicts between local repo and upstream

These are recorded for awareness. The local commands remain authoritative; do not
overwrite them with upstream values without explicit review.

1. Basecaller: several local workflows use Guppy with R9.4.1 chemistry (amr_nanopore;
   avian influenza RNA002/cDNA). Upstream has deprecated Guppy and R9.4.1 (Dorado
   only on R10.4.1/RNA004). Reproduce locally only for matching legacy data.
2. EPI2ME workflows are Nextflow pipelines with managed containers and sample sheets;
   the local workflows are modular bash/Python scripts and SLURM launchers. The
   skill pack mirrors the local script model, not the Nextflow model.
3. wf-metagenomics performs classification (+optional ResFinder AMR) but does not
   assemble, bin, run MEGAN-CE, or do methylation-based host association; the local
   environmental and host-association skills do. No upstream equivalent exists for
   the Nanomotif methylation-motif host-association method or for signal-level
   viability inference (Squiggle4Viability).
4. wf-bacterial-genomes uses Medaka auto-model selection, ResFinder/PointFinder, and
   Sourmash taxonomy; the local CRE/AMR skills use AMRFinderPlus, an explicit Medaka
   `--bacteria` model, and external MLST/Pathogenwatch. Different tool choices, not
   reconciled.
5. wf-flu builds an IRMA consensus and types with INSaFLU and offers an `--rbk` flag;
   the local AIV/feather skills benchmark BCFtools/iVar/IRMA consensus across
   chemistries and add animal-vs-inoculum differential filtering. Different scope.
6. Naming: this repo's `external_workflows.json` references `wf-16s`; the prompt also
   listed `wf-amplicon`. Both exist upstream as distinct, active workflows (wf-16s for
   rRNA taxonomy, wf-amplicon for haploid amplicon variant/consensus). No rename.

---

## 4. Items to review manually (needs_review)

Repository-internal ambiguities surfaced while building the skills. Each is also
recorded in the relevant skill's `needs_review`.

- air_metagenomics: basecalling model version differs across sources (config.yaml and
  pipelines.json say `...hac@v4.3.0`; MANUAL_EXECUTION_GUIDE says `...hac@v5.0.0`).
  NanoFilt thresholds differ (stage script `-q 9 -l 500` vs config `100` vs
  playbooks `Q>=8/100`).
- amr_nanopore: README shows `flye --nano-corr` while run_pipeline.sh uses `--nano-hq`;
  explicit AMR/MOB commands live in the KPC notebook, not the directory README.
- avian_influenza_profiling: RNA004 basecall script uses `rna004_130bps_hac@v3.0.1`
  vs the guide's `...sup...`; `irma.sh` runs `IRMA FLU-minion` vs the guide's
  `IRMA FLU`; iVar/IRMA/blastn are not in the unified environment.
- from_feather_to_fur: `process_vcf.py` and `run_process_vcf.sh` have a malformed
  first line (missing leading `#` on the shebang); `variant_calling.sh`'s final
  `bcftools view merge_output.vcf.gz` is flagged in-script as needing modification.
- listeria_adaptive_sampling: NanoFilt `-q` presence differs between the flag
  reference (`-l 100` only) and the guide (`-q 9 -l 100`); `Myloasm` is listed as an
  assembler but has no documented command line in the inspected sources;
  `scripts/pipeline.conf` (sourced by submit_pipeline.sh) is not in the listing.
- nanopore_amr_host_association: `filter_bam_by_fastq.py` and `make_contig_bins.py`
  use in-script hardcoded paths (no CLI args); the outputs doc describes columns
  that differ from what `amr_host_association.py` actually writes.
- squiggle4viability: `inference_variable_length.py` is referenced by the wrapper and
  README but is absent from `AI_scripts/`; `generate_CAM.py` (capital) vs README's
  `generate_cam.py`; `detect_drops.py` has no `--figure_path`; `preprocess.py` has no
  `-b`; a file named `mask_dark regions_cam.py` (with a space) exists.
- wetland_dna_shotgun_metagenomics: `dna_shotgun_analysis_pipeline.md` exceeds the
  single-read size limit and was not read inline; commands come from
  MANUAL_EXECUTION_GUIDE.md, the README, and align_megan.sh. Re-read the full track
  doc to capture any additional verbatim commands and exact MEGAN invocations.
