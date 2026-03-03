# Latest RNA and DNA nanopores allow for rapid avian influenza profiling

Code used in the manuscript.

## Quick Start
To interactively explore the available pipeline steps and obtain guidance on which script to execute, use the provided wrapper:
1. **Activate your environment** (Ensure Dorado, Flye, Minimap2, and IRMA are installed if running them).
2. **Run the Interactive Wrapper:**
    ```bash
    bash run_pipeline.sh
    ```
3. **Follow the Prompts** to select your desired workflow mode. You will be directed to the correct script, which you can run manually or script-by-script.

---

> ⚠️ **Installation:** For the general installation of **Dorado** and large databases, please see the centralized [INSTALL_AND_DATABASES.md](../../INSTALL_AND_DATABASES.md) at the root of the repository.


## RNA_mod_base_calling_dRNA004.sh

Script used for detect m6A modifications. 
```bash
# Example syntax:
bash RNA_mod_base_calling_dRNA004.sh /path/to/pod5 /path/to/output_dir
```

## base_calling_RNA002.sh 

Script used to base call direct RNA002 data
```bash
bash base_calling_RNA002.sh /path/to/fast5 /path/to/output.fastq
```

## base_calling_RNA004.sh 

Script used to base call direct RNA004 data
```bash
bash base_calling_RNA004.sh /path/to/pod5 /path/to/output.fastq
```

## base_calling_cDNA.sh

Scrip used to base call cDNA from ms-rt PCR using rapid barcoding kit
```bash
bash base_calling_cDNA.sh /path/to/pod5 /path/to/output.fastq
```

## denovo_flye.sh 

Script used for de novo assembly with Flye and polishing with minimap2 and racon 
```bash
bash denovo_flye.sh /path/to/fastq /path/to/output_dir
```

## denovo_meta_fly.sh 

Same than before but using --meta option 
```bash
bash denovo_meta_flye.sh /path/to/fastq /path/to/output_dir
```

## flu_ref_based_new.sh

Script to perform reference-based pipeline from cDNA data to all fastq files 
```bash
bash flu_ref_based_new.sh /path/to/fastq /path/to/output_dir /path/to/reference.fasta
```

## flu_ref_based_new_RNA.sh 

Script to perform reference-based pipeline from RNA004 and RNA002 data to all fastq files 
```bash
bash flu_ref_based_new_RNA.sh /path/to/fastq /path/to/output_dir /path/to/reference.fasta
```

## irma.sh 

Script to obtain consensus sequences using IRMA.  
```bash
bash irma.sh /path/to/fastq /path/to/output_dir
```

 
