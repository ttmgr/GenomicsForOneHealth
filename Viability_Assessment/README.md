# Viability Assessment

This category covers pipelines for assessing microbial viability directly from raw nanopore electrical signals, without the need for cell culture or viability staining.

**Contact:** Harika Ürel (PhD Student) & Dr. Lara Urban

> **Pipeline Selector:** Use the public [Pipeline Selector](https://ttmgr.github.io/GenomicsForOneHealth/) if you need to determine whether your project belongs in signal-level viability inference or one of the read-based workflows elsewhere in the collection.

---

## Pipelines

### [Squiggle4Viability](./Squiggle4Viability/README.md)
*Assessing bacterial viability directly from raw nanopore electrical signals (FAST5/POD5).*

Trains a deep neural network (ResNet/Transformer) on raw nanopore signal data to distinguish DNA from viable versus dead microorganisms. Includes explainable AI (XAI) tools to identify the signal features that drive viability predictions. Validated on UV-killed *E. coli* and applied to *Chlamydia* where culture-based viability testing has high false-negative rates.

**Published in:** [GigaScience, 2025](https://academic.oup.com/gigascience/article/doi/10.1093/gigascience/giaf100/8246397)

---

## Environment

> **Note:** Squiggle4Viability requires a GPU-capable machine and has distinct PyTorch/CUDA dependencies not included in the shared `environment.yaml`. See [`Squiggle4Viability/requirements.txt`](./Squiggle4Viability/requirements.txt) and the pipeline README for setup instructions.
