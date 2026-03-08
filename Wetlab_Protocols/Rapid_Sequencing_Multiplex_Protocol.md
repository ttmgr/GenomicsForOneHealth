# Rapid Sequencing DNA V14 Barcoding
> [!NOTE]
> This protocol describes how to carry out rapid barcoding of genomic DNA using the Rapid Barcoding Kit 24 or 96 V14 (`SQK-RBK114.24` / `SQK-RBK114.96`). Based on Oxford Nanopore Technologies document `RBK_9176_v114_revS_27Oct2025`.
> **FOR RESEARCH USE ONLY.**

## Overview
This protocol uses genomic DNA, allows multiplexing of 1-96 samples, and has a high-yield library preparation time of ~60 minutes. It includes transposase-driven fragmentation and is compatible with **R10.4.1** flow cells (`FLO-MIN114`). 

**Input Requirement**: 200 ng high-molecular-weight gDNA per sample.

> [!CAUTION]
> **Barcode Minimums:** For optimal output, you **must use a minimum of 4 barcodes.** If you have fewer than 4 samples, split the samples across multiple barcodes (e.g. For 2 samples, run Sample A on RB01 and RB02, and Sample B on RB03 and RB04). Each barcode still requires 200 ng of input DNA. 

## Equipment & Consumables
*   **Kit:** Rapid Barcoding Kit 24 V14 (`SQK-RBK114.24`) or 96 V14 (`SQK-RBK114.96`).
*   **Third-Party:** Qubit dsDNA HS Assay Kit, Nuclease-free water, freshly prepared 80% Ethanol, AMPure XP beads, Bovine Serum Albumin (BSA) 50 mg/ml.
*   **Hardware:** Microplate centrifuge, thermal cycler, magnetic separation rack, Hula mixer, Qubit fluorometer.

---

## Library Preparation Protocol

### 1. Preparation & Tagmentation
1. Program thermal cycler: **30°C for 2 minutes**, then **80°C for 2 minutes**.
2. Thaw all kit components at room temperature. 
   * *Required Reagents:* Rapid Adapter (`RA`), Adapter Buffer (`ADB`), AMPure XP Beads (`AXP`), Elution Buffer (`EB`), Rapid Barcodes (`RB01-RBxx`).
   * *Spin down and mix by pipetting. AXP must be vortexed.*
3. Prepare the DNA in nuclease-free water:
   * Transfer **200 ng** of gDNA per sample into individual PCR tubes or a 96-well PCR plate.
   * Adjust the volume of each to **10 µl** with nuclease-free water. Pipette mix 10-15 times.
4. Add **1.5 µl** of the desired Rapid Barcode to each sample tube/well (Total volume = 11.5 µl).
5. Mix thoroughly by pipetting and spin down.
6. Incubate on thermal cycler: **30°C for 2 mins**, then **80°C for 2 mins**. Cool on ice briefly.

### 2. Sample Pooling & Clean-up
7. Spin down tubes/plate and pool all barcoded samples into a clean 2 ml LoBind tube. 
   *(Note total volume. For 24 samples: 276 µl. Limit pooled volume to 1,000 µl maximum).*
8. Resuspend AMPure XP Beads (`AXP`) by vortexing.
9. Add an **equal volume** of `AXP` to the pooled barcoded sample, and mix by flicking.
10. Incubate on a Hula mixer for **10 minutes** at room temperature.
11. Prepare fresh 80% ethanol.
12. Spin down the sample and pellet on a magnetic rack. Pipette off the supernatant.
13. Wash the beads with **1 ml** of 80% ethanol. Remove ethanol and discard. **Repeat this wash step once.**
14. Spin down, place back on the magnet, and remove residual ethanol. Allow to air dry for ~30 seconds (do not over-dry/crack the pellet). 

### 3. Elution & Adapter Attachment
15. Remove tube from the magnet and resuspend the pellet in **15 µl Elution Buffer** (`EB`) per 24 barcodes used (e.g., 15 µl for up to 24 samples; 30 µl for 48 samples, etc.). Always elute in at least 15 µl.
16. Incubate for **10 minutes** at room temperature.
17. Pellet the beads on the magnet for ≥1 min until eluate is clear. Retain the full volume of eluate in a clean 1.5 ml LoBind tube.
18. *Optional QC*: Quantify 1 µl of eluted sample using Qubit.
19. Transfer exactly **11 µl** of the sample into a new 1.5 ml LoBind tube. 
20. In a separate fresh tube, dilute the Rapid Adapter (`RA`) by mixing:
    * **1.5 µl** Rapid Adapter (`RA`)
    * **3.5 µl** Adapter Buffer (`ADB`)
21. Add **1 µl of the diluted Rapid Adapter mix** to the 11 µl of barcoded DNA.
22. Mix gently by flicking the tube, spin down, and incubate for **5 minutes** at room temperature.
   * *The library is now prepared. Store on ice until flow cell loading.*

---

## Priming and Loading the Flow Cell
> [!IMPORTANT]
> This kit is only compatible with R10.4.1 flow cells (`FLO-MIN114`). Take the flow cell out of the fridge 20 mins before loading. Complete a flow cell pore check BEFORE loading the library.

### Reagent Prep
1. Thaw Sequencing Buffer (`SB`), Library Beads (`LIB`), Flow Cell Tether (`FCT`), and Flow Cell Flush (`FCF`) at room temperature. Vortex, spin down, and keep on ice.
2. Prepare the **Flow Cell Priming Mix**: Combine in a new tube:
   * **1,170 µl** Flow Cell Flush (`FCF`)
   * **5 µl** BSA (at 50 mg/ml) — *Required for R10.4.1 performance.*
   * **30 µl** Flow Cell Tether (`FCT`)
   * Mix by inverting. Total = 1,205 µl.

### Priming the Flow Cell
3. Open the flow cell priming port.
4. Set a P1000 pipette to 200 µl. Insert tip into port and turn the wheel to 220-230 µl to **draw back 20-30 µl** of buffer (removing any bubbles). Do not introduce air.
5. Load **800 µl of the Priming Mix** through the priming port. Wait **5 minutes**.
6. Thoroughly mix the Library Beads (`LIB`) by pipetting immediately before use. 
7. Prepare the **DNA Library for Loading** in a new tube:
   * **37.5 µl** Sequencing Buffer (`SB`)
   * **25.5 µl** Library Beads (`LIB`) — *If sample is highly viscous, use Library Solution (`LIS`) instead of `LIB`.*
   * **12 µl** Prepared DNA Library
   * Total = 75 µl.
8. Complete the flow cell priming by loading the remaining **200 µl of the Priming Mix** into the priming port. Wait **5 minutes**.
9. Open the SpotON sample port cover.
10. Gently drip the **75 µl prepared DNA library** into the SpotON sample port drop by drop. Let each drop siphon in.
11. Replace SpotON cover, close the priming port, and replace the light shield.
12. Start the sequencing run in MinKNOW.
