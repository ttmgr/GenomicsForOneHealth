# Chemistry Technical Document

> [!NOTE]
> This document summarizes the library preparation chemistries and sequencing kits available for Oxford Nanopore Technologies devices. Based on `CHTD_500_v1_revAT_17Feb2026`.
> **FOR RESEARCH USE ONLY.**

## 1. Introduction to Library Preparation Chemistry

Library preparation converts a DNA or RNA sample into a format suitable for sequencing on nanopore flow cells. Sequencing adapters are attached to strand ends, which are loaded with a motor protein. This protein controls the strand's movement through the ion-permeable nanopores, while a hydrophobic tether localizes the template closer to the membrane, improving sensitivity ~10,000 fold. PCR is not strictly required, as nucleic acids are directly sequenced.

There are two primary types of chemistry:
1.  **Ligation-based chemistry**: Sequencing adapters are ligated onto DNA ends using ligation enzymes.
2.  **Rapid-based chemistry**: Sequencing adapters are attached via transposase fragmentation without ligation enzymes (though some barcoding kits may use rapid attachment post-transposase).

### Terminology:
*   **Sample**: Starting material.
*   **Library**: Fragments with sequencing adapters attached.
*   **Barcodes**: Known sequences attached to fragments to allow multiplexing.
*   **Reactions**: Number of times a kit can perform library prep or flow cell priming.
*   **Pack size**: Number of libraries or primed flow cells the kit can generate.

---

## 2. Sequencing Kits: Ligation vs Rapid

### A. Ligation-Based Sequencing Kits
*Optimized for maximum output and accuracy (over 99% / Q20+ on R10.4.1 pores).*

*   **Kits**: Ligation Sequencing Kit V14 (`SQK-LSK114`), Native Barcoding Kits 24/96 V14 (`SQK-NBD114.24/96`), PCR Barcoding Expansions, and XL versions.
*   **Input Requirements**:
    *   *Short fragments (<1 kb)*: 200 fmol
    *   *Fragments (1–10 kb)*: 100–200 fmol
    *   *Long fragments (>10 kb)*: 1 µg
*   **Yield Note**: Molar quantification is unreliable for long fragments; a standard 1 µg input is usually sufficient. Using <1 µg may reduce adapted strand yield and pore occupancy. If input < 100 ng, amplification (PCR/MDA) is recommended. Shearing HMW DNA (e.g., using Covaris g-TUBE) increases sequenceable strand ends, increasing output.
*   **Workflow**:
    1.  End-prep and nick repair (repair damage, generate 5' phosphates and 3' dA-tails).
    2.  Ligation of sequencing adapters (with complementary dT-tails).

### B. Rapid-Based Sequencing Kits
*Optimized for speed and simplicity, requiring limited laboratory equipment.*

*   **Kits**: Rapid Sequencing Kit V14 (`SQK-RAD114`), Ultra-Long DNA Sequencing Kit V14 (`SQK-ULK114`), Rapid Barcoding Kits 24/96 V14 (`SQK-RBK114.24/96`).
*   **Output Note**: Throughput is slightly lower than ligation kits due to fewer purification steps and the presence of transposases (which can block pores).
*   **Input Requirements**:
    *   Reduced starting input of **100 ng** HMW gDNA.
    *   *To generate long fragments*: Add >100 ng (fewer cuts per molecule).
    *   *To generate short fragments*: Add <100 ng (more cuts per molecule).
*   **Workflow**:
    1.  Transposase complex cleaves gDNA and adds transposase adapters simultaneously.
    2.  Rapid sequencing adapters are directly attached in an enzyme-free reaction.

---

## 3. Multiplexing & Barcoding Overview

Barcoding allows pooling and sequencing of multiple samples on a single flow cell to reduce cost per sample and efficiently use flow cell capacity.

### Types of Barcoding Kits:
1.  **Ligation-based (Native)**: E.g., `SQK-NBD114.24`. Uses PCR-free methods to preserve base modifications. Achieves highest accuracy and yield.
2.  **Ligation-based PCR**: E.g., `EXP-PBC096`. For low inputs (100 ng gDNA/amplicon) requiring amplification. Uses tailed primers. Capable of Dual Barcoding.
3.  **Rapid chemistry-based**: E.g., `SQK-RBK114.96`. 200 ng gDNA input. Uses transposase for fragmentation and barcode addition in one step.
4.  **Rapid chemistry-based PCR**: E.g., `SQK-RPB114.24`. Requires 1-5 ng low input gDNA. DNA is tagmented, amplified with barcoded primers, and sequenced.
5.  **Microbial Amplicon / 16S**: Targeted barcoding of the 16S rRNA or ITS genes for bacterial/fungal profiling.

*Note: Oxford Nanopore currently allows flexible expansion sets (e.g., 3 libraries of 96 barcodes vs 12 libraries of 24 barcodes per kit, coupled with Flow Cell Priming Expansions).*

---

## 4. RNA and cDNA Kits
Direct RNA sequencing (`SQK-RNA004`) skips cDNA intermediates, allowing detection of native modifications. 
*   **Input:** 300 ng poly(A) RNA or 1 µg total RNA.
*   **cDNA Kits:** Available for full-length transcripts (`SQK-PCS114`) starting from lower inputs (10 ng poly(A) RNA).

---

## 5. Sample Quality & Preparation

> [!TIP]
> **Pore Occupancy & Library Quality:** Adding less library reduces the "threadable ends" available. If pores aren't constantly sequencing, flow cell capacity is wasted. Note that the relationship between input mass and output is not strictly linear.

*   **Quantification:** Use Qubit (mass) and Agilent Femto Pulse/Bioanalyzer or Gel Electrophoresis (fragment length).
*   **Purity:** Pure DNA gives an A260/280 ratio of ~1.8. Ratios <2.0 A260/230 can indicate phenol or carbohydrate contaminants.
*   **Size Selection:** Extracting HMW DNA always yields some short fragments. To enrich for long reads, methods like SPRI beads, Short Fragment Eliminator Kit (`EXP-SFE001`), or BluePippin should be used to deplete fragments <10-25 kb.
