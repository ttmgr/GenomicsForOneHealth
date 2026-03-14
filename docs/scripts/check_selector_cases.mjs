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
  expertRules: readJson("expert_rules.json"),
  nanoporeProfiles: readJson("nanopore_profiles.json"),
  externalWorkflows: readJson("external_workflows.json")
};

const exactCases = [
  {
    name: "environmental_air_taxonomy",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "taxonomy_profiling",
      example_context: "air_bioaerosol_example"
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
      example_context: "wetland_passive_water_example"
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
      example_context: "wetland_rna_virome_example"
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
      example_context: "wetland_edna_example"
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
      example_context: "zambia_water_edna_example"
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
      example_context: "amr_nanopore_example"
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
      example_context: "cre_plasmid_example"
    },
    pipeline: "cre_plasmid_clustering",
    status: "exact"
  },
  {
    name: "clinical_metagenome_host_association",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "clinical_metagenome",
      target_goal: "amr_host_association"
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
      target_goal: "listeria_target_recovery"
    },
    pipeline: "listeria_adaptive_sampling",
    status: "exact",
    requiresExamplePage: false
  }
];

for (const testCase of exactCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: expected a recommendation`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected ${testCase.pipeline}, got ${result.backend.pipeline.id}`);
  assert(result.status === testCase.status, `${testCase.name}: expected status ${testCase.status}, got ${result.status}`);
  if (testCase.track) {
    assert(result.backend.track?.id === testCase.track, `${testCase.name}: expected track ${testCase.track}`);
  }
  if (testCase.requiresExamplePage === false) {
    assert(!needsExampleSelection(testCase.answers, datasets), `${testCase.name}: example page should be skipped`);
    assert(!getWizardPageSequence(datasets.questionSpec, testCase.answers, datasets).includes("example"), `${testCase.name}: example page should not appear in the sequence`);
  }
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
    pipeline: "air_metagenomics",
    externalIds: ["epi2me_metagenomics", "cz_id_long_read_metagenomics"]
  },
  {
    name: "other_environmental_matrix",
    answers: {
      sample_context: "environmental",
      material_class: "long_read_metagenomic_dna",
      target_goal: "functional_profiling",
      example_context: "other_environmental_unsupported_example"
    },
    pipeline: "air_metagenomics",
    externalIds: ["epi2me_metagenomics", "cz_id_long_read_metagenomics"]
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
    track: "rna_virome",
    externalIds: ["cz_id_long_read_metagenomics"]
  },
  {
    name: "other_edna_context",
    answers: {
      sample_context: "environmental",
      material_class: "edna_12s_amplicon",
      target_goal: "host_range_inference",
      example_context: "other_edna_unsupported_example"
    },
    pipeline: "zambia_edna",
    externalIds: ["epi2me_amplicon"]
  },
  {
    name: "other_single_isolate",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "single_isolate_long_read_dna",
      target_goal: "annotation",
      example_context: "other_single_isolate_example"
    },
    pipeline: "amr_nanopore",
    externalIds: ["epi2me_bacterial_genomes"]
  },
  {
    name: "other_barcoded_isolate",
    answers: {
      sample_context: "clinical_isolate",
      material_class: "barcoded_isolate_long_read_dna",
      target_goal: "phylogenetics_outbreak_tracking",
      example_context: "other_barcoded_isolate_example"
    },
    pipeline: "cre_plasmid_clustering",
    externalIds: ["epi2me_bacterial_genomes"]
  }
];

for (const testCase of unsupportedCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: expected a recommendation`);
  assert(result.status === "unsupported", `${testCase.name}: expected unsupported status`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected nearest pipeline ${testCase.pipeline}`);
  if (testCase.track) {
    assert(result.backend.track?.id === testCase.track, `${testCase.name}: expected nearest track ${testCase.track}`);
  }
  for (const workflowId of testCase.externalIds) {
    assert(result.external_fallbacks.some((workflow) => workflow.id === workflowId), `${testCase.name}: missing external fallback ${workflowId}`);
  }
}

const multiExampleAnswers = {
  sample_context: "environmental",
  material_class: "long_read_metagenomic_dna",
  target_goal: "taxonomy_profiling"
};

assert(needsExampleSelection(multiExampleAnswers, datasets), "environmental long-read DNA should require example selection");
assert(getWizardPageSequence(datasets.questionSpec, multiExampleAnswers, datasets).includes("example"), "example page should appear when multiple contexts fit");

const shortReadAssemblyResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "mag_recovery",
    example_context: "wetland_passive_water_example",
    median_read_length_below_1000: "yes"
  },
  datasets
);

assert(shortReadAssemblyResult.preferred_tool_override?.to === "nanoMDBG", "short metagenomic reads should trigger the nanoMDBG heuristic");

const normalAssemblyResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "mag_recovery",
    example_context: "wetland_passive_water_example",
    median_read_length_below_1000: "no"
  },
  datasets
);

assert(!normalAssemblyResult.preferred_tool_override, "nanoMDBG should not be preferred when median read length is not below 1000 bp");

const barcodedSetupResult = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "barcoded_isolate_long_read_dna",
    target_goal: "plasmid_reconstruction",
    example_context: "cre_plasmid_example",
    library_mode: "rbk114_24"
  },
  datasets
);

assert(barcodedSetupResult.entry_actions.some((action) => action.title.includes("Demultiplex")), "barcoded kits should insert a demultiplexing action");
assert(barcodedSetupResult.expert_effects.some((effect) => effect.title.includes("demultiplexing")), "barcoded kits should surface a demultiplexing heuristic");

const basecallingResult = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "single_isolate_long_read_dna",
    target_goal: "complete_genome_assembly",
    example_context: "amr_nanopore_example",
    basecalling_goal: "already_basecalled"
  },
  datasets
);

assert(basecallingResult.expert_effects.some((effect) => effect.title.includes("Skip upstream basecalling")), "already-basecalled routes should suppress basecalling insertion");
assert(!basecallingResult.entry_actions[0].title.includes("Basecall"), "already-basecalled routes should not prepend a basecalling action");

const lskResult = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "single_isolate_long_read_dna",
    target_goal: "complete_genome_assembly",
    example_context: "amr_nanopore_example",
    library_mode: "lsk114"
  },
  datasets
);

assert(lskResult.warnings.some((warning) => warning.title === "Single-isolate ligation framing"), "LSK114 should reinforce single-isolate framing");

const minionResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    flowcell_family: "minion_r10_4_1"
  },
  datasets
);

assert(minionResult.setup_summary.recommendation.includes("MinION R10.4.1"), "MinION should appear in the setup recommendation");

const promethionResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    flowcell_family: "promethion_r10_4_1"
  },
  datasets
);

assert(promethionResult.warnings.some((warning) => warning.title === "PromethION depth framing"), "PromethION should trigger deep-run framing");

const fastBasecallingResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    basecalling_goal: "real_time_fast"
  },
  datasets
);

assert(fastBasecallingResult.setup_summary.recommendation.includes("FAST"), "FAST basecalling should appear in the setup recommendation");

const hacResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example",
    basecalling_goal: "balanced_hac"
  },
  datasets
);

assert(hacResult.setup_summary.recommendation.includes("HAC"), "HAC should appear in the setup recommendation");

const supResult = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "single_isolate_long_read_dna",
    target_goal: "complete_genome_assembly",
    example_context: "amr_nanopore_example",
    basecalling_goal: "max_accuracy_sup"
  },
  datasets
);

assert(supResult.setup_summary.recommendation.includes("SUP"), "SUP should appear in the setup recommendation");

console.log("Selector smoke tests passed.");
