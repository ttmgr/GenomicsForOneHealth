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

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const datasets = {
  pipelines: readJson("pipelines.json"),
  questionSpec: readJson("questions.json"),
  playbooks: readJson("playbooks.json"),
  presets: readJson("presets.json"),
  outOfScopeRules: readJson("out_of_scope.json")
};

const cases = [
  {
    name: "env_air_rbk",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "rbk114_24",
      analysis_goal: "taxonomy_profiling",
      sample_type: "air_bioaerosol",
      input_format: "pod5",
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
    name: "wetland_dna_nbd",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "nbd114_24",
      analysis_goal: "mag_recovery",
      sample_type: "wetland_or_passive_water_sample",
      input_format: "fastq",
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
    name: "wetland_rna_rbk",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "rbk114_24",
      analysis_goal: "rna_virome",
      sample_type: "wetland_or_passive_water_sample",
      input_format: "fastq",
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
    name: "wetland_edna_amplicon",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "amplicon_workflow",
      analysis_goal: "edna_12s_biodiversity",
      sample_type: "wetland_or_passive_water_sample",
      input_format: "fastq",
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
    name: "zambia_edna_amplicon",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "amplicon_workflow",
      analysis_goal: "edna_12s_biodiversity",
      sample_type: "edna_water_sample",
      input_format: "fastq",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "zambia_edna",
    status: "exact"
  },
  {
    name: "clinical_single_isolate_lsk",
    answers: {
      sequencing_context: "clinical_isolate",
      library_mode: "lsk114",
      analysis_goal: "complete_genome_assembly",
      sample_type: "bacterial_isolate",
      input_format: "pod5",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "prefer_sup",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "amr_nanopore",
    status: "exact"
  },
  {
    name: "clinical_barcoded_isolate_rbk",
    answers: {
      sequencing_context: "clinical_isolate",
      library_mode: "rbk114_24",
      analysis_goal: "plasmid_reconstruction",
      sample_type: "bacterial_isolate",
      input_format: "pod5",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "prefer_sup",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "cre_plasmid_clustering",
    status: "exact"
  },
  {
    name: "clinical_host_association",
    answers: {
      sequencing_context: "clinical_isolate",
      library_mode: "barcoded_metagenome",
      analysis_goal: "amr_host_association",
      sample_type: "clinical_metagenome",
      input_format: "pod5",
      multiplexing: "yes",
      demultiplexing: "needed",
      basecalling_state: "raw_signal_not_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "nanopore_amr_host_association",
    status: "exact"
  },
  {
    name: "food_listeria_adaptive_sampling",
    answers: {
      sequencing_context: "food_safety",
      library_mode: "adaptive_sampling",
      analysis_goal: "listeria_target_recovery",
      sample_type: "food_safety_sample",
      input_format: "bam",
      multiplexing: "unsure",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "listeria_adaptive_sampling",
    status: "exact"
  },
  {
    name: "soil_unsupported",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "rbk114_24",
      analysis_goal: "taxonomy_profiling",
      sample_type: "soil",
      input_format: "fastq",
      multiplexing: "yes",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "already_trimmed_and_filtered"
    },
    pipeline: "air_metagenomics",
    status: "unsupported",
    confidence: "low"
  },
  {
    name: "clinical_metagenome_non_host_route",
    answers: {
      sequencing_context: "clinical_isolate",
      library_mode: "rbk114_24",
      analysis_goal: "amr_virulence_profiling",
      sample_type: "clinical_metagenome",
      input_format: "fastq",
      multiplexing: "yes",
      demultiplexing: "already_done",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "nanopore_amr_host_association",
    status: "unsupported"
  },
  {
    name: "food_general_case_unsupported",
    answers: {
      sequencing_context: "food_safety",
      library_mode: "standard_control",
      analysis_goal: "unsure",
      sample_type: "food_safety_sample",
      input_format: "fastq",
      multiplexing: "unsure",
      demultiplexing: "unsure",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "listeria_adaptive_sampling",
    status: "unsupported"
  },
  {
    name: "multiplex_override_does_not_reroute",
    answers: {
      sequencing_context: "environmental_metagenomics",
      library_mode: "rbk114_24",
      analysis_goal: "taxonomy_profiling",
      sample_type: "air_bioaerosol",
      input_format: "pod5",
      multiplexing: "no",
      demultiplexing: "not_needed",
      basecalling_state: "prefer_hac",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "air_metagenomics",
    status: "exact"
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
