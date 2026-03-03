# Installation and Setup

This pipeline is designed for Linux/macOS. For Windows, we recommend using WSL2.

⚠️ **Important:** For the general installation of **Mamba**, **Dorado**, and large databases like **Kraken2** or **AMRFinderPlus**, please see the centralized [INSTALL_AND_DATABASES.md](../../../INSTALL_AND_DATABASES.md) at the root of the repository.

Once Mamba and Dorado are set up from the master guide, return here to create the project-specific environment.

## 1) Create an environment with all required tools
The pipeline uses one consolidated environment for all steps.

```bash
mamba env create -f env/environment.yaml
```

Then activate it:
```bash
mamba activate listeria_as
```
*(Note: If the scripts on your cluster specifically look for `conda activate tim`, you can either name your environment `tim` or update the `# Activate conda environment` section at the top of the `scripts/*.sh` files.)*

### Quick check that tools are available:
```bash
samtools --version
kraken2 --version
flye --version
amrfinder --version
```

## 2) Databases & Dorado Models

As declared in the [INSTALL_AND_DATABASES.md](../../../INSTALL_AND_DATABASES.md), you will need the Kraken2 and AMRFinderPlus databases, as well as Dorado basecalling models.

* **Kraken2:** Once downloaded centrally, set the `KRAKEN2_DB` variable in `scripts/05_kraken2.sh` and `scripts/13_kraken2_contigs.sh`.
* **AMRFinderPlus:** Once updated centrally, set the reference using `-d` in `11_amrfinderplus.sh`.
* **Dorado Models:** Download models centrally (`dorado download --model all`) and export `DORADO_MODELS_DIRECTORY` in `09b_dorado_polish.sh`.

---

## Where to get each tool (Official package / docs links)
- **Bioconda setup:** https://bioconda.github.io/
- **samtools:** https://bioconda.github.io/recipes/samtools/README.html
- **porechop:** https://bioconda.github.io/recipes/porechop/README.html
- **NanoFilt:** https://bioconda.github.io/recipes/nanofilt/README.html
- **NanoStat:** https://bioconda.github.io/recipes/nanostat/README.html
- **kraken2:** https://bioconda.github.io/recipes/kraken2/README.html
- **seqtk:** https://bioconda.github.io/recipes/seqtk/README.html
- **seqkit:** https://bioconda.github.io/recipes/seqkit/README.html
- **Flye:** https://bioconda.github.io/recipes/flye/README.html
- **metaMDBG:** https://bioconda.github.io/recipes/metamdbg/README.html
- **Myloasm:** https://bioconda.github.io/recipes/myloasm/README.html
- **minimap2:** https://bioconda.github.io/recipes/minimap2/README.html
- **racon:** https://bioconda.github.io/recipes/racon/README.html
- **AMRFinderPlus:** https://bioconda.github.io/recipes/ncbi-amrfinderplus/README.html

 
  
