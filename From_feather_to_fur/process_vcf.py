!/usr/bin/env python3

import pandas as pd
import argparse

# Amino acid three-letter to one-letter code mapping
amino_acid_mapping = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*"
}

# Function to convert protein change to one-letter code
def convert_protein_change(protein_change):
    if pd.isnull(protein_change) or not isinstance(protein_change, str):
        return protein_change
    if protein_change.startswith("p."):
        protein_change = protein_change[2:]  # Remove the "p." prefix
    parts = protein_change.split()
    if len(parts) == 1:  # Handle single entries like "Thr25Thr"
        for three_letter, one_letter in amino_acid_mapping.items():
            protein_change = protein_change.replace(three_letter, one_letter)
        return protein_change
    elif len(parts) == 3:
        start, pos, end = parts[0], parts[1], parts[2]
        start = amino_acid_mapping.get(start.capitalize(), start)
        end = amino_acid_mapping.get(end.capitalize(), end)
        return f"{start}{pos}{end}"
    return protein_change

# Function to parse VCF files and extract all required information
def parse_vcf_with_details(file_path):
    variants = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("#"):
                continue
            columns = line.strip().split("\t")
            chrom, pos, id_, ref, alt, qual, filter_, info, format_, sample_data = columns[:10]
            
            # Extract frequency, position depth, and variant depth from sample data
            format_fields = format_.split(":")
            sample_fields = sample_data.split(":")
            
            freq = float(sample_fields[format_fields.index("AF")]) if "AF" in format_fields else None
            depth = int(sample_fields[format_fields.index("DP")]) if "DP" in format_fields else None
            
            variant_depth = None
            if "AD" in format_fields:
                ad_index = format_fields.index("AD")
                ad_values = sample_fields[ad_index].split(",")
                if len(ad_values) > 1:
                    variant_depth = int(ad_values[1])  # Depth for the alternate allele

            # Extract annotation (protein change)
            annotations = [field for field in info.split(";") if field.startswith("ANN=")]
            protein_change = None
            if annotations:
                annotation_details = annotations[0].split(",")[0]
                protein_change = annotation_details.split("|")[10] if len(annotation_details.split("|")) > 10 else None
            
            variants.append({
                "CHROM": chrom, 
                "POS": pos, 
                "REF": ref, 
                "ALT": alt, 
                "FREQ": freq, 
                "DEPTH": depth, 
                "VARIANT_DEPTH": variant_depth, 
                "PROTEIN_CHANGE": protein_change
            })
    return pd.DataFrame(variants)

# Function to filter variants based on frequency and presence
def filter_variants(merged_variants):
    def filter_logic(row):
        if pd.notnull(row['FREQ_animal']) and pd.notnull(row['FREQ_inoc']):
            freq_diff = abs(row['FREQ_animal'] - row['FREQ_inoc'])
            if freq_diff / row['FREQ_inoc'] >= 0.25:
                return True
        elif pd.notnull(row['FREQ_animal']) and pd.isnull(row['FREQ_inoc']):
            return True
        return False

    return merged_variants[merged_variants.apply(filter_logic, axis=1)]

# Function to generate VCF content from the filtered variants
def generate_vcf(filtered_data):
    header = [
	"##fileformat=VCFv4.2",
        "##source=Filtered_Variants",
        "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Depth of the position\">",
        "##INFO=<ID=VD,Number=1,Type=Integer,Description=\"Depth of the variant\">",
        "##INFO=<ID=AF,Number=1,Type=Float,Description=\"Allele Frequency\">",
        "##INFO=<ID=ANN,Number=.,Type=String,Description=\"Protein change annotation\">",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
    ]

    vcf_body = []
    for _, row in filtered_data.iterrows():
        info_fields = [
            f"DP={row['DEPTH_animal']}" if pd.notnull(row['DEPTH_animal']) else None,
            f"VD={row['VARIANT_DEPTH_animal']}" if pd.notnull(row['VARIANT_DEPTH_animal']) else None,
            f"AF={row['FREQ_animal']}" if pd.notnull(row['FREQ_animal']) else None,
            f"ANN={row['PROTEIN_CHANGE_animal']}" if pd.notnull(row['PROTEIN_CHANGE_animal']) else None
        ]
	info = ";".join([field for field in info_fields if field is not None])
        vcf_body.append(f"{row['CHROM']}\t{row['POS']}\t.\t{row['REF']}\t{row['ALT']}\t.\tPASS\t{info}")

    return header + vcf_body

# Main function to parse arguments and process files
def main():
    parser = argparse.ArgumentParser(description="Process VCF files to generate filtered variants and VCF outputs.")
    parser.add_argument("--animal", required=True, help="Path to animal VCF file")
    parser.add_argument("--inoculum", required=True, help="Path to inoculum VCF file")
    parser.add_argument("--output_excel", required=True, help="Path to output filtered variants (txt) file")
    parser.add_argument("--output_vcf", required=True, help="Path to output VCF file")
    args = parser.parse_args()

    # Parse VCF files
    animal_variants = parse_vcf_with_details(args.animal)
    inoculum_variants = parse_vcf_with_details(args.inoculum)

    # Merge datasets
    merged_variants = pd.merge(
        animal_variants, 
        inoculum_variants, 
        on=['CHROM', 'POS', 'REF', 'ALT'], 
        suffixes=('_animal', '_inoc'), 
        how='outer'
    )

    # Filter variants
    filtered_variants = filter_variants(merged_variants)

    # Add percentage difference and convert protein changes
    filtered_variants['Percentage_Difference'] = filtered_variants.apply(
        lambda row: abs(row['FREQ_animal'] - row['FREQ_inoc']) / row['FREQ_inoc'] * 100
        if pd.notnull(row['FREQ_animal']) and pd.notnull(row['FREQ_inoc']) else None, axis=1
    )
    filtered_variants['PROTEIN_CHANGE_animal'] = filtered_variants['PROTEIN_CHANGE_animal'].apply(convert_protein_change)
    filtered_variants['PROTEIN_CHANGE_inoc'] = filtered_variants['PROTEIN_CHANGE_inoc'].apply(convert_protein_change)

    # Sort by CHROM and POS
    filtered_variants['POS'] = pd.to_numeric(filtered_variants['POS'], errors='coerce')
    filtered_variants = filtered_variants.sort_values(by=["CHROM", "POS"]).reset_index(drop=True)

    # Save filtered variants to a tab-separated file
    filtered_variants.to_csv(args.output_excel, sep="\t", index=False)

    # Generate VCF content
    vcf_content = generate_vcf(filtered_variants)

    # Save to a VCF file
    with open(args.output_vcf, 'w') as vcf_file:
        vcf_file.write("\n".join(vcf_content))

if __name__ == "__main__":
    main()
