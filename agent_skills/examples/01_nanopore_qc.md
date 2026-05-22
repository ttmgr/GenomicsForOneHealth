# Example: Nanopore read QC

A worked end-to-end example of how a coding agent uses the skill pack for read
quality control. Inputs and outputs are illustrative.

## User request

"I have filtered Nanopore FASTQ for an air sample. Give me read QC and tell me if
the yield looks too low to assemble."

## Intent routing

Read QC is the front-end of several skills. For an air/bioaerosol sample, route to
`air_metagenomics`, whose stage 1 runs NanoStat after Porechop/NanoFilt.

## Selected skill

`agent_skills/skills/air_metagenomics.yaml` (command `nanostat`).

## Preflight checks

```python
from agent_skills.hooks import preflight
preflight.check_fastq_extension("filtered_barcode01.fastq")   # ok
preflight.check_command_available("NanoStat")                  # ok if on PATH
```

## Command construction

```python
from agent_skills.hooks import command_builder as cb
skill = cb.load_skill_yaml("agent_skills/skills/air_metagenomics.yaml")["skill"]
cb.build_command(
    next(c["template"] for c in skill["command_templates"] if c["id"] == "nanostat"),
    {"filtered_fastq": "filtered_barcode01.fastq", "nanostat_out": "barcode01_nanostats.txt"},
)
# -> NanoStat --fastq filtered_barcode01.fastq > barcode01_nanostats.txt
```

## Expected output (NanoStat summary, illustrative)

```
General summary:
Mean read length:               2,450.0
Mean read quality:                 12.6
Number of reads:                  820.0
Read length N50:                3,100.0
Total bases:              2,009,000.0
```

## Parsing and validation

```python
from agent_skills.hooks import parsers, validation
m = parsers.parse_nanostat("barcode01_nanostats.txt")["metrics"]
validation.low_read_yield(n_reads=m["number_of_reads"], total_bases=m["total_bases"])
# -> {"flag": True, "severity": "warning",
#     "message": "Low read yield: reads=820 < 1000; bases=2009000 ... "} (reads below the
#        air-metagenomics threshold of 1000 from config.yaml)
validation.low_n50(m["read_length_n50"])
# -> {"flag": False, "severity": "info", "message": "N50 3100 within configured threshold."}
```

## Final report

- 820 reads, ~2.0 Mb total, mean Q 12.6, N50 3,100 bp.
- WARNING: read count (820) is below the air-metagenomics minimum of 1,000
  (threshold from `Air_Metagenomics/config/config.yaml`). Assembly and binning may
  be unreliable at this yield; consider pooling or re-sequencing.
- N50 is acceptable.

## Caveats

These thresholds are the repository's documented defaults, not universal cutoffs.
The flag is advisory; it is not a biological or diagnostic judgment.
