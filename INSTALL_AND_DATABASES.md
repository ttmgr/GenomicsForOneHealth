# Centralized Installation and Database Setup

This guide provides the underlying setup instructions for tools and databases that are common across multiple projects in the `GenomicsForOneHealth` repository. 

Because each sub-project was validated using specific versions of bioinformatics tools to ensure reproducibility, **tool environments (like Conda/Mamba environments) are defined individually within each sub-project's directory**. 

Use this guide to set up the foundational requirements (Mamba, Dorado, Databases) once, and then refer to the specific sub-project's documentation to create the appropriate environment with exact tool versions.

---

## 1. Mamba (Conda) Installation

We heavily rely on Mamba for software environment management as it resolves dependencies significantly faster than standard Conda.

**If you do not have Mamba installed:**
```bash
# Example for installing Miniforge (which includes mamba) on Linux:
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
```
*(For macOS, the equivalent Miniforge `.sh` script is available on the [Miniforge GitHub releases page](https://github.com/conda-forge/miniforge/releases)).*

Once installed, ensure your channels are configured correctly:
```bash
mamba config --add channels bioconda
mamba config --add channels conda-forge
mamba config --set channel_priority strict
```

---

## 2. Dorado Basecaller Installation

Dorado is Oxford Nanopore Technologies' state-of-the-art basecaller. Because it is highly optimized for specific hardware (NVIDIA GPUs, Apple M-series chips) and releases frequently, it is not distributed via Conda and **must be installed manually**.

1. **Download the Binary:** Visit the [Dorado GitHub Releases page](https://github.com/nanoporetech/dorado/releases) and download the pre-compiled binary for your architecture (e.g., `dorado-x.y.z-linux-x64.tar.gz`).
2. **Extract:**
   ```bash
   tar -xvf dorado-*-linux-x64.tar.gz
   ```
3. **Add to PATH:** Add the extracted `bin/` directory to your system `$PATH`, or provide the absolute path to the `dorado` executable when running scripts.
4. **Download Models:** Dorado requires specific machine learning models (e.g., `sup` for super-accuracy or specific methylation models) for basecalling and polishing.
   ```bash
   export DORADO_MODELS_DIRECTORY="/path/to/my/dorado_models"
   dorado download --model all
   ```
   *(Ensure you export `DORADO_MODELS_DIRECTORY` in your shell or cluster submission scripts before running Dorado.)*

---

## 3. Large Database Setup

Several pipelines use Kraken2 for taxonomic classification and AMRFinderPlus for resistance gene detection. These databases are large and should be downloaded once centrally.

### Kraken2 Database
Kraken2 requires a pre-built reference index.
- **Option 1: Prebuilt (Recommended)** Download a standard or PlusPF index from the [Ben Langmead AWS index collection](https://benlangmead.github.io/aws-indexes/k2). Extract it to a designated folder.
- **Option 2: Build from NCBI (Advanced)**
  ```bash
  kraken2-build --standard --threads 24 --db /path/to/your_kraken2_standard
  ```
Once you have the database, update the `KRAKEN2_DB` variable or `--db` flags within the respective sub-project scripts to point to this central directory.

### AMRFinderPlus Database
AMRFinderPlus requires its database of AMR genes and virulence factors.
Once you install `ncbi-amrfinderplus` via the specific sub-project's Mamba environment, you can download/update the database centrally:
```bash
amrfinder --update -d /path/to/central_amrfinder_db
```
Configure your pipeline scripts to point to this directory using the `-d` flag.

### DIAMOND Database (NCBI nr)
Used primarily in the Viral Metagenomics workflows.
```bash
wget ftp://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz
gunzip nr.gz
diamond makedb --in nr --db /path/to/your_diamond_db/nr
```
*Note: This database is extremely large and compilation takes significant time and resources.*
