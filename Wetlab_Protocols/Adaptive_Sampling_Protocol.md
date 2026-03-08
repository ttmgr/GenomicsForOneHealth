# Adaptive Sampling Protocol

> [!NOTE]
> This document provides an overview and quick-start guide to Adaptive Sampling for targeted sequencing on Oxford Nanopore devices. Based on Oxford Nanopore Technologies document, V `ADS_S1016_v1_revN_05Sep2025` (September 2025).
> **FOR RESEARCH USE ONLY.**

## 1. Introduction
Adaptive sampling is a fast and flexible targeted sequencing method that enriches or depletes regions of interest (ROI) by rejecting off-target regions in real-time. Target selection takes place during the sequencing process using MinKNOW, with no upfront sample manipulation required.

MinKNOW requires:
1.  **A FASTA reference file** representing the sample.
2.  **A `.bed` file** detailing the coordinates for regions of interest.

**Modes:**
*   **Enrichment mode:** Rejects strands that fall *outside* the ROI. Ideal when targeting <10% of the genome (expect ~5-10x enrichment).
*   **Depletion mode:** Rejects strands that fall *within* the provided ROIs (e.g., rejecting host DNA in a metagenomic analysis).

## 2. Sample Preparation and Analysis
Although no special prep is needed, the following aspects maximize output:

*   **Pore Occupancy:** Because strands are constantly rejected, pore occupancy drops. It is highly recommended to load a higher amount of sample input than for normal runs. The ideal molarity for V14 chemistry is **50–65 fmol per load**.
    *   *Example Calculation:* For a library with an N50 of 6.5 kb, 50 fmol ≈ 200 ng to 215 ng. (Input up to 600 ng has no negative effect).
*   **Library Fragmentation:** Shorter fragments reduce pore blocking and increase total data output. If your ROIs are short (e.g., 2–5 kb) and you use a 30 kb library, much time is wasted sequencing off-target regions of an accepted strand. An N50 of ~6–8 kb (e.g., Covaris g-TUBE) is generally ideal for capturing typical ROIs without excessive blocking.

## 3. Targeting and Buffering (`.bed` file)
Adaptive sampling makes its decision based on the first ~400 bases (1 second of sequencing) that enter the pore. If a strand starts just slightly outside your target region, it might be rejected before reaching the ROI. To prevent this, add **Buffer Regions** (flanking sequences) to your `.bed` file targets.

### How to Define Buffer Size
*   **General Rule:** Add an amount of buffer equal to the **N25 to N10** of the read length distribution to each side of the target.
*   **Quick Rule of Thumb:** For a normal distribution library with an N50 of ~8 kb, aim to add a **20 kb buffer** to each side.
*   *Warning:* Ensure the total amount targeted (ROI + Buffer) ideally remains **under 5%** of the full genome (up to 10% maximum for reasonable returns). Adding too much buffer to thousands of small ROIs will significantly reduce enrichment.

### Verifying the `.bed` File
Always verify your `.bed` file using Oxford Nanopore's provided checker tool (Bed Bugs) before setting up the MinKNOW run.

## 4. MinKNOW UI and Dialogs Setup

During target setup, MinKNOW contains two main sections where `.bed` and FASTA files are added:

1.  **3. Run Options (Adaptive Sampling Section):**
    *   Upload the **Buffered `.bed` File** (ROI + Buffer).
    *   Upload the Reference FASTA.
    *   *This controls the actual sequencing selection process.*
2.  **4. Analysis (Live Alignment Section):**
    *   Upload the **Unbuffered `.bed` File** (ROI only).
    *   Upload the Reference FASTA (must be the exact same FASTA).
    *   *This tracks live coverage accurately without modifying the run parameters. This is an optional feature.*

> [!CAUTION]
> **Device Limits:** Adaptive sampling demands heavy real-time computing power. It is highly recommended to turn off Live Basecalling when running adaptive sampling on multiple flow cells, keeping the device clear of background processes. If running on a MinION Mk1C, do not upload a non-indexed reference larger than 125 Mb.

---

### Understanding the Decision Process (Advanced)
When a strand is acquired:
1. MinKNOW sequences ~1 second (400 bases).
2. The sequence chunk is quickly basecalled and aligned to the FASTA reference (minimap2 short read mode).
3. The aligned location is checked against the provided `.bed` file.
4. Decision: If running *Enrichment*, alignment inside the target region = **Accept**; outside = **Reject** (polarity is reversed to eject the strand). If unaligned = **Reject**.
