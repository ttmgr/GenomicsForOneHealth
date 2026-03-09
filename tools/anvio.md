# anvi'o: The Integrated Analysis Ecosystem

[anvi'o](https://anvio.org/) is radically different from the other tools in our stack. It must be presented not as "just another tool," but as a comprehensive platform and ecosystem for microbial 'omics.

## Ecosystem Architecture
At the center of the anvi'o ecosystem is the **contigs database**, an artifact that stores sequences, k-mer frequencies, and structural annotations. Around this hub, anvi'o provides an expansive CLI surface, an interactive graphical interface for data visual exploration, and natively integrated Snakemake-based workflows.

### Relevant Workflows
Our usage primarily leverages the following anvi'o workflow families:
- **Metagenomics:** For read recruitment and coverage profiling.
- **Pangenomics:** For exploring gene clusters across related genomes or bins.
- **Phylogenomics:** For high-resolution evolutionary tracking.
- **Contigs & SRA Download:** For foundational data retrieval and assembly processing.

## Role in the Pipeline Stack
If Conifer provides confidence and MGCalibrator provides calibration, anvi'o provides **context**. It is our Integrated Analysis Layer, where we visualize bins, track functions, and analyze pangenomic relationships.

> [!CAUTION]
> **Licensing and Code Integrity:** anvi'o is a massive piece of software licensed under **GPL-3.0**. Under no circumstances should any part of the anvi'o codebase or its official documentation be vendored, partially absorbed, or copied into this repository. We rely on standard installations and interface with it strictly via its published CLI and workflows.

### Assumptions and Caveats
- The sheer scale of anvi'o can be overwhelming; stay focused on the specific workflows relevant to the project goals.
- It assumes a high degree of integration: data must be formatted specifically into anvi'o databases before analysis can begin.
