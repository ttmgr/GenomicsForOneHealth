import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const docsDir = path.resolve(__dirname, "..");
const dataDir = path.join(docsDir, "data");
const require = createRequire(import.meta.url);
const selectorEngine = require(path.join(docsDir, "selector-engine.js"));

const {
  needsExampleSelection,
  getWizardPageSequence,
  computeRecommendation
} = selectorEngine;

function readJson(filename) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, filename), "utf8"));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const datasets = {
  questionSpec: readJson("questions.json"),
  pipelines: readJson("pipelines.json"),
  playbooks: readJson("playbooks.json"),
  examples: readJson("examples.json"),
  expertRules: readJson("expert_rules.json")
};

const exactCases = [
  {
    name: "environmental_air_taxonomy",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "taxonomy_profiling",
      example_context: "air_bioaerosol_example",
      input_format: "pod5",
      basecalling_state: "raw_signal_not_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "air_metagenomics",
    status: "exact"
  },
  {
    name: "wetland_dna_mag",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "mag_recovery",
      example_context: "wetland_passive_water_example",
      library_mode: "nbd114_24",
      demultiplexing: "already_done",
      input_format: "fastq",
      basecalling_state: "already_basecalled",
      preprocessing_state: "need_trim_and_filter"
    },
    pipeline: "wetland_health",
    track: "dna_metagenomics",
    status: "track_exact"
  },
  {
    name: "wetland_rna_virome",
    answers: {
      sample_context: "environmental",
      material_class: "rna_virome_material",
      target_goal: "viral_discovery",
      example_context: "wetland_rna_virome_example",
      input_format: "fastq",
      basecalling_state: "already_basecalled"
    },
    pipeline: "wetland_health",
    track: "rna_virome",
    status: "track_exact"
  },
  {
    name: "wetland_edna",
    answers: {
      sample_context: "environmental",
      material_class: "edna_12s_amplicon",
      target_goal: "biodiversity_metabarcoding",
      example_context: "wetland_edna_example",
      library_mode: "amplicon_workflow",
      input_format: "fastq",
      demultiplexing: "needed"
    },
    pipeline: "wetland_health",
    track: "edna",
    status: "track_exact"
  },
  {
    name: "zambia_edna",
    answers: {
      sample_context: "environmental",
      material_class: "edna_12s_amplicon",
      target_goal: "biodiversity_metabarcoding",
      example_context: "zambia_water_edna_example",
      library_mode: "amplicon_workflow",
      input_format: "fastq"
    },
    pipeline: "zambia_edna",
    status: "exact"
  },
  {
    name: "single_isolate_amr",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "single_isolate_long_read_dna",
      target_goal: "complete_genome_assembly",
      example_context: "amr_nanopore_example",
      library_mode: "lsk114",
      input_format: "pod5",
      basecalling_state: "prefer_sup"
    },
    pipeline: "amr_nanopore",
    status: "exact"
  },
  {
    name: "barcoded_isolate_cre",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "barcoded_isolate_long_read_dna",
      target_goal: "plasmid_reconstruction",
      example_context: "cre_plasmid_example",
      library_mode: "rbk114_24",
      input_format: "pod5",
      demultiplexing: "needed",
      basecalling_state: "prefer_sup"
    },
    pipeline: "cre_plasmid_clustering",
    status: "exact"
  },
  {
    name: "host_association_unique_example",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "clinical_metagenome",
      target_goal: "amr_host_association",
      library_mode: "barcoded_metagenome",
      input_format: "pod5",
      demultiplexing: "needed",
      basecalling_state: "raw_signal_not_basecalled"
    },
    pipeline: "nanopore_amr_host_association",
    status: "exact",
    requiresExamplePage: false
  },
  {
    name: "food_safety_listeria",
    answers: {
      sample_context: "food_safety",
      material_class: "listeria_enrichment_material",
      target_goal: "listeria_target_recovery",
      library_mode: "adaptive_sampling",
      input_format: "bam",
      basecalling_state: "already_basecalled"
    },
    pipeline: "listeria_adaptive_sampling",
    status: "exact",
    requiresExamplePage: false
  }
];

for (const testCase of exactCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: no recommendation returned`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected ${testCase.pipeline}, got ${result.backend.pipeline.id}`);
  assert(result.status === testCase.status, `${testCase.name}: expected status ${testCase.status}, got ${result.status}`);
  if (testCase.track) {
    assert(result.backend.track?.id === testCase.track, `${testCase.name}: expected track ${testCase.track}`);
  }
  if (testCase.requiresExamplePage === false) {
    assert(!needsExampleSelection(testCase.answers, datasets), `${testCase.name}: example page should be skipped`);
    assert(!getWizardPageSequence(datasets.questionSpec, testCase.answers, datasets).includes("example"), `${testCase.name}: example page should not be in wizard sequence`);
  }
  assert(result.entry_actions.length > 0, `${testCase.name}: expected at least one entry action`);
}

const unsupportedCases = [
  {
    name: "soil_unsupported",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "taxonomy_profiling",
      example_context: "soil_unsupported_example"
    },
    pipeline: "air_metagenomics"
  },
  {
    name: "other_environmental_matrix",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "functional_profiling",
      example_context: "other_environmental_unsupported_example"
    },
    pipeline: "air_metagenomics"
  },
  {
    name: "other_environmental_virome",
    answers: {
      sample_context: "environmental",
      material_class: "rna_virome_material",
      target_goal: "viral_discovery",
      example_context: "other_environmental_virome_unsupported_example"
    },
    pipeline: "wetland_health",
    track: "rna_virome"
  },
  {
    name: "other_edna_context",
    answers: {
      sample_context: "environmental",
      material_class: "edna_12s_amplicon",
      target_goal: "host_range_inference",
      example_context: "other_edna_unsupported_example"
    },
    pipeline: "zambia_edna"
  },
  {
    name: "other_single_isolate",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "single_isolate_long_read_dna",
      target_goal: "annotation",
      example_context: "other_single_isolate_example"
    },
    pipeline: "amr_nanopore"
  },
  {
    name: "other_barcoded_isolate",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "barcoded_isolate_long_read_dna",
      target_goal: "phylogenetics_outbreak_tracking",
      example_context: "other_barcoded_isolate_example"
    },
    pipeline: "cre_plasmid_clustering"
  }
];

for (const testCase of unsupportedCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: no recommendation returned`);
  assert(result.status === "unsupported", `${testCase.name}: expected unsupported status`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected nearest pipeline ${testCase.pipeline}`);
  if (testCase.track) {
    assert(result.backend.track?.id === testCase.track, `${testCase.name}: expected nearest track ${testCase.track}`);
  }
}

const multiExampleAnswers = {
  sample_context: "environmental",
  material_class: "long_read_metagenomic_dna",
  target_goal: "taxonomy_profiling"
};
assert(needsExampleSelection(multiExampleAnswers, datasets), "Environmental long-read DNA should require the example page");
assert(getWizardPageSequence(datasets.questionSpec, multiExampleAnswers, datasets).includes("example"), "Environmental long-read DNA should include the example page");

const nanoMdbgCase = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "mag_recovery",
    example_context: "wetland_passive_water_example",
    median_read_length_below_1000: "yes",
    input_format: "fastq",
    basecalling_state: "already_basecalled"
  },
  datasets
);
assert(nanoMdbgCase.expert_effects.some((effect) => effect.title.includes("nanoMDBG")), "Short-read environmental assembly should trigger the nanoMDBG override");
assert(nanoMdbgCase.preprocessing.additional_preprocessing.includes("nanoMDBG"), "Short-read environmental assembly should mention nanoMDBG in preprocessing");

const noNanoMdbgCase = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "mag_recovery",
    example_context: "wetland_passive_water_example",
    median_read_length_below_1000: "no",
    input_format: "fastq",
    basecalling_state: "already_basecalled"
  },
  datasets
);
assert(!noNanoMdbgCase.preprocessing.additional_preprocessing.includes("nanoMDBG"), "Longer-read environmental assembly should not force the nanoMDBG override");
assert(noNanoMdbgCase.backend.pipeline.id === nanoMdbgCase.backend.pipeline.id, "Expert heuristics must not change the selected backend");

const rawSignalCase = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    input_format: "pod5",
    basecalling_state: "raw_signal_not_basecalled"
  },
  datasets
);
assert(rawSignalCase.entry_actions.some((action) => action.id === "generic_basecalling"), "Raw signal should insert a basecalling step");

const alreadyBasecalledCase = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    input_format: "fastq",
    basecalling_state: "already_basecalled"
  },
  datasets
);
assert(!alreadyBasecalledCase.entry_actions.some((action) => action.id === "generic_basecalling"), "Already-basecalled input should suppress generic basecalling");

const demuxCase = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "barcoded_isolate_long_read_dna",
    target_goal: "plasmid_reconstruction",
    example_context: "cre_plasmid_example",
    library_mode: "rbk114_24",
    demultiplexing: "needed"
  },
  datasets
);
assert(demuxCase.entry_actions.some((action) => action.id === "generic_demultiplexing"), "Barcoded pooled input should insert demultiplexing");

const trimmedCase = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    preprocessing_state: "already_trimmed_and_filtered"
  },
  datasets
);
assert(!trimmedCase.entry_actions.some((action) => action.id === "generic_read_cleaning"), "Already-trimmed reads should suppress generic cleaning");
assert(trimmedCase.warnings.some((warning) => warning.title.includes("Suppress early read-cleaning steps")), "Already-trimmed reads should add a compatibility warning");

console.log("selector cases ok");
