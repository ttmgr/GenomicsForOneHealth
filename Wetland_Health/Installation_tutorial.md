# Installation Tutorial

This guide provides instructions for installing the necessary bioinformatics tools for the Wetland Metagenomics & Viromics by Nanopore Sequencing project. We recommend using Mamba for managing software packages and environments, as it is generally faster than Conda. Dorado basecaller installation is handled separately as per ONT's recommendations.

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Mamba:** If you don't have Mamba, we recommend installing Mambaforge or Miniforge.
    * **Mambaforge:** [https://github.com/conda-forge/mambaforge#installation](https://github.com/conda-forge/mambaforge#installation)
    * Follow the instructions on the Mambaforge GitHub page for your operating system. This will also install Conda and set up Mamba.
* **Git:** Required for cloning the Dorado repository and potentially others.
    * Installation: [https://git-scm.com/book/en/v2/Getting-Started-Installing-Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* **Build Tools (Optional but Recommended):** Some software or their dependencies might require compilation. Having common build tools can be helpful.
    * On Linux (Debian/Ubuntu): `sudo apt-get update && sudo apt-get install build-essential`
    * On Linux (Fedora/CentOS): `sudo yum groupinstall "Development Tools"`
    * On macOS: Install Xcode Command Line Tools: `xcode-select --install`

## 2. Dorado Installation (from ONT GitHub)

Dorado is Oxford Nanopore Technologies' basecaller. It's recommended to install it from their official GitHub repository to get the latest versions and models.

1.  **Visit the Dorado GitHub page:** [https://github.com/nanoporetech/dorado](https://github.com/nanoporetech/dorado)
2.  **Check for Releases:** Look for the "Releases" section for pre-compiled binaries suitable for your system (Linux/macOS, CPU/GPU). Downloading a pre-compiled binary is often the easiest method. The DNA analysis in the manuscript used Dorado v5.0.0[cite: 83].
3.  **Follow ONT's Instructions:** The Dorado GitHub page provides detailed instructions on downloading pre-compiled versions or building from source if needed.
    * You will also need to download basecalling models compatible with your data (e.g., R10.4.1 super-accuracy models mentioned in the manuscript [cite: 83]). Dorado's documentation will guide you on model download and usage.

    ```bash
    # Example of cloning (if building from source, but check releases first)
    # git clone [https://github.com/nanoporetech/dorado.git](https://github.com/nanoporetech/dorado.git)
    # cd dorado
    # # Follow their build instructions, e.g., using cmake
    ```
    **Note:** Ensure the Dorado executable is in your system's PATH or call it using its full path.

## 3. Mamba Environment Setup

Using separate Mamba environments for each tool or logical groups of tools helps manage dependencies and avoid conflicts.

* **Creating an environment:** `mamba create -n <environment_name> -c <channel1> -c <channel2> <package_name>[=<version>]`
* **Activating an environment:** `mamba activate <environment_name>`
* **Deactivating an environment:** `mamba deactivate`

We will use the following primary channels:
* `bioconda`
* `conda-forge`

## 4. Installation of Tools via Mamba

Install each of the following tools in its own Mamba environment to ensure clean dependency management, unless specified otherwise. Versions are specified as used in the manuscript where available.

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

## 5. Database Setup

Several tools require specific databases:

* **Kraken2 Database:**
    * Kraken2 needs a pre-built database for classification. The manuscript used `nt_core database` (accessed May 2025)[cite: 88, 101].
    * You can download pre-built databases from the Kraken2 website or build your own. Building standard databases can be resource-intensive.
    * Example for downloading a small test database (replace with your chosen database):
        ```bash
        # mamba activate kraken2_env
        # kraken2-build --download-library bacteria --db /path/to/your_kraken2_db
        # kraken2-build --build --db /path/to/your_kraken2_db --threads <N>
        ```
    * The `nt_core` database would be significantly larger. Consult Kraken2 documentation and available resources for the `nt_core` database specifically.

* **AMRFinderPlus Database:**
    * AMRFinderPlus requires its own database of AMR genes and virulence factors.
    * When you install AMRFinderPlus, it usually comes with instructions to download/update the database.
        ```bash
        # mamba activate amrfinder_env
        # amrfinder --update_db --database /path/to/your_amrfinderplus_db
        ```
    * Ensure this path is provided when running `amrfinder`.

* **DIAMOND Database (NCBI nr):**
    * The manuscript used the NCBI nr database (accessed May 2025) for DIAMOND alignments[cite: 101].
    * Download `nr.gz` from the NCBI FTP site.
    * Create a DIAMOND-formatted database:
        ```bash
        # mamba activate diamond_env
        # wget ftp://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz
        # gunzip nr.gz
        # diamond makedb --in nr --db /path/to/your_diamond_db/nr
        ```
    * This is a very large database and will take significant time and disk space.

* **AIV Reference Database:**
    * The manuscript used a custom database generated for each segment from the NCBI Influenza Virus Database, containing all AIV nucleotide sequences from Europe (as of 04/03/2023)[cite: 112].
    * You will need to prepare this FASTA file containing the relevant AIV sequences to be used with Minimap2. The ENA study or supplementary information for the paper might provide this, or it would need to be reconstructed.

## 6. Using the Environments

To use a tool, activate its corresponding Mamba environment:
```bash
mamba activate <environment_name>
