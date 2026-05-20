# Example: plasmid profiling and relatedness

## User request

"I have polished CRE isolate assemblies. Type their plasmids and compare two
IncN plasmids for relatedness."

## Intent routing

CRE isolate plasmid reconstruction and relatedness routes to
`cre_plasmid_clustering` (MOB-suite typing, then Mash distance and Pling
clustering).

## Selected skill

`agent_skills/skills/cre_plasmid_clustering.yaml` (commands `mob_recon`,
`mash_dist`, `pling_cluster`).

## Preflight checks

```python
from agent_skills.hooks import preflight
preflight.check_fasta_extension("barcode01/consensus.fasta")   # ok
preflight.check_command_available("mob_recon")                 # ok
preflight.check_command_available("mash")                      # ok
preflight.check_command_available("pling")                     # ok
```

## Command construction

```python
from agent_skills.hooks import command_builder as cb
skill = cb.load_skill_yaml(".../cre_plasmid_clustering.yaml")["skill"]
get = lambda i: next(c["template"] for c in skill["command_templates"] if c["id"] == i)

cb.build_command(get("mob_recon"),
  {"consensus_fasta": "barcode01/consensus.fasta", "mob_out_dir": "mob/barcode01"})
# -> mob_recon --infile barcode01/consensus.fasta --outdir mob/barcode01

cb.build_command(get("mash_dist"),
  {"plasmid_a": "plasmid_IncN_barcode01.fasta",
   "plasmid_b": "plasmid_IncN_barcode02.fasta", "mash_out": "mash_IncN.txt"})
# -> mash dist plasmid_IncN_barcode01.fasta plasmid_IncN_barcode02.fasta > mash_IncN.txt

cb.build_command(get("pling_cluster"),
  {"containment_distance": "0.3", "cores": 8,
   "plasmid_list": "plasmid.txt", "pling_out_dir": "clustering/pling_out"})
# -> pling align --containment_distance 0.3 --cores 8 --sourmash plasmid.txt clustering/pling_out
```

## Expected outputs

- `mob/barcode01/contig_report.txt` (MOB-suite molecule typing)
- `mash_IncN.txt` (pairwise Mash distance, e.g. `... 0.012 0 991/1000`)
- `clustering/pling_out/` (Pling DCJ network and clusters)

## Parsing and validation

```python
from agent_skills.hooks import parsers, validation
rep = parsers.parse_generic_tsv("mob/barcode01/contig_report.txt")
[r for r in rep["rows"] if r.get("molecule_type") == "plasmid"]   # plasmid contigs
validation.unexpected_empty_output(path="mash_IncN.txt")          # warns if empty
```

## Final report

- MOB-suite typed the assembly into chromosome and plasmid contigs.
- The two IncN plasmids have a small Mash distance (e.g. 0.012), suggesting close
  relatedness; Pling DCJ clustering then groups plasmids for a relatedness network.

## Caveats

Mash distance and DCJ clustering describe sequence relatedness, not transmission;
epidemiological inference requires metadata and expert review. Re-running Flye can
renumber contigs, which can break previously matched plasmid annotations (see the
skill's failure modes).
