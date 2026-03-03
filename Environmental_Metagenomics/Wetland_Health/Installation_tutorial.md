# Installation Tutorial

This guide provides instructions for creating Mamba environments for the necessary bioinformatics tools for the Wetland Metagenomics & Viromics by Nanopore Sequencing project.

⚠️ **Important:** For the general installation of **Mamba**, **Dorado**, and large databases like **Kraken2** or **AMRFinderPlus**, please see the centralized [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) at the root of the repository.

Once Mamba and Dorado are set up from the master guide, return here to create the project-specific environments.

## 1. Unified Mamba Environment Setup

We provide a unified Conda environment that installs all the tools required for this pipeline simultaneously. This is the fastest and easiest way to get started.

```bash
mamba env create -f env/environment.yaml
mamba activate wetland_health
```

If you encounter dependency conflicts or prefer to keep tools strictly isolated as they were originally run, you can optionally install each tool in its own individual environment as detailed in Section 2 below.

## 2. (Optional) Individual Installation of Tools via Mamba

If you chose not to use the unified `environment.yaml` above, you can install each of the following tools in its own Mamba environment to ensure strict version isolation. Versions are specified as used in the manuscript where available.

### Porechop
* Used for adapter and barcode trimming of ONT reads[cite: 84].
    ```bash
    mamba create -n porechop_env -c bioconda -c conda-forge porechop=0.2.4
    ```

### NanoFilt
* Used for quality and length filtering of ONT reads[cite: 85].
    ```bash
    mamba create -n nanofilt_env -c bioconda -c conda-forge nanofilt=2.8.0
    ```

### Filtlong
* Used for quality and length filtering, particularly for AIV reads in this project[cite: 110].
    ```bash
    mamba create -n filtlong_env -c bioconda -c conda-forge filtlong
    ```

### Kraken2
* Used for k-mer based taxonomic classification[cite: 88, 94, 101, 121].
    ```bash
    mamba create -n kraken2_env -c bioconda -c conda-forge kraken2=2.1.2
    ```
    * **Database:** Kraken2 requires a database. See Section 5 for database setup.

### metaFlye
* Long-read assembler for metagenomes[cite: 91].
    ```bash
    mamba create -n metaflye_env -c bioconda -c conda-forge metaflye=2.9.6
    ```

### metaMDBG
* Long-read assembler for metagenomes[cite: 92].
    ```bash
    mamba create -n metamdbg_env -c bioconda -c conda-forge metamdbg=1.1.0 # Check Bioconda for exact version 1.1
    ```
    *(Note: Check Bioconda for the availability of metaMDBG v1.1. The command installs v1.1.0 if available; adjust if necessary.)*

### Minimap2
* Used for long-read alignment. Two versions are mentioned in the manuscript.
    * For DNA assembly polishing (v2.28)[cite: 91]:
        ```bash
        mamba create -n minimap2_dna_env -c bioconda -c conda-forge minimap2=2.28
        ```
    * For AIV alignment (v2.26)[cite: 111]:
        ```bash
        mamba create -n minimap2_aiv_env -c bioconda -c conda-forge minimap2=2.26
        ```

### Racon
* Used for consensus correction/polishing for assemblies[cite: 91].
    ```bash
    mamba create -n racon_env -c bioconda -c conda-forge racon=1.5.0 # Racon 1.5 specified [cite: 91]
    ```

### Medaka
* Used for consensus correction/polishing for assemblies using neural networks, specifically for ONT data[cite: 92].
    ```bash
    mamba create -n medaka_env -c bioconda -c conda-forge ont-medaka=2.0.1 # Medaka 2.0.1 specified [cite: 92]
    ```
    * **Models:** Medaka requires specific models for polishing that correspond to the basecaller model and sequencing chemistry used. Refer to Medaka's documentation on GitHub for downloading appropriate R10.4.1 models.

### AMRFinderPlus
* Used for detection of acquired antimicrobial resistance genes[cite: 95].
    ```bash
    mamba create -n amrfinder_env -c bioconda -c conda-forge amrfinderplus=3.12.8
    ```
    * **Database:** AMRFinderPlus requires a database. See Section 5.

### DIAMOND
* High-throughput protein sequence alignment tool[cite: 101].
    ```bash
    mamba create -n diamond_env -c bioconda -c conda-forge diamond
    ```

### Seqkit
* Toolkit for FASTA/Q sequence manipulation[cite: 86, 96, 97].
    ```bash
    mamba create -n seqkit_env -c bioconda -c conda-forge seqkit=2.10.0
    ```

### SAMtools
* Utilities for SAM/BAM alignment files[cite: 113].
    ```bash
    mamba create -n samtools_env -c bioconda -c conda-forge samtools=1.17
    ```

### BCFtools
* Utilities for variant calling and consensus sequence generation[cite: 116].
    ```bash
    mamba create -n bcftools_env -c bioconda -c conda-forge bcftools=1.17
    ```

### Python Environment for PCoA
* The manuscript mentions specific Python libraries for PCoA[cite: 90]. These can be installed in a single environment.
    ```bash
    mamba create -n pcoa_py_env -c conda-forge python=3.12.2 scikit-bio=0.6.3 matplotlib=3.10.0 pandas=2.2.3 numpy=1.26.4
    ```
    *(Note: The Python version 3.12.2 is specified from the manuscript's PCoA visualization tools list[cite: 90]. Adjust if needed based on compatibility or your system preferences.)*

## 3. Database Setup

Several tools require specific databases.

⚠️ Please refer to the [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) file at the root of the repository for centralized instructions on downloading the extremely large databases for **Kraken2**, **AMRFinderPlus**, and **DIAMOND**.

Once you have downloaded them using the central instructions, configure your scripts to point to their paths.

* **AIV Reference Database:**
    * The manuscript used a custom database generated for each segment from the NCBI Influenza Virus Database, containing all AIV nucleotide sequences from Europe (as of 04/03/2023)[cite: 112].
    * You will need to prepare this FASTA file containing the relevant AIV sequences to be used with Minimap2. The ENA study or supplementary information for the paper might provide this, or it would need to be reconstructed.

## 6. Using the Environments

To use a tool, activate its corresponding Mamba environment:
```bash
mamba activate <environment_name>

 
  
