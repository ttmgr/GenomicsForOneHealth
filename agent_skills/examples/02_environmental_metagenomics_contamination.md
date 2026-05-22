# Example: environmental metagenomics and contamination screening

## User request

"I have a clinical metagenome (POD5). I want to assemble it, then check whether any
contigs look contaminated before I trust the host association."

## Intent routing

A clinical metagenome with methylation-aware host association routes to
`nanopore_amr_host_association`. Contamination screening here is produced by the
Nanomotif `detect_contamination` step, which yields the motif-contig score file.

## Selected skill

`agent_skills/skills/nanopore_amr_host_association.yaml`.

## Preflight checks

```python
from agent_skills.hooks import preflight
preflight.check_dir_exists("/data/pod5")                       # ok
preflight.check_database_exists("/db/kraken2_standard")        # ok
preflight.check_command_available("nanomotif")                 # ok if installed
preflight.check_any_command_available(["metaMDBG", "flye"])    # at least one assembler
```

## Command construction (assembly + contamination steps)

```python
from agent_skills.hooks import command_builder as cb
skill = cb.load_skill_yaml(".../nanopore_amr_host_association.yaml")["skill"]
params = {
  "filtered_fastq": "/work/filtered.fastq", "assembly_out_dir": "/work/asm", "threads": 20,
  "polished_fasta": "/work/polished.fasta", "pileup_bed": "/work/sample.pileup.bed",
  "contig_bin_tsv": "/work/contig2bin.tsv", "bin_motifs_tsv": "/work/nanomotif/bin-motifs.tsv",
  "nanomotif_out_dir": "/work/nanomotif", "valid_coverage": 10,
}
# build_commands_for_skill validates parameters first, then builds every template.
```

## Expected outputs

- `/work/asm/assembly.fasta` (metaMDBG or metaFlye)
- `/work/sample.pileup.bed` (Modkit)
- `/work/nanomotif/bin-motifs.tsv`, contamination score file

## Validation

```python
from agent_skills.hooks import validation
validation.unexpected_empty_output(path="/work/polished.fasta")   # warns if missing/empty
validation.contamination_signal(n_flagged=3)
# -> {"flag": True, "severity": "warning",
#     "message": "Possible contamination signal: 3 flagged contig(s) to review."}
```

## Final report

- Assembly produced; polished FASTA present.
- WARNING: 3 contigs flagged by the Nanomotif contamination check. Review these
  before trusting their host assignment, since a contaminated contig can carry a
  misleading methylation vector.

## Caveats

Kraken2 is used here only for annotation; host association depends on the
methylation analysis. Contamination flags are advisory and require manual review;
they are not a biological or diagnostic conclusion.
