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
  externalWorkflows: readJson("external_workflows.json"),
  matrixProfiles: readJson("matrix_profiles.json")
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
    status: "exact",
    matrix: "air_aerobiome"
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
    status: "track_exact",
    matrix: "wetland_passive_water_metagenomics"
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
    status: "track_exact",
    matrix: "environmental_rna_virome"
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
    status: "track_exact",
    matrix: "edna_12s_water"
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
    status: "exact",
    matrix: "edna_12s_water"
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
    status: "exact",
    matrix: "single_isolate_long_read"
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
    status: "exact",
    matrix: "barcoded_isolate_long_read"
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
    matrix: "clinical_metagenome_host_association",
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
    matrix: "food_safety_target_recovery",
    requiresExamplePage: false
  }
];

for (const testCase of exactCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: expected a recommendation`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected ${testCase.pipeline}, got ${result.backend.pipeline.id}`);
  assert(result.status === testCase.status, `${testCase.name}: expected status ${testCase.status}, got ${result.status}`);
  assert(result.matrix_profile?.id === testCase.matrix, `${testCase.name}: expected matrix profile ${testCase.matrix}`);
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
    externalIds: ["epi2me_metagenomics", "cz_id_long_read_metagenomics"],
    matrix: "soil_long_read_metagenomics"
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
    externalIds: ["epi2me_metagenomics", "cz_id_long_read_metagenomics"],
    matrix: "other_environmental_long_read"
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
    externalIds: ["cz_id_long_read_metagenomics"],
    matrix: "environmental_rna_virome"
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
    externalIds: ["epi2me_amplicon"],
    matrix: "edna_12s_water"
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
    externalIds: ["epi2me_bacterial_genomes"],
    matrix: "single_isolate_long_read"
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
    externalIds: ["epi2me_bacterial_genomes"],
    matrix: "barcoded_isolate_long_read"
  }
];

for (const testCase of unsupportedCases) {
  const result = computeRecommendation(testCase.answers, datasets);
  assert(result, `${testCase.name}: expected a recommendation`);
  assert(result.status === "unsupported", `${testCase.name}: expected unsupported status`);
  assert(result.backend.pipeline.id === testCase.pipeline, `${testCase.name}: expected nearest pipeline ${testCase.pipeline}`);
  assert(result.matrix_profile?.id === testCase.matrix, `${testCase.name}: expected matrix profile ${testCase.matrix}`);
  assert(result.literature_links.length > 0, `${testCase.name}: expected literature links`);
  if (testCase.track) {
    assert(result.backend.track?.id === testCase.track, `${testCase.name}: expected nearest track ${testCase.track}`);
  }
  for (const workflowId of testCase.externalIds) {
    assert(result.external_fallbacks.some((workflow) => workflow.id === workflowId), `${testCase.name}: missing external fallback ${workflowId}`);
  }
  const sortedIds = result.external_fallbacks.slice(0, testCase.externalIds.length).map((workflow) => workflow.id);
  assert(JSON.stringify(sortedIds) === JSON.stringify(testCase.externalIds), `${testCase.name}: expected fallback order ${testCase.externalIds.join(", ")}`);
  assert(result.guide_links.some((link) => link.url.includes(`#${result.matrix_profile.guide_section_id}`)), `${testCase.name}: expected anchored guide link`);
}

const multiExampleAnswers = {
  sample_context: "environmental",
  material_class: "long_read_metagenomic_dna",
  target_goal: "taxonomy_profiling"
};

assert(needsExampleSelection(multiExampleAnswers, datasets), "environmental long-read DNA should require example selection");
assert(getWizardPageSequence(datasets.questionSpec, multiExampleAnswers, datasets).includes("example"), "example page should appear when multiple contexts fit");

const airResult = computeRecommendation(
  {
    sample_context: "environmental",
    material_class: "long_read_metagenomic_dna",
    target_goal: "taxonomy_profiling",
    example_context: "air_bioaerosol_example"
  },
  datasets
);

assert(airResult.matrix_notes.summary.toLowerCase().includes("low-biomass"), "air result should include low-biomass matrix framing");
assert(airResult.literature_links.length >= 1, "air result should expose literature links");

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

const clinicalMatrixResult = computeRecommendation(
  {
    sample_context: "clinical_isolate",
    material_class: "clinical_metagenome",
    target_goal: "amr_host_association"
  },
  datasets
);

assert(clinicalMatrixResult.matrix_notes.warnings.some((warning) => warning.includes("Plasma")), "clinical metagenome result should mention plasma guide-only variants");
assert(clinicalMatrixResult.external_fallbacks[0].id === "cz_id_long_read_metagenomics", "clinical metagenome alternatives should prioritize CZ ID");

console.log("Selector smoke tests passed.");
