import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.resolve(__dirname, "../data");

function readJson(filename) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, filename), "utf8"));
}

function fail(message) {
  throw new Error(message);
}

const pipelines = readJson("pipelines.json");
const playbooks = readJson("playbooks.json");
const questions = readJson("questions.json");
const examples = readJson("examples.json");
const expertRules = readJson("expert_rules.json");
const nanoporeProfiles = readJson("nanopore_profiles.json");
const externalWorkflows = readJson("external_workflows.json");
const matrixProfiles = readJson("matrix_profiles.json");

const expectedPageIds = [
  "sample",
  "material",
  "target",
  "example",
  "setup",
  "kit",
  "flowcell",
  "basecalling",
  "analysis",
  "conditions",
  "results"
];

const allowedPageTypes = new Set(["route", "conditional_route", "info", "setup", "conditions", "results"]);
const allowedExampleStatuses = new Set(["exact", "unsupported_nearest"]);
const allowedRuleEffects = new Set(["tool_swap", "step_insert", "step_skip", "warning_only", "preprocessing_override"]);
const allowedWorkflowCompat = new Set(["exact", "unsupported"]);
const allowedWorkflowSources = new Set(["ont_curated", "cloud"]);
const allowedMatrixScopes = new Set(["route_attached", "guide_only"]);

if (!Array.isArray(questions.pages)) {
  fail("questions.json must define a top-level pages array");
}

const pagesById = new Map();
const questionsById = new Map();
const questionOrder = [];
const optionSets = new Map();

for (const page of questions.pages) {
  if (!page.id || !page.title || !page.summary || !page.page_type) {
    fail(`Question page ${page.id || "<unknown>"} is missing metadata`);
  }
  if (!allowedPageTypes.has(page.page_type)) {
    fail(`Question page ${page.id} uses unsupported page_type ${page.page_type}`);
  }
  if (pagesById.has(page.id)) {
    fail(`Duplicate question page id ${page.id}`);
  }
  if (!Array.isArray(page.questions)) {
    fail(`Question page ${page.id} must define a questions array`);
  }

  pagesById.set(page.id, page);
  for (const question of page.questions) {
    if (!question.id || !question.field || !question.label) {
      fail(`Question in page ${page.id} is missing required fields`);
    }
    if (questionsById.has(question.id)) {
      fail(`Duplicate question id ${question.id}`);
    }
    questionsById.set(question.id, question);
    questionOrder.push(question.id);
    optionSets.set(question.id, new Set((question.options || []).map((option) => option.value)));
  }
}

if (JSON.stringify(expectedPageIds) !== JSON.stringify(questions.pages.map((page) => page.id))) {
  fail(`questions.json pages must match the expected order: ${expectedPageIds.join(", ")}`);
}

function validateVisibilityDependency(ownerLabel, visibleWhen, currentQuestionId, options = {}) {
  if (!visibleWhen) {
    return;
  }

  const { allowUnknownDependencies = false } = options;

  for (const [dependencyId, acceptedValues] of Object.entries(visibleWhen)) {
    if (!questionsById.has(dependencyId)) {
      if (allowUnknownDependencies) {
        continue;
      }
      fail(`${ownerLabel} references unknown question ${dependencyId}`);
    }
    if (!Array.isArray(acceptedValues) || acceptedValues.length === 0) {
      fail(`${ownerLabel} must include accepted values for ${dependencyId}`);
    }

    if (currentQuestionId) {
      const dependencyIndex = questionOrder.indexOf(dependencyId);
      const currentIndex = questionOrder.indexOf(currentQuestionId);
      if (dependencyIndex >= currentIndex) {
        fail(`${ownerLabel} depends on ${dependencyId}, which is not earlier in the wizard`);
      }
    }

    const allowedValues = optionSets.get(dependencyId);
    for (const acceptedValue of acceptedValues) {
      if (allowedValues.size > 0 && !allowedValues.has(acceptedValue)) {
        fail(`${ownerLabel} references invalid option ${dependencyId}:${acceptedValue}`);
      }
    }
  }
}

for (const question of questionsById.values()) {
  validateVisibilityDependency(`Question ${question.id}`, question.visible_when, question.id);

  if (question.dynamic_options_from) {
    if (question.dynamic_options_from !== "examples") {
      fail(`Question ${question.id} uses unsupported dynamic source ${question.dynamic_options_from}`);
    }
    continue;
  }

  if (!Array.isArray(question.options) || question.options.length === 0) {
    fail(`Question ${question.id} must define options or a dynamic source`);
  }

  for (const option of question.options) {
    if (!option.value || !option.label) {
      fail(`Question ${question.id} has an incomplete option`);
    }
    validateVisibilityDependency(`Question ${question.id} option ${option.value}`, option.visible_when, question.id);
  }
}

const pipelineIds = new Set(pipelines.map((pipeline) => pipeline.id));
const trackIdsByPipeline = new Map(
  pipelines.map((pipeline) => [pipeline.id, new Set((pipeline.track_notes || []).map((track) => track.id))])
);

for (const pipeline of pipelines) {
  for (const field of [
    "id",
    "title",
    "short_title",
    "category",
    "sample_types",
    "analysis_goals",
    "library_modes",
    "supported_entry_points",
    "default_preprocessing",
    "primary_docs",
    "setup_docs",
    "closest_alternatives",
    "track_notes"
  ]) {
    if (!(field in pipeline)) {
      fail(`Pipeline ${pipeline.id} is missing required field ${field}`);
    }
  }

  for (const link of [...pipeline.primary_docs, ...pipeline.setup_docs]) {
    if (!link.label || !link.url) {
      fail(`Pipeline ${pipeline.id} contains an incomplete documentation link`);
    }
  }

  for (const alternativeId of pipeline.closest_alternatives) {
    if (!pipelineIds.has(alternativeId)) {
      fail(`Pipeline ${pipeline.id} references unknown closest alternative ${alternativeId}`);
    }
  }
}

for (const playbook of playbooks) {
  for (const field of [
    "pipeline_id",
    "track_id",
    "example_badge",
    "route_summary",
    "entry_actions",
    "curated_commands",
    "preprocessing_defaults",
    "required_tools",
    "required_databases",
    "evidence_links"
  ]) {
    if (!(field in playbook)) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} is missing ${field}`);
    }
  }

  if (!pipelineIds.has(playbook.pipeline_id)) {
    fail(`Playbook references unknown pipeline ${playbook.pipeline_id}`);
  }

  if (playbook.track_id !== null && !trackIdsByPipeline.get(playbook.pipeline_id).has(playbook.track_id)) {
    fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} references an unknown track`);
  }

  for (const action of playbook.entry_actions) {
    if (!action.id || !action.title || !action.summary || !action.entry_file || !action.doc_url) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} has an incomplete entry action`);
    }
  }

  for (const command of playbook.curated_commands) {
    if (!command.label || !command.command || !command.source_url) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} has an incomplete curated command`);
    }
    validateVisibilityDependency(
      `Curated command ${playbook.pipeline_id}/${playbook.track_id}`,
      command.when,
      null,
      { allowUnknownDependencies: true }
    );
  }

  for (const link of playbook.evidence_links) {
    if (!link.label || !link.url) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} has an incomplete evidence link`);
    }
  }
}

const exampleIds = new Set();
for (const example of examples) {
  exampleIds.add(example.id);
  for (const field of [
    "id",
    "label",
    "sample_contexts",
    "material_classes",
    "target_goals",
    "status_class",
    "route_summary",
    "selection_help"
  ]) {
    if (!(field in example)) {
      fail(`Example ${example.id || "<unknown>"} is missing ${field}`);
    }
  }

  if (!allowedExampleStatuses.has(example.status_class)) {
    fail(`Example ${example.id} uses unsupported status_class ${example.status_class}`);
  }

  for (const [questionId, values] of [
    ["sample_context", example.sample_contexts],
    ["material_class", example.material_classes],
    ["target_goal", example.target_goals]
  ]) {
    if (!Array.isArray(values) || values.length === 0) {
      fail(`Example ${example.id} must define values for ${questionId}`);
    }
    const allowedValues = optionSets.get(questionId);
    for (const value of values) {
      if (!allowedValues.has(value)) {
        fail(`Example ${example.id} references invalid ${questionId}:${value}`);
      }
    }
  }

  if (example.status_class === "exact") {
    if (!example.pipeline_id || !pipelineIds.has(example.pipeline_id)) {
      fail(`Exact example ${example.id} must resolve to a known pipeline`);
    }
    if (example.track_id !== null && !trackIdsByPipeline.get(example.pipeline_id).has(example.track_id)) {
      fail(`Exact example ${example.id} references an unknown track`);
    }
  } else {
    if (!example.nearest_pipeline_id || !pipelineIds.has(example.nearest_pipeline_id)) {
      fail(`Unsupported example ${example.id} must define a known nearest_pipeline_id`);
    }
    if (!example.unsupported_reason) {
      fail(`Unsupported example ${example.id} must include an unsupported_reason`);
    }
    if (example.nearest_track_id !== null && !trackIdsByPipeline.get(example.nearest_pipeline_id).has(example.nearest_track_id)) {
      fail(`Unsupported example ${example.id} references an unknown nearest track`);
    }
  }
}

if (!Array.isArray(matrixProfiles) || matrixProfiles.length === 0) {
  fail("matrix_profiles.json must define a non-empty array");
}

const matrixProfileIds = new Set();
const guideSectionIds = new Set();
const externalWorkflowIds = new Set(externalWorkflows.map((workflow) => workflow.id));

for (const profile of matrixProfiles) {
  for (const field of [
    "id",
    "label",
    "scope",
    "applies_to",
    "selector_summary",
    "selector_warnings",
    "setup_biases",
    "fallback_workflow_ids",
    "guide_section_id",
    "citations",
    "guide_highlights",
    "what_this_changes"
  ]) {
    if (!(field in profile)) {
      fail(`Matrix profile ${profile.id || "<unknown>"} is missing ${field}`);
    }
  }

  if (!allowedMatrixScopes.has(profile.scope)) {
    fail(`Matrix profile ${profile.id} uses unsupported scope ${profile.scope}`);
  }
  if (matrixProfileIds.has(profile.id)) {
    fail(`Duplicate matrix profile id ${profile.id}`);
  }
  if (guideSectionIds.has(profile.guide_section_id)) {
    fail(`Duplicate matrix guide section id ${profile.guide_section_id}`);
  }

  matrixProfileIds.add(profile.id);
  guideSectionIds.add(profile.guide_section_id);

  if (!profile.applies_to || !Array.isArray(profile.applies_to.example_ids)) {
    fail(`Matrix profile ${profile.id} must define applies_to.example_ids`);
  }
  if (profile.scope === "route_attached" && profile.applies_to.example_ids.length === 0) {
    fail(`Route-attached matrix profile ${profile.id} must point to at least one example`);
  }

  for (const exampleId of profile.applies_to.example_ids) {
    if (!exampleIds.has(exampleId)) {
      fail(`Matrix profile ${profile.id} references unknown example ${exampleId}`);
    }
  }

  for (const value of profile.applies_to.sample_contexts || []) {
    if (!optionSets.get("sample_context").has(value)) {
      fail(`Matrix profile ${profile.id} references invalid sample_context ${value}`);
    }
  }
  for (const value of profile.applies_to.material_classes || []) {
    if (!optionSets.get("material_class").has(value)) {
      fail(`Matrix profile ${profile.id} references invalid material_class ${value}`);
    }
  }
  for (const value of profile.applies_to.target_goals || []) {
    if (!optionSets.get("target_goal").has(value)) {
      fail(`Matrix profile ${profile.id} references invalid target_goal ${value}`);
    }
  }

  if (!Array.isArray(profile.selector_warnings) || profile.selector_warnings.length < 2 || profile.selector_warnings.length > 4) {
    fail(`Matrix profile ${profile.id} must include 2 to 4 selector_warnings`);
  }
  if (!Array.isArray(profile.guide_highlights) || profile.guide_highlights.length < 2 || profile.guide_highlights.length > 5) {
    fail(`Matrix profile ${profile.id} must include 2 to 5 guide_highlights`);
  }
  if (!Array.isArray(profile.citations) || profile.citations.length === 0 || profile.citations.length > 3) {
    fail(`Matrix profile ${profile.id} must include 1 to 3 citations`);
  }

  for (const field of ["kit", "flowcell", "basecalling", "analysis_environment"]) {
    if (!profile.setup_biases[field]) {
      fail(`Matrix profile ${profile.id} is missing setup_biases.${field}`);
    }
  }

  for (const workflowId of profile.fallback_workflow_ids) {
    if (!externalWorkflowIds.has(workflowId)) {
      fail(`Matrix profile ${profile.id} references unknown fallback workflow ${workflowId}`);
    }
  }

  for (const citation of profile.citations) {
    if (!citation.label || !citation.url) {
      fail(`Matrix profile ${profile.id} has an incomplete citation`);
    }
    if (!/^https?:\/\//.test(citation.url)) {
      fail(`Matrix profile ${profile.id} must use absolute citation URLs`);
    }
  }
}

for (const example of examples) {
  if (!example.matrix_profile_id) {
    fail(`Example ${example.id} must include matrix_profile_id`);
  }
  if (!matrixProfileIds.has(example.matrix_profile_id)) {
    fail(`Example ${example.id} references unknown matrix_profile_id ${example.matrix_profile_id}`);
  }
  const matrixProfile = matrixProfiles.find((profile) => profile.id === example.matrix_profile_id);
  if (matrixProfile.scope !== "route_attached") {
    fail(`Example ${example.id} must point to a route-attached matrix profile`);
  }
  if (!matrixProfile.applies_to.example_ids.includes(example.id)) {
    fail(`Matrix profile ${matrixProfile.id} must explicitly include example ${example.id}`);
  }
}

for (const collection of ["kits", "flow_cells", "basecalling_profiles", "route_defaults"]) {
  if (!Array.isArray(nanoporeProfiles[collection]) || nanoporeProfiles[collection].length === 0) {
    fail(`nanopore_profiles.json must include a non-empty ${collection} array`);
  }
}

const kitIds = new Set();
for (const kit of nanoporeProfiles.kits) {
  kitIds.add(kit.id);
  if (!kit.id || !kit.label || !kit.summary || !kit.consequences) {
    fail(`Nanopore kit ${kit.id || "<unknown>"} is missing fields`);
  }
}

const flowCellIds = new Set();
for (const flowCell of nanoporeProfiles.flow_cells) {
  flowCellIds.add(flowCell.id);
  if (!flowCell.id || !flowCell.label || !flowCell.summary) {
    fail(`Flow cell ${flowCell.id || "<unknown>"} is missing fields`);
  }
}

const basecallingIds = new Set();
for (const profile of nanoporeProfiles.basecalling_profiles) {
  basecallingIds.add(profile.id);
  if (!profile.id || !profile.label || !profile.summary) {
    fail(`Basecalling profile ${profile.id || "<unknown>"} is missing fields`);
  }
}

for (const profile of nanoporeProfiles.route_defaults) {
  for (const field of ["sample_contexts", "material_classes", "target_goals", "defaults", "result_note"]) {
    if (!(field in profile)) {
      fail("Each route default must define sample_contexts, material_classes, target_goals, defaults, and result_note");
    }
  }

  for (const value of profile.sample_contexts) {
    if (!optionSets.get("sample_context").has(value)) {
      fail(`Route default references invalid sample_context ${value}`);
    }
  }
  for (const value of profile.material_classes) {
    if (!optionSets.get("material_class").has(value)) {
      fail(`Route default references invalid material_class ${value}`);
    }
  }
  for (const value of profile.target_goals) {
    if (!optionSets.get("target_goal").has(value)) {
      fail(`Route default references invalid target_goal ${value}`);
    }
  }

  if (!kitIds.has(profile.defaults.library_mode)) {
    fail(`Route default references unknown kit ${profile.defaults.library_mode}`);
  }
  if (!flowCellIds.has(profile.defaults.flowcell_family)) {
    fail(`Route default references unknown flow cell ${profile.defaults.flowcell_family}`);
  }
  if (!basecallingIds.has(profile.defaults.basecalling_goal)) {
    fail(`Route default references unknown basecalling profile ${profile.defaults.basecalling_goal}`);
  }
  if (!optionSets.get("analysis_environment").has(profile.defaults.analysis_environment)) {
    fail(`Route default references unknown analysis environment ${profile.defaults.analysis_environment}`);
  }
}

for (const workflow of externalWorkflows) {
  for (const field of [
    "id",
    "label",
    "route_compatibility",
    "supported_material_classes",
    "supported_target_goals",
    "recommended_when",
    "avoid_when",
    "url",
    "source_type"
  ]) {
    if (!(field in workflow)) {
      fail(`External workflow ${workflow.id || "<unknown>"} is missing ${field}`);
    }
  }

  for (const value of workflow.route_compatibility) {
    if (!allowedWorkflowCompat.has(value)) {
      fail(`External workflow ${workflow.id} uses unsupported route compatibility ${value}`);
    }
  }
  for (const value of workflow.supported_material_classes) {
    if (!optionSets.get("material_class").has(value)) {
      fail(`External workflow ${workflow.id} references invalid material_class ${value}`);
    }
  }
  for (const value of workflow.supported_target_goals) {
    if (!optionSets.get("target_goal").has(value)) {
      fail(`External workflow ${workflow.id} references invalid target_goal ${value}`);
    }
  }
  if (!allowedWorkflowSources.has(workflow.source_type)) {
    fail(`External workflow ${workflow.id} uses unsupported source_type ${workflow.source_type}`);
  }
  if (!/^https?:\/\//.test(workflow.url)) {
    fail(`External workflow ${workflow.id} must use an absolute URL`);
  }
  if (workflow.preferred_matrix_profile_ids) {
    if (!Array.isArray(workflow.preferred_matrix_profile_ids)) {
      fail(`External workflow ${workflow.id} preferred_matrix_profile_ids must be an array`);
    }
    for (const profileId of workflow.preferred_matrix_profile_ids) {
      if (!matrixProfileIds.has(profileId)) {
        fail(`External workflow ${workflow.id} references unknown preferred matrix profile ${profileId}`);
      }
    }
  }
}

for (const rule of expertRules) {
  for (const field of ["id", "applies_to_example_ids", "when", "effect_type", "title", "summary", "priority"]) {
    if (!(field in rule)) {
      fail(`Expert rule ${rule.id || "<unknown>"} is missing ${field}`);
    }
  }

  if (!allowedRuleEffects.has(rule.effect_type)) {
    fail(`Expert rule ${rule.id} uses unsupported effect_type ${rule.effect_type}`);
  }

  for (const exampleId of rule.applies_to_example_ids) {
    if (!exampleIds.has(exampleId)) {
      fail(`Expert rule ${rule.id} references unknown example ${exampleId}`);
    }
  }

  for (const [questionId, values] of Object.entries(rule.when)) {
    if (!questionsById.has(questionId)) {
      fail(`Expert rule ${rule.id} references unknown question ${questionId}`);
    }
    const validValues = optionSets.get(questionId);
    for (const value of values) {
      if (!validValues.has(value)) {
        fail(`Expert rule ${rule.id} references invalid ${questionId}:${value}`);
      }
    }
  }

  if (rule.pipeline_id || rule.track_id || rule.reroute_to) {
    fail(`Expert rule ${rule.id} must not reroute the backend`);
  }
}

console.log("Selector data validation passed.");
