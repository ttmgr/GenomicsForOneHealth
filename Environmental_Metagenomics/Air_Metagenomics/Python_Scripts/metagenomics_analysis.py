#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consolidated Python script for Nanopore Metagenomics Analysis.

This script combines functionalities for:
1.  Extracting read quality metrics from NanoStat.
2.  Processing and summarizing Kraken2 taxonomic classification reports.
3.  Visualizing data, including read length histograms and read count plots.
4.  Generating a comprehensive HTML report with interactive data.
"""
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template
import argparse
import logging
from collections import defaultdict

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Nanostat Metrics Extraction ---
def extract_nanostat_metrics(directory):
    """Extracts metrics from NanoStat report files."""
    data_list = []
    logger.info(f"Scanning directory for NanoStat files: {directory}")
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            try:
                barcode = filename.split('_')[1] # Assumes format 'filtered_barcode01_... .txt'
                file_stats = {'Barcode': barcode, 'Mean_Read_Length': np.nan, 'Median_Read_Length': np.nan, 'Read_Length_N50': np.nan, 'Number_of_Reads': np.nan}
                with open(os.path.join(directory, filename), 'r') as file:
                    for line in file:
                        if 'Mean read length:' in line:
                            file_stats['Mean_Read_Length'] = float(line.split(':')[1].strip().replace(',', ''))
                        elif 'Median read length:' in line:
                            file_stats['Median_Read_Length'] = float(line.split(':')[1].strip().replace(',', ''))
                        elif 'Read length N50:' in line:
                            file_stats['Read_Length_N50'] = float(line.split(':')[1].strip().replace(',', ''))
                        elif 'Number of reads:' in line:
                            file_stats['Number_of_Reads'] = float(line.split(':')[1].strip().replace(',', ''))
                data_list.append(file_stats)
            except IndexError:
                logger.warning(f"Could not extract barcode from filename: {filename}. Skipping.")
                continue
    if not data_list:
        logger.warning("No NanoStat files were processed. Please check the directory and file naming.")
    return pd.DataFrame(data_list)

# --- Read Length Histogram ---
def plot_read_length_histogram(fastq_path, output_path):
    """Generates and saves a read length histogram from a FASTQ file."""
    logger.info(f"Extracting read lengths from {fastq_path}")
    read_lengths = []
    with open(fastq_path, 'r') as file:
        for i, line in enumerate(file):
            if i % 4 == 1:  # Sequence line
                read_lengths.append(len(line.strip()))
    
    if not read_lengths:
        logger.warning(f"No reads found in {fastq_path}. Cannot generate histogram.")
        return

    read_lengths_array = np.array(read_lengths)
    
    plt.figure(figsize=(12, 7))
    plt.hist(read_lengths_array, bins=np.logspace(np.log10(max(1, np.min(read_lengths_array))), np.log10(np.max(read_lengths_array)), 80), color='lightgreen', edgecolor='black')
    plt.xscale('log')
    
    median_read_length = np.median(read_lengths_array)
    plt.axvline(median_read_length, color='black', linestyle='--', label=f'Median: {median_read_length:.2f} bp')
    
    plt.xlabel('Read Length (bp, log scale)')
    plt.ylabel('Number of Reads')
    plt.title(f'Read Length Distribution for {os.path.basename(fastq_path)}')
    plt.legend()
    plt.grid(axis='y', alpha=0.75)
    
    output_filename = os.path.join(output_path, f"{Path(fastq_path).stem}_length_histogram.png")
    plt.savefig(output_filename)
    plt.close()
    logger.info(f"Read length histogram saved to {output_filename}")

# --- Kraken2 Report Processing ---
def process_single_kraken_report(file_path):
    """Processes a single Kraken2 report to calculate relative abundances."""
    df = pd.read_csv(file_path, sep='\t', header=None, names=["Percentage", "Reads", "Reads_at_Level", "Rank", "TaxID", "Name"])
    df['Name'] = df['Name'].str.strip()
    
    # Filter out unclassified and human reads
    df_filtered = df[(df['Rank'] != 'U') & (df['Name'] != 'Homo')]
    df_taxa = df_filtered[df_filtered['Rank'].isin(['P', 'G'])] # Phylum and Genus
    
    # Calculate relative abundance for P and G ranks
    taxa_reads = df_taxa.groupby(['Rank', 'Name'])['Reads'].sum()
    total_reads_by_rank = taxa_reads.groupby('Rank').sum()
    
    if total_reads_by_rank.empty:
        return pd.DataFrame(columns=['Rank.code', 'Name', 'Relative_Abundance'])

    relative_abundances = taxa_reads.div(total_reads_by_rank, level='Rank').fillna(0) * 100
    df_relative = relative_abundances.reset_index()
    df_relative.columns = ['Rank.code', 'Name', 'Relative_Abundance']
    
    return df_relative[df_relative['Relative_Abundance'] >= 1.0]

def process_all_kraken_reports(directory_path):
    """Processes all Kraken2 reports in a directory for relative abundance."""
    combined_df = pd.DataFrame()
    logger.info(f"Scanning directory for Kraken2 reports: {directory_path}")
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            df = process_single_kraken_report(file_path)
            df['Sample'] = Path(filename).stem.replace('report_', '')
            combined_df = pd.concat([combined_df, df], ignore_index=True)
    if combined_df.empty:
        logger.warning("No Kraken2 reports were processed. Please check the directory.")
    return combined_df

def extract_kraken_read_counts(directory_path):
    """Extracts total phylum and genus read counts from Kraken2 reports."""
    data_list = []
    logger.info(f"Scanning directory for Kraken2 reports to count reads: {directory_path}")
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            try:
                # Assuming format 'report_filtered_barcode01_passed.txt' or similar standard format
                barcode = filename.split('_')[1] if 'barcode' in filename else Path(filename).stem
                phylum_sum = 0
                genus_sum = 0
                with open(os.path.join(directory_path, filename), 'r') as file:
                    for line in file:
                        parts = line.split('\t')
                        if len(parts) >= 6:
                            rank = parts[3].strip()
                            count = int(parts[1].strip())
                            if rank == 'P':
                                phylum_sum += count
                            elif rank == 'G':
                                genus_sum += count
                data_list.append({'Barcode': barcode, 'Phylum_Reads': phylum_sum, 'Genus_Reads': genus_sum})
            except Exception as e:
                logger.warning(f"Error processing {filename}: {e}")
                continue

    if not data_list:
        logger.warning("No Kraken2 reports were processed for read counts.")
    return pd.DataFrame(data_list)
    
# --- Plotting Classified Reads ---
def plot_classified_read_counts(csv_path, output_dir):
    """Creates bar plots of classified read counts from a summary CSV file."""
    try:
        data = pd.read_csv(csv_path)
        # Infer location from sample ID
        data['Location'] = data['Sample ID'].str.extract(r'(^.*?)(?:_\d| \d)')[0].fillna('Unknown')
    except Exception as e:
        logger.error(f"Failed to load or process CSV {csv_path}: {e}")
        return

    sns.set(style="whitegrid")
    for location in data['Location'].unique():
        location_data = data[data['Location'] == location].copy()
        # Create a shorter sample ID for plotting
        location_data['Short Sample ID'] = location_data['Sample ID'].str.replace(f'{location}', '', n=1).str.strip(' _')
        
        plt.figure(figsize=(14, 10))
        
        plot_cols = [col for col in ['Reads after filtering', 'Reads mapped to phylum', 'Reads mapped to genus'] if col in location_data.columns]
        if not plot_cols:
            logger.warning(f"No data columns to plot for location: {location}")
            continue

        ax = location_data.set_index('Short Sample ID')[plot_cols].plot(kind='bar')
        
        ax.set_title(f'Read Counts for {location}')
        ax.set_xlabel('Sample Replicate')
        ax.set_ylabel('Number of Reads')
        
        if 'Reads after filtering' in location_data.columns:
            ylim_max = location_data['Reads after filtering'].max() * 1.1
            ax.set_ylim(0, ylim_max)
        
        ax.legend(title='Metrics')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        output_filename = os.path.join(output_dir, f"{location}_read_counts.png")
        plt.savefig(output_filename)
        plt.close()
        logger.info(f"Read count plot saved to {output_filename}")

# --- HTML Report Generation ---
class MetagenomicsReportGenerator:
    """Generate comprehensive HTML reports for metagenomics analysis"""
    
    def __init__(self, input_dir, output_file):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.data = defaultdict(dict)
        self.figures = {}
        
    def collect_data(self):
        """Collect all analysis data from the pipeline output"""
        logger.info("Collecting data from pipeline output...")
        self._collect_preprocessing_stats()
        self._collect_assembly_stats()
        self._collect_classification_results()
        self._collect_amr_results()
        self._collect_annotation_results()
        
    def _collect_preprocessing_stats(self):
        """Collect preprocessing statistics"""
        qc_dir = self.input_dir / "03_nanostat"
        
        if qc_dir.exists():
            stats = []
            for stat_file in qc_dir.glob("*_nanostats.txt"):
                sample_stats = self._parse_nanostat_file(stat_file)
                if sample_stats:
                    stats.append(sample_stats)
            
            if stats:
                self.data['preprocessing']['stats'] = pd.DataFrame(stats)
                logger.info(f"Collected preprocessing stats for {len(stats)} samples")
    
    def _parse_nanostat_file(self, stat_file):
        """Parse NanoStat output file"""
        stats = {'sample': stat_file.stem.replace('_nanostats', '')}
        
        try:
            with open(stat_file, 'r') as f:
                for line in f:
                    if 'Mean read length:' in line:
                        stats['mean_length'] = float(line.split(':')[1].strip().replace(',', ''))
                    elif 'Median read length:' in line:
                        stats['median_length'] = float(line.split(':')[1].strip().replace(',', ''))
                    elif 'Number of reads:' in line:
                        stats['num_reads'] = int(line.split(':')[1].strip().replace(',', ''))
                    elif 'Read length N50:' in line:
                        stats['n50'] = float(line.split(':')[1].strip().replace(',', ''))
                    elif 'Total bases:' in line:
                        stats['total_bases'] = int(line.split(':')[1].strip().replace(',', ''))
                    elif 'Mean read quality:' in line:
                        stats['mean_quality'] = float(line.split(':')[1].strip())
        except Exception as e:
            logger.error(f"Error parsing {stat_file}: {e}")
            return None
        return stats
    
    def _collect_assembly_stats(self):
        """Collect assembly statistics"""
        assembly_dir = self.input_dir / "08_assembly_stats"
        
        if assembly_dir.exists():
            stats = []
            for stat_file in assembly_dir.glob("*_assemblystats.txt"):
                sample_stats = self._parse_assembly_stats(stat_file)
                if sample_stats:
                    stats.append(sample_stats)
            
            if stats:
                self.data['assembly']['stats'] = pd.DataFrame(stats)
                logger.info(f"Collected assembly stats for {len(stats)} samples")
    
    def _parse_assembly_stats(self, stat_file):
        """Parse assembly statistics file"""
        stats = {'sample': stat_file.stem.replace('_assemblystats', '')}
        
        try:
            with open(stat_file, 'r') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        metric, value = parts[0], parts[1]
                        if metric == 'sum':
                            stats['total_length'] = int(value)
                        elif metric == 'n':
                            stats['num_contigs'] = int(value)
                        elif metric == 'ave':
                            stats['avg_length'] = float(value)
                        elif metric == 'largest':
                            stats['largest_contig'] = int(value)
                        elif metric == 'N50':
                            stats['n50'] = int(value)
        except Exception as e:
            logger.error(f"Error parsing {stat_file}: {e}")
            return None
        return stats
    
    def _collect_classification_results(self):
        """Collect taxonomic classification results"""
        kraken_dir = self.input_dir / "04_kraken2_reads"
        
        if kraken_dir.exists():
            taxa_abundance = defaultdict(lambda: defaultdict(float))
            
            for report_file in kraken_dir.glob("report_*.txt"):
                sample = report_file.stem.replace('report_', '')
                
                try:
                    with open(report_file, 'r') as f:
                        for line in f:
                            parts = line.strip().split('\t')
                            if len(parts) >= 6:
                                percentage = float(parts[0])
                                rank = parts[3]
                                name = parts[5].strip()
                                
                                if rank in ['P', 'G', 'S']:  # Phylum, Genus, Species
                                    taxa_abundance[rank][(sample, name)] = percentage
                except Exception as e:
                    logger.error(f"Error parsing {report_file}: {e}")
            
            # Convert to DataFrames
            for rank, data in taxa_abundance.items():
                df_data = []
                for (sample, taxon), abundance in data.items():
                    df_data.append({
                        'sample': sample,
                        'taxon': taxon,
                        'abundance': abundance
                    })
                
                if df_data:
                    rank_name = {'P': 'phylum', 'G': 'genus', 'S': 'species'}[rank]
                    self.data['classification'][rank_name] = pd.DataFrame(df_data)
                    logger.info(f"Collected {rank_name} level classification data")
    
    def _collect_amr_results(self):
        """Collect AMR detection results"""
        abricate_dir = self.input_dir / "10_annotation" / "contig_amr"
        if abricate_dir.exists():
            amr_genes = []
            
            for result_file in abricate_dir.glob("*_abricate.txt"):
                sample = result_file.stem.replace('_abricate', '')
                
                try:
                    df = pd.read_csv(result_file, sep='\t')
                    if not df.empty:
                        df['sample'] = sample
                        amr_genes.append(df)
                except Exception as e:
                    logger.error(f"Error reading {result_file}: {e}")
            
            if amr_genes:
                self.data['amr']['abricate'] = pd.concat(amr_genes, ignore_index=True)
                logger.info(f"Collected ABRicate results for {len(amr_genes)} samples")
    
    def _collect_annotation_results(self):
        """Collect functional annotation results"""
        eggnog_dir = self.input_dir / "10_annotation" / "contig_eggnog"
        
        if eggnog_dir.exists():
            annotations = []
            
            for result_file in eggnog_dir.glob("*.emapper.annotations"):
                sample = result_file.stem.replace('.emapper', '')
                
                try:
                    df = pd.read_csv(result_file, sep='\t', comment='#')
                    if not df.empty:
                        df['sample'] = sample
                        annotations.append(df)
                except Exception as e:
                    logger.error(f"Error reading {result_file}: {e}")
            
            if annotations:
                self.data['annotation']['eggnog'] = pd.concat(annotations, ignore_index=True)
                logger.info(f"Collected eggNOG annotations for {len(annotations)} samples")
    
    def create_visualizations(self):
        """Create all visualizations for the report"""
        logger.info("Creating visualizations...")
        
        # Preprocessing visualizations
        if 'preprocessing' in self.data and 'stats' in self.data['preprocessing']:
            self._create_preprocessing_plots()
        
        # Assembly visualizations
        if 'assembly' in self.data and 'stats' in self.data['assembly']:
            self._create_assembly_plots()
        
        # Classification visualizations
        if 'classification' in self.data:
            self._create_classification_plots()
        
        # AMR visualizations
        if 'amr' in self.data:
            self._create_amr_plots()
    
    def _create_preprocessing_plots(self):
        """Create preprocessing visualization plots"""
        df = self.data['preprocessing']['stats']
        
        # Read statistics overview
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Read Count', 'Total Bases', 'Read Length Distribution', 'Quality Distribution')
        )
        
        # Read count bar plot
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['num_reads'], name='Read Count'),
            row=1, col=1
        )
        
        # Total bases bar plot
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['total_bases'], name='Total Bases'),
            row=1, col=2
        )
        
        # Read length box plot
        for sample in df['sample']:
            sample_data = df[df['sample'] == sample].iloc[0]
            fig.add_trace(
                go.Box(
                    y=[sample_data['mean_length']], 
                    name=sample,
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # N50 bar plot
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['n50'], name='N50'),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False)
        self.figures['preprocessing_stats'] = fig
    
    def _create_assembly_plots(self):
        """Create assembly visualization plots"""
        df = self.data['assembly']['stats']
        
        # Assembly statistics
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Number of Contigs', 'Total Assembly Length', 
                          'Contig N50', 'Largest Contig')
        )
        
        # Number of contigs
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['num_contigs']),
            row=1, col=1
        )
        
        # Total length
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['total_length']),
            row=1, col=2
        )
        
        # N50
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['n50']),
            row=2, col=1
        )
        
        # Largest contig
        fig.add_trace(
            go.Bar(x=df['sample'], y=df['largest_contig']),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False)
        self.figures['assembly_stats'] = fig
    
    def _create_classification_plots(self):
        """Create taxonomic classification plots"""
        # Genus level abundance heatmap
        if 'genus' in self.data['classification']:
            df = self.data['classification']['genus']
            
            # Get top 20 most abundant genera
            top_genera = df.groupby('taxon')['abundance'].sum().nlargest(20).index
            df_top = df[df['taxon'].isin(top_genera)]
            
            # Pivot for heatmap
            heatmap_data = df_top.pivot(index='taxon', columns='sample', values='abundance').fillna(0)
            
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale='Viridis'
            ))
            
            fig.update_layout(
                title='Top 20 Genera Abundance Heatmap',
                xaxis_title='Sample',
                yaxis_title='Genus',
                height=600
            )
            
            self.figures['genus_heatmap'] = fig
    
    def _create_amr_plots(self):
        """Create AMR visualization plots"""
        if 'abricate' in self.data['amr']:
            df = self.data['amr']['abricate']
            
            # AMR genes per sample
            gene_counts = df.groupby('sample')['GENE'].count()
            
            fig = go.Figure(data=[
                go.Bar(x=gene_counts.index, y=gene_counts.values)
            ])
            
            fig.update_layout(
                title='AMR Genes Detected per Sample',
                xaxis_title='Sample',
                yaxis_title='Number of AMR Genes',
                height=400
            )
            
            self.figures['amr_counts'] = fig
    
    def generate_report(self):
        """Generate the final HTML report"""
        logger.info("Generating HTML report...")
        
        # HTML template
        template_str = '''
<!DOCTYPE html>
<html>
<head>
    <title>Nanopore Metagenomics Analysis Report</title>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #333;
        }
        h1 {
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            margin-top: 40px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }
        .summary-box {
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 20px 0;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .metric-label {
            color: #666;
            font-size: 14px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #007bff;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .plot-container {
            margin: 20px 0;
        }
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Nanopore Metagenomics Analysis Report</h1>
        
        <div class="summary-box">
            <h3>Analysis Summary</h3>
            <div class="metric">
                <div class="metric-value">{{ n_samples }}</div>
                <div class="metric-label">Samples Analyzed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total_reads }}</div>
                <div class="metric-label">Total Reads</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total_bases }}</div>
                <div class="metric-label">Total Bases</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ generation_date }}</div>
                <div class="metric-label">Report Generated</div>
            </div>
        </div>
        
        <h2>1. Preprocessing Results</h2>
        {% if preprocessing_table %}
        <h3>Read Statistics Summary</h3>
        {{ preprocessing_table }}
        {% endif %}
        
        {% if preprocessing_stats_plot %}
        <div class="plot-container">
            {{ preprocessing_stats_plot }}
        </div>
        {% endif %}
        
        <h2>2. Assembly Results</h2>
        {% if assembly_table %}
        <h3>Assembly Statistics Summary</h3>
        {{ assembly_table }}
        {% endif %}
        
        {% if assembly_stats_plot %}
        <div class="plot-container">
            {{ assembly_stats_plot }}
        </div>
        {% endif %}
        
        <h2>3. Taxonomic Classification</h2>
        {% if genus_heatmap_plot %}
        <h3>Genus-level Abundance</h3>
        <div class="plot-container">
            {{ genus_heatmap_plot }}
        </div>
        {% endif %}
        
        <h2>4. Antimicrobial Resistance Detection</h2>
        {% if amr_counts_plot %}
        <h3>AMR Genes per Sample</h3>
        <div class="plot-container">
            {{ amr_counts_plot }}
        </div>
        {% endif %}
        
        {% if amr_table %}
        <h3>AMR Genes Summary</h3>
        {{ amr_table }}
        {% endif %}
        
        <h2>5. Functional Annotation</h2>
        {% if annotation_summary %}
        {{ annotation_summary }}
        {% endif %}
        
        <div class="footer">
            <p>Generated by Nanopore Metagenomics Pipeline v1.0.0</p>
            <p>{{ generation_date }}</p>
        </div>
    </div>
</body>
</html>
        '''
        
        # Prepare template data
        template_data = {
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'n_samples': 0,
            'total_reads': 0,
            'total_bases': 0
        }
        
        # Add preprocessing data
        if 'preprocessing' in self.data and 'stats' in self.data['preprocessing']:
            df = self.data['preprocessing']['stats']
            template_data['n_samples'] = len(df)
            template_data['total_reads'] = f"{df['num_reads'].sum():,}"
            template_data['total_bases'] = f"{df['total_bases'].sum():,}"
            template_data['preprocessing_table'] = df.to_html(index=False, classes='table')
        
        # Add assembly data
        if 'assembly' in self.data and 'stats' in self.data['assembly']:
            df = self.data['assembly']['stats']
            template_data['assembly_table'] = df.to_html(index=False, classes='table')
        
        # Add AMR summary
        if 'amr' in self.data and 'abricate' in self.data['amr']:
            df = self.data['amr']['abricate']
            summary = df.groupby('sample')['GENE'].count().reset_index()
            summary.columns = ['Sample', 'AMR Genes']
            template_data['amr_table'] = summary.to_html(index=False, classes='table')
        
        # Add plots
        for plot_name, fig in self.figures.items():
            template_data[f'{plot_name}_plot'] = fig.to_html(include_plotlyjs=False, div_id=plot_name)
        
        # Render template
        template = Template(template_str)
        html_content = template.render(**template_data)
        
        # Write report
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Report generated: {self.output_file}")

    def run(self):
        """Run the complete report generation pipeline"""
        self.collect_data()
        self.create_visualizations()
        self.generate_report()

# --- Main Function and Argument Parsing ---
def main():
    parser = argparse.ArgumentParser(
        description="A consolidated script for nanopore metagenomics data analysis.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='task', required=True, help='Available tasks')

    # Sub-parser for nanostat
    p_ns = subparsers.add_parser('nanostat', help='Extract metrics from NanoStat output files.')
    p_ns.add_argument('--input_dir', required=True, help='Directory containing NanoStat .txt files.')
    p_ns.add_argument('--output_file', required=True, help='Path to save the output CSV file.')

    # Sub-parser for read length histogram
    p_hist = subparsers.add_parser('length_histogram', help='Generate a read length histogram from a FASTQ file.')
    p_hist.add_argument('--input_file', required=True, help='Path to the input FASTQ file.')
    p_hist.add_argument('--output_dir', required=True, help='Directory to save the output histogram PNG.')
    
    # Sub-parser for Kraken2 relative abundance
    p_kr = subparsers.add_parser('kraken_abundance', help='Process Kraken2 reports for relative abundance of major taxa.')
    p_kr.add_argument('--input_dir', required=True, help='Directory containing Kraken2 report .txt files.')
    p_kr.add_argument('--output_file', required=True, help='Path to save the output CSV file.')

    # Sub-parser for Kraken2 read counts
    p_kc = subparsers.add_parser('kraken_counts', help='Extract total phylum and genus read counts from Kraken2 reports.')
    p_kc.add_argument('--input_dir', required=True, help='Directory containing Kraken2 report .txt files.')
    p_kc.add_argument('--output_file', required=True, help='Path to save the output CSV file.')
    
    # Sub-parser for plotting read counts
    p_plot = subparsers.add_parser('plot_counts', help='Plot classified read counts from a summary CSV file.')
    p_plot.add_argument('--input_file', required=True, help='Path to the summary CSV file.')
    p_plot.add_argument('--output_dir', required=True, help='Directory to save the output plots.')
    
    # Sub-parser for generating the final report
    p_report = subparsers.add_parser('create_report', help='Generate a final HTML report from pipeline results.')
    p_report.add_argument('--input_dir', required=True, help='Main pipeline output directory containing all results.')
    p_report.add_argument('--output_file', required=True, help='Path for the final HTML report file.')

    args = parser.parse_args()

    # --- Task Execution ---
    if hasattr(args, 'output_file'):
        os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    elif hasattr(args, 'output_dir'):
        os.makedirs(args.output_dir, exist_ok=True)

    if args.task == 'nanostat':
        df = extract_nanostat_metrics(args.input_dir)
        df.to_csv(args.output_file, index=False)
        logger.info(f"NanoStat metrics summary saved to {args.output_file}")
    
    elif args.task == 'length_histogram':
        plot_read_length_histogram(args.input_file, args.output_dir)

    elif args.task == 'kraken_abundance':
        df = process_all_kraken_reports(args.input_dir)
        df.to_csv(args.output_file, index=False)
        logger.info(f"Kraken2 relative abundance summary saved to {args.output_file}")
        
    elif args.task == 'kraken_counts':
        df = extract_kraken_read_counts(args.input_dir)
        df.to_csv(args.output_file, index=False)
        logger.info(f"Kraken2 read count summary saved to {args.output_file}")

    elif args.task == 'plot_counts':
        plot_classified_read_counts(args.input_file, args.output_dir)
    
    elif args.task == 'create_report':
        # Here input_dir is the base `--input_dir` passed to `create_report`
        report_generator = MetagenomicsReportGenerator(args.input_dir, args.output_file)
        report_generator.run()

if __name__ == '__main__':
    main()

 
  
 
