"""Inline parsing fixtures for the GenomicsForOneHealth benchmark tasks.

Small synthetic tool outputs written to a temp file by the harness runner so the
parsing checks need no real bioinformatics tools. Keyed by the ``fixture`` field
in project/eval/benchmark_tasks.yaml.
"""

FIXTURES = {
    "nanostat": (
        "General summary:\n"
        "Mean read length:\t2,450.0\n"
        "Number of reads:\t820.0\n"
        "Read length N50:\t3,100.0\n"
        "Total bases:\t2,009,000.0\n"
    ),
    "kraken2": (
        " 38.20\t38200\t38200\tU\t0\tunclassified\n"
        " 61.80\t61800\t120\tR\t1\troot\n"
        " 30.40\t30400\t1200\tG\t561\t    Escherichia\n"
    ),
    "amrfinder": (
        "Protein identifier\tContig id\tGene symbol\tElement type\tClass\n"
        "NA\tcontig_3\tfosX\tAMR\tFOSFOMYCIN\n"
        "NA\tcontig_7\tlmo0919_fam\tAMR\tLINCOSAMIDE\n"
    ),
    "vcf": (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "HA\t512\t.\tA\tG\t.\tPASS\tDP=120;AF=0.98\n"
    ),
}
