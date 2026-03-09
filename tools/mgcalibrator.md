# MGCalibrator: The Calibration Layer

[MGCalibrator](https://github.com/NimroddeWit/MGCalibrator) is an absolute-abundance calibration layer. While relative abundances reveal community structure, they fail to capture the actual microbial load in a sample. MGCalibrator resolves this by anchoring sequencing data to physical DNA mass.

## Core Features
- Combines BAM files with empirical DNA mass measurements to compute absolute abundances.
- Extracts coverage depth metrics directly from alignments.
- Provides optional identity filtering (via CoverM) and supports optional clustering or binning upstream.
- Calculates scaling factors and employs Monte Carlo simulations to generate confidence intervals for the calibrated outputs.

## Implementation Details
MGCalibrator is structured as an accessible, modular Python package (`cli.py`, `fileutils.py`, `parser.py`, `processor.py`). It is open-source under the **MIT License**.

> [!WARNING]
> **Filename-dependent Logic:** The parser module (`parser.py`) relies heavily on specific filename conventions to identify and group samples. You must strictly adhere to its expected naming schema to avoid sample mismatch errors during processing.

## Role in the Pipeline Stack
MGCalibrator serves as the **Calibration Layer**. After Conifer ensures the taxonomic assignments are confident, MGCalibrator ensures they are quantitative. This is critical in environmental and clinical monitoring, where an increase in total pathogen load might occur without a corresponding shift in relative abundance.

### Assumptions and Caveats
- **Maturity:** While theoretically robust, the software is relatively young. Do not oversell its maturity; always validate the quantitative output distributions against biological expectations.
- **DNA Mass Accuracy:** The absolute calibration is only as accurate as your initial DNA mass quantification. Errors in benchtop fluorometry (e.g., Qubit) will propagate linearly into the final estimates.
