# Example: taxonomic classification

## User request

"Classify the reads from my wetland water DNA sample and tell me the classified
fraction."

## Intent routing

Wetland passive-water DNA shotgun routes to `wetland_dna_shotgun_metagenomics`,
whose read classification step runs Kraken2 against NCBI nt_core.

## Selected skill

`agent_skills/skills/wetland_dna_shotgun_metagenomics.yaml` (command `kraken2_reads`).

## Preflight checks

```python
from agent_skills.hooks import preflight
preflight.check_database_exists("/db/kraken2_nt_core")    # ok
preflight.check_command_available("kraken2")              # ok
```

## Command construction

```python
from agent_skills.hooks import command_builder as cb
skill = cb.load_skill_yaml(".../wetland_dna_shotgun_metagenomics.yaml")["skill"]
cb.build_command(
  next(c["template"] for c in skill["command_templates"] if c["id"] == "kraken2_reads"),
  {"kraken2_db": "/db/kraken2_nt_core", "threads": 20,
   "kraken_report": "/work/report.txt", "kraken_output": "/work/output.txt",
   "filtered_fastq": "/work/filtered.fastq"},
)
# -> kraken2 --db /db/kraken2_nt_core --threads 20 --use-names
#      --report /work/report.txt --output /work/output.txt /work/filtered.fastq
```

## Expected output (Kraken2 report, illustrative)

```
 38.20	38200	38200	U	0	unclassified
 61.80	61800	120	R	1	root
 55.10	55100	80	D	2	  Bacteria
 30.40	30400	1200	G	561	    Escherichia
```

## Parsing and validation

```python
from agent_skills.hooks import parsers, validation
rep = parsers.parse_kraken2_report("/work/report.txt")
rep["summary"]["classified_percent"]      # -> 61.8
validation.low_classification_rate(rep["summary"]["classified_percent"], min_percent=50.0)
# -> {"flag": False, "severity": "info", "message": "Classification rate 61.8% above heuristic threshold."}
```

## Final report

- 61.8% of reads classified (38.2% unclassified).
- Above the 50% heuristic threshold, so classification depth looks reasonable for
  an environmental sample, though environmental samples often carry a large
  unclassified fraction.

## Caveats

The 50% threshold is a heuristic, not a repository-sourced cutoff; set it per
study. A high unclassified fraction is common for environmental DNA and is not by
itself a problem. This is not a biological conclusion.
