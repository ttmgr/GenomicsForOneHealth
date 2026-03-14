import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const docsDir = path.resolve(__dirname, "..");
const dataDir = path.join(docsDir, "data");
const require = createRequire(import.meta.url);
const { computeRecommendation } = require(path.join(docsDir, "selector-engine.js"));

function readJson(filename) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, filename), "utf8"));
}

const datasets = {
  pipelines: readJson("pipelines.json"),
  questionSpec: readJson("questions.json"),
  playbooks: readJson("playbooks.json"),
  presets: readJson("presets.json"),
  outOfScopeRules: readJson("out_of_scope.json")
};

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const cases = [
  {
    name: "air_pod5_rbk114",
    answers: {
      category: "environmental_metagenomics",
      sample_type: "air_bioaerosol",
      molecule_type: "dna",
      analysis_goal: "community_profiling",
      input_format: "pod5",
      library_mode: "rbk114_24",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "prefer_hac",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "air_metagenomics",
    status: "exact",
    confidence: "high"
  },
  {
    name: "wetland_dna",
    answers: {
      category: "environmental_metagenomics",
      sample_type: "wetland_or_passive_water_sample",
      molecule_type: "dna",
      analysis_goal: "pathogen_amr_surveillance",
      input_format: "fastq",
      library_mode: "rbk114_24",
      multiplexing: "yes",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "wetland_health",
    status: "track_exact",
    track: "dna_metagenomics"
  },
  {
    name: "wetland_rna_virome",
    answers: {
      category: "environmental_metagenomics",
      sample_type: "wetland_or_passive_water_sample",
      molecule_type: "rna",
      analysis_goal: "viral_metagenomics",
      input_format: "fastq",
      library_mode: "rbk114_24",
      multiplexing: "yes",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "wetland_health",
    status: "track_exact",
    track: "rna_virome"
  },
  {
    name: "wetland_edna",
    answers: {
      category: "environmental_metagenomics",
      sample_type: "wetland_or_passive_water_sample",
      molecule_type: "amplicon_dna",
      analysis_goal: "biodiversity_metabarcoding",
      input_format: "fastq",
      library_mode: "amplicon",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "wetland_health",
    status: "track_exact",
    track: "edna"
  },
  {
    name: "listeria_bam",
    answers: {
      category: "food_safety",
      sample_type: "food_safety_sample",
      molecule_type: "dna",
      analysis_goal: "target_enrichment_and_listeria_recovery",
      input_format: "bam",
      library_mode: "adaptive_sampling",
      multiplexing: "yes",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "listeria_adaptive_sampling",
    status: "exact"
  },
  {
    name: "amr_isolate",
    answers: {
      category: "clinical_isolates_plasmids",
      sample_type: "bacterial_isolate",
      molecule_type: "dna",
      analysis_goal: "clinical_amr_profiling",
      input_format: "fast5",
      library_mode: "standard_isolate",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "prefer_hac",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "amr_nanopore",
    status: "exact"
  },
  {
    name: "cre_plasmid",
    answers: {
      category: "clinical_isolates_plasmids",
      sample_type: "bacterial_isolate",
      molecule_type: "dna",
      analysis_goal: "plasmid_clustering",
      input_format: "pod5",
      library_mode: "rbk114_24",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "prefer_sup",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "cre_plasmid_clustering",
    status: "exact"
  },
  {
    name: "amr_host_association",
    answers: {
      category: "clinical_isolates_plasmids",
      sample_type: "clinical_metagenome",
      molecule_type: "dna",
      analysis_goal: "amr_host_association",
      input_format: "pod5",
      library_mode: "barcoded_metagenome",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "raw_signal_not_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "nanopore_amr_host_association",
    status: "exact"
  },
  {
    name: "aiv_direct_rna",
    answers: {
      category: "veterinary_zoonotic_surveillance",
      sample_type: "avian_influenza_sample",
      molecule_type: "rna",
      analysis_goal: "aiv_consensus_subtyping_phylogeny",
      input_format: "pod5",
      library_mode: "direct_rna004",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "raw_signal_not_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "avian_influenza_profiling",
    status: "exact"
  },
  {
    name: "feather_to_fur",
    answers: {
      category: "veterinary_zoonotic_surveillance",
      sample_type: "cross_host_aiv_pair",
      molecule_type: "viral_reads_or_variants",
      analysis_goal: "cross_host_variant_tracking",
      input_format: "fastq_and_vcf",
      library_mode: "standard_isolate",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "already_basecalled",
      preprocessing_state: "already_trimmed_and_filtered"
    },
    pipeline: "from_feather_to_fur",
    status: "exact"
  },
  {
    name: "viability_signal",
    answers: {
      category: "viability_assessment",
      sample_type: "raw_signal",
      molecule_type: "raw_signal",
      analysis_goal: "viability_inference",
      input_format: "pod5",
      library_mode: "signal_only",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "not_applicable",
      preprocessing_state: "unsure"
    },
    pipeline: "squiggle4viability",
    status: "exact"
  },
  {
    name: "soil_unsupported",
    answers: {
      category: "environmental_metagenomics",
      sample_type: "soil",
      molecule_type: "dna",
      analysis_goal: "community_profiling",
      input_format: "fastq",
      library_mode: "rbk114_24",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "already_basecalled",
      preprocessing_state: "already_trimmed_and_filtered"
    },
    pipeline: "air_metagenomics",
    status: "unsupported",
    confidence: "low"
  }
];

for (const testCase of cases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: no recommendation returned`);
  assert(result.primary.pipeline.id === testCase.pipeline, `${testCase.name}: expected ${testCase.pipeline}, got ${result.primary.pipeline.id}`);
  assert(result.status === testCase.status, `${testCase.name}: expected status ${testCase.status}, got ${result.status}`);
  if (testCase.track) {
    assert(result.primary.track && result.primary.track.id === testCase.track, `${testCase.name}: expected track ${testCase.track}`);
  }
  if (testCase.confidence) {
    assert(result.confidence === testCase.confidence, `${testCase.name}: expected confidence ${testCase.confidence}, got ${result.confidence}`);
  }
  assert(result.primary.entryActions.length > 0, `${testCase.name}: expected at least one action`);
}

console.log("selector cases ok");
