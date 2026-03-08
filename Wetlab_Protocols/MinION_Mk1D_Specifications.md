# MinION Mk1D – Device and IT Specifications

> [!NOTE]
> This document outlines the technical specifications of the MinION Mk1D and provides guidance for selecting a compatible computer to run the device effectively. Based on Oxford Nanopore Technologies document, January 2026.
> **FOR RESEARCH USE ONLY.**

## 1. Overview
The MinION™ Mk1D is a compact, portable nanopore sequencing device designed to bring sequencing to the sample. It must be connected to a computer for power, and sequencing control is via the MinKNOW™ software. MinKNOW manages key sequencing tasks, including:
- Data acquisition and real-time analysis
- Data streaming and device control
- Run parameter selection
- Sample identification and tracking

In addition to collecting raw nanopore signal data, MinKNOW includes a basecalling algorithm that converts this signal into DNA or RNA sequences using machine learning.

## 2. Technical Specifications

| Component | Specification |
| :--- | :--- |
| **Size and Weight** | H 13 × W 55 × D 125 mm; 130 g |
| **Maximum rated power** | 7.5 W |
| **Installation ports** | 1 × USB Type-C |
| **Software installed** | MinION driver |
| **Sequencing temperature**| Designed for sequencing at environmental temperatures of +10°C to +35°C* |
| **Heat output** | 25.6 BTU/hr maximum |
| **Installation requirement** | Maintain a minimum 5 cm clearance on all sides of the device except the base. Do not place the device on top of a laptop or other heat source. |

*\*The device electronics are functional within environmental temperatures of +5°C to +40°C.*

## 3. Site-planning (pre-delivery)

### Configuring a new host computer
> [!IMPORTANT]
> The MinION Mk1D requires MinKNOW version 24.11.10 or later.

#### Minimum vs. Recommended Specifications

*   **Recommended**: Ensures real-time, high-accuracy basecalling, including detection of modified bases (CpG-context 5mC/5hmC), alignment, and adaptive sampling. Supports generation of super-accurate basecalls in real time.
*   **Minimum**: Balances performance and cost. Enables high-accuracy basecalling, with data ready at the end of a typical 72-hour run. *Limitations:* Real-time performance may not be achievable for shorter runs. Adaptive sampling and high-accuracy basecalling may not run simultaneously. Super-accurate (SUP) basecalling may require significant post-run processing time.

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating system** | Windows 10/11 <br> Ubuntu 22.04/24.04 LTS <br> MacOS | Windows 10/11 <br> Ubuntu 22.04/24.04 LTS |
| **Peripheral** | USB Type-C (USB 2.0 or higher) | USB Type-C (USB 2.0 or higher) |
| **Memory** | 16 GB + <br> Apple: 24 GB + Unified Memory | 32 GB + |
| **GPU** | NVIDIA RTX 5060 Laptop GPU + <br> Apple: M4 Pro + | NVIDIA RTX 5090 Laptop GPU |
| **CPU** | Intel I5 + / AMD Threadripper + / Apple M4 Pro + (12-cores +) | Intel I7 + (6-cores +) |
| **Storage** | 1 TB SSD + | 2 TB SSD + |

*Note: Hardware marked with the '+' symbol indicates suitability of that specification or better.*

#### Processor details
*   MinKNOW is only supported on modern Intel, AMD, and Apple Silicon processors.
*   CPU must support AVX-2 (Intel Haswell, AMD Steamroller, or newer).
*   Intel-based Macs, Qualcomm Snapdragon, and other ARM-based chips are **not** supported.

### Network and Connectivity

*   **USB connectivity**: Must connect via USB-C port (USB 2.0 speeds required). USB-A to USB-C adapters/cables are **not supported** (insufficient power).
*   **Network access**: Required for updates and telemetry. Outbound only over TCP ports 80 and 443.

| Access type | Purpose | Required domains |
| :--- | :--- | :--- |
| **Telemetry** | MinKNOW telemetry | `ping.oxfordnanoportal.com` |
| **Software/OS updates** | MinKNOW, OS packages, GPU drivers | `cdn.oxfordnanoportal.com`, `*.ubuntu.com`, `*.nvidia.com` |
| **EPI2ME** | Container-based analysis workflows | `*.github.com`, `hub.docker.com` |
| **Nanopore login** | Account and cloud services | `id.nanoporetech.com`, `*.okta.com` |

### Other system considerations

*   **User privileges**: Local Administrator required for updates/installation (not for running sequences).
*   **Internet**: Stable connection required.
*   **Antivirus/Endpoint detection**: Disable automatic scans and software during sequencing to avoid performance interference.
*   **BIOS/Updates**: Keep BIOS up to date. Enable virtualization for EPI2ME. Set OS updates to manual mode to prevent run interruptions.

## 4. Package Contents

| Quantity | Item | Function |
| :---: | :--- | :--- |
| 1 | MinION Mk1D | DNA/RNA sequencing instrument |
| 1 | MinION Configuration Test Cell (CTC) | Verifies sequencing hardware functionality |
| 1 | USB-C 0.5 m cable | Connects device to computer |
| 1 | Quick Start Guide | Overview of system setup |
| 1 | Safety/regulatory documentation | Safe use and compliance |

## 5. Physical Installation
Allow at least 5 cm clearance at the front, rear, and sides of each unit to ensure adequate ventilation and access. Do not place on top of a laptop/computer or near active heat sources.

## 6. Data Formats and Storage

### File types
*   **FASTQ**: Extracted sequences and quality scores.
*   **BAM**: Aligned reads, including modified base calls.
*   **sequencing_summary.txt**: Metadata for all basecalled reads.
*   **POD5** (Optional): Primary raw data format. Efficient storage/processing.

### Estimated Storage Requirements
*(Assuming saving POD5, FASTQ, BAM, N50 of 23 kb)*

| Flow cell output (Gbases) | POD5 (Gbytes) | FASTQ.gz (Gbytes) | Unaligned BAM w/ mods (Gbytes) |
| :---: | :---: | :---: | :---: |
| 10 | 70 | 6.5 | 6 |
| 15 | 105 | 9.75 | 9 |
| 30 | 210 | 19.5 | 18 |
| 50 | 350 | 35 | 30 |

### EPI2ME Analysis
EPI2ME Desktop App provides local or cloud-based (AWS) workflow processing for FASTQ/BAM via custom Nextflow pipelines.

## 7. Compatibility

The MinION Mk1D is compatible with the latest chemistry for MinION/GridION Flow Cells:
*   **Flow Cells**: R10 Series (FLO-MIN114), RNA004 (FLO-MIN004RA), Flongle R10 Series (FLO-FLG114)
*   **Kits**: All V14 chemistry kits (ligation, multiplex, rapid, barcoding, ultra-long, PCR, cDNA, 16S, Direct RNA).
*   **Software**: MinKNOW, Dorado Basecall Server, EPI2ME.

---
*For full support and safety compliance documentation, refer to the original Oxford Nanopore Technologies guidelines.*
