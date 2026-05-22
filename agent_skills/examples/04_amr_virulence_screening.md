# Example: AMR / virulence screening

## User request

"Run AMR and virulence detection on my recovered Listeria contigs and summarize the
genes found."

## Intent routing

A food-safety Listeria target-recovery sample routes to
`listeria_adaptive_sampling`, whose AMR step runs AMRFinderPlus in `--plus` mode.

## Selected skill

`agent_skills/skills/listeria_adaptive_sampling.yaml` (command `amrfinder`).

## Preflight checks

```python
from agent_skills.hooks import preflight
preflight.check_fasta_extension("listeria_contigs.fasta")   # ok
preflight.check_command_available("amrfinder")              # ok
preflight.check_database_exists("/db/amrfinderplus")        # ok (or update with amrfinder --update)
```

## Command construction

```python
from agent_skills.hooks import command_builder as cb
skill = cb.load_skill_yaml(".../listeria_adaptive_sampling.yaml")["skill"]
cb.build_command(
  next(c["template"] for c in skill["command_templates"] if c["id"] == "amrfinder"),
  {"contigs_fasta": "listeria_contigs.fasta", "threads": 8, "amr_out": "amr.tsv"},
)
# -> amrfinder --plus -n listeria_contigs.fasta --threads 8 > amr.tsv
```

## Expected output (AMRFinderPlus table, illustrative, tab-separated)

```
Protein identifier	Contig id	Gene symbol	Sequence name	Element type	Class	Subclass
NA	contig_3	fosX	fosfomycin resistance	AMR	FOSFOMYCIN	FOSFOMYCIN
NA	contig_7	lmo0919_fam	lincosamide resistance	AMR	LINCOSAMIDE	LINCOSAMIDE
```

## Parsing and validation

```python
from agent_skills.hooks import parsers, validation
amr = parsers.parse_amrfinder_table("amr.tsv")
amr["n_hits"]          # -> 2
amr["gene_symbols"]    # -> ["fosX", "lmo0919_fam"]
validation.missing_amr_hits(amr["n_hits"])
# -> {"flag": False, "severity": "info", "message": "2 AMR/virulence hit(s) detected."}
```

## Final report

- 2 AMR/virulence determinants detected: fosX (fosfomycin), lmo0919_fam
  (lincosamide), consistent with the intrinsic Listeria resistance profile.
- If zero hits had been returned, that would have been flagged as informational
  (possible true negative; check contig completeness/coverage).

## Caveats

Gene detection reports presence of a sequence determinant; it does not establish
phenotypic resistance. These are screening results, not a clinical or regulatory
determination.
