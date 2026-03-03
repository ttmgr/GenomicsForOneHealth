# Installation Guide for the Nanopore Metagenomics Pipeline

This guide provides concise instructions for setting up the specific software environment needed for the Air Monitoring Nanopore Sequencing Pipeline.

⚠️ **Important:** For the general installation of **Mamba**, **Dorado/Guppy basecallers**, and large databases like **Kraken2** or **AMRFinderPlus**, please see the centralized [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) at the root of the repository.

## Step 1: Create the Conda Environment

This is the primary installation step. The `environment.yaml` file will automatically install all the necessary pipeline tools into a single, isolated environment named `nanopore-metagenomics`.

```bash
# Navigate to the repository's root directory
# Create the environment using the provided file
mamba env create -f env/environment.yaml
```

This process will take some time as it downloads and installs numerous bioinformatics packages. Once complete, you can activate the environment at any time using:

```bash
mamba activate nanopore-metagenomics
```

---

## Step 2: Install ONT Basecallers & Large Databases

As noted above, **Guppy** and **Dorado** cannot be installed via `environment.yaml`. Some databases also require manual caching. 

Please refer strictly to the root [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) for how to download these external dependencies.

---

## Step 3: Run Additional Database Helpers

The pipeline requires several large databases. A helper script, `download_databases.sh`, is provided to automate this process.

1.  ** IMPORTANT :** First, open the script **`bash_scripts/download_databases.sh`** and edit the `DB_BASE_DIR` variable to the full path where you want to store the databases. This location requires **~400-500 GB** of free space.

2.  Run the script. Make sure you have activated the `nanopore-metagenomics` environment first, as it contains some of the required helper tools.
    ```bash
    mamba activate nanopore-metagenomics
    bash bash_scripts/download_databases.sh
    ```

3.  The script will download and set up databases for:
    * Kraken2
    * AMRFinderPlus
    * Bakta
    * eggNOG-mapper
    * ABRicate

4.  After the script finishes, it will print the final paths for each database. Copy these paths and update the configuration section at the top of **`bash_scripts/run_pipeline.sh`** to ensure the pipeline can find them.

---

## Key Tools Included in the Environment

Creating the environment with the `environment.yaml` file provides all the necessary tools for the automated pipeline, including:

* **Read Processing**: `Porechop`, `NanoFilt`
* **Quality Control**: `NanoStat`, `Assembly-stats`
* **Assembly & Polishing**: `Flye`, `Minimap2`, `Racon`
* **Binning**: `MetaWRAP`, `MetaBAT2`, `MaxBin2`, `CONCOCT`
* **Annotation**: `Kraken2`, `Prokka`, `Bakta`, `Prodigal`, `eggNOG-mapper`
* **AMR Detection**: `ABRicate`, `NCBI-AMRFinderPlus`
* **Utilities**: `Seqkit`, `Samtools`

With the environment activated and databases configured, you are now ready to run the main pipeline.

 
  
 
