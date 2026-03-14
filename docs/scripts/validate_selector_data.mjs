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
const questions = readJson("questions.json");
const playbooks = readJson("playbooks.json");
const examples = readJson("examples.json");
const expertRules = readJson("expert_rules.json");

const requiredPipelineFields = [
  "id",
  "title",
  "short_title",
  "readiness_level",
  "category",
  "sample_types",
  "analysis_goals",
  "input_formats",
  "library_modes",
  "supports_multiplexing",
  "supported_entry_points",
  "default_preprocessing",
  "primary_docs",
  "setup_docs",
  "closest_alternatives",
  "decision_notes",
  "maintainer",
  "last_reviewed",
  "track_notes"
];

const requiredPlaybookFields = [
  "pipeline_id",
  "track_id",
  "example_badge",
  "route_summary",
  "recommended_when",
  "avoid_when",
  "required_inputs",
  "entry_actions",
  "curated_commands",
  "preprocessing_defaults",
  "required_tools",
  "required_databases",
  "expected_outputs",
  "runtime_notes",
  "evidence_links"
];

const allowedPageTypes = new Set(["route", "conditional_route", "expert", "results"]);
const allowedExampleStatuses = new Set(["exact", "unsupported_nearest"]);
const allowedRuleEffects = new Set(["tool_swap", "step_insert", "step_skip", "warning_only", "preprocessing_override"]);
const expectedPageIds = ["sample", "material", "target", "example", "expert", "results"];

const questionOptions = new Map();
const questionsById = new Map();
const questionOrder = [];

if (!Array.isArray(questions.pages)) {
  fail("questions.json must define a top-level pages array");
}

for (const page of questions.pages) {
  if (!page.id || !page.title || !page.summary || !page.page_type) {
    fail(`Question page ${page.id || "<unknown>"} is missing required metadata`);
  }
  if (!allowedPageTypes.has(page.page_type)) {
    fail(`Question page ${page.id} has unsupported page_type ${page.page_type}`);
  }

  if (!Array.isArray(page.questions)) {
    fail(`Question page ${page.id} must define a questions array`);
  }

  for (const question of page.questions) {
    if (!question.id || !question.field || !question.label) {
      fail(`Question in page ${page.id} is missing required fields`);
    }

    questionsById.set(question.id, question);
    questionOrder.push(question.id);
    if (question.dynamic_options_from) {
      questionOptions.set(question.id, new Set());
    } else {
      questionOptions.set(question.id, new Set((question.options || []).map((option) => option.value)));
    }
  }
}

if (expectedPageIds.some((pageId) => !questions.pages.find((page) => page.id === pageId))) {
  fail(`questions.json must include the exact wizard pages ${expectedPageIds.join(", ")}`);
}

const pipelineIds = new Set(pipelines.map((pipeline) => pipeline.id));
const tracksByPipeline = new Map(
  pipelines.map((pipeline) => [pipeline.id, new Set((pipeline.track_notes || []).map((track) => track.id))])
);
const exampleIds = new Set(examples.map((example) => example.id));

function validateVisibilityDependency(ownerLabel, visibleWhen, currentQuestionId) {
  if (!visibleWhen) {
    return;
  }

  for (const [dependencyId, acceptedValues] of Object.entries(visibleWhen)) {
    if (!questionsById.has(dependencyId)) {
      fail(`${ownerLabel} references unknown dependency question ${dependencyId}`);
    }

    if (currentQuestionId) {
      const dependencyIndex = questionOrder.indexOf(dependencyId);
      const currentIndex = questionOrder.indexOf(currentQuestionId);
      if (dependencyIndex >= currentIndex) {
        fail(`${ownerLabel} depends on ${dependencyId}, which is not an earlier question`);
      }
    }

    if (acceptedValues.length === 0) {
      fail(`${ownerLabel} must include at least one accepted value for ${dependencyId}`);
    }

    const allowedValues = questionOptions.get(dependencyId);
    for (const value of acceptedValues) {
      if (allowedValues.size > 0 && !allowedValues.has(value)) {
        fail(`${ownerLabel} references invalid option ${dependencyId}:${value}`);
      }
    }
  }
}

for (const question of questionsById.values()) {
  validateVisibilityDependency(`Question ${question.id}`, question.visible_when, question.id);

  if (question.dynamic_options_from) {
    if (question.dynamic_options_from !== "examples") {
      fail(`Question ${question.id} references unsupported dynamic source ${question.dynamic_options_from}`);
    }
    continue;
  }

  if (!Array.isArray(question.options) || question.options.length === 0) {
    fail(`Question ${question.id} must include static options or a dynamic source`);
  }

  for (const option of question.options) {
    if (!option.value || !option.label) {
      fail(`Question ${question.id} has an incomplete option`);
    }
    validateVisibilityDependency(`Question ${question.id} option ${option.value}`, option.visible_when, question.id);
  }
}

for (const pipeline of pipelines) {
  for (const field of requiredPipelineFields) {
    if (!(field in pipeline)) {
      fail(`Pipeline ${pipeline.id} is missing required field ${field}`);
    }
  }

  if (!pipeline.primary_docs.length || !pipeline.setup_docs.length) {
    fail(`Pipeline ${pipeline.id} must include primary_docs and setup_docs`);
  }

  for (const link of [...pipeline.primary_docs, ...pipeline.setup_docs]) {
    if (!link.label || !link.url) {
      fail(`Pipeline ${pipeline.id} has an incomplete doc link`);
    }
  }

  for (const alternativeId of pipeline.closest_alternatives) {
    if (!pipelineIds.has(alternativeId)) {
      fail(`Pipeline ${pipeline.id} references unknown closest alternative ${alternativeId}`);
    }
  }
}

for (const playbook of playbooks) {
  for (const field of requiredPlaybookFields) {
    if (!(field in playbook)) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} is missing ${field}`);
    }
  }

  if (!pipelineIds.has(playbook.pipeline_id)) {
    fail(`Playbook references unknown pipeline ${playbook.pipeline_id}`);
  }

  if (playbook.track_id !== null && !tracksByPipeline.get(playbook.pipeline_id).has(playbook.track_id)) {
    fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} references an unknown track`);
  }

  if (!Array.isArray(playbook.entry_actions) || playbook.entry_actions.length === 0) {
    fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} must include at least one entry action`);
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
      null
    );
  }

  for (const link of playbook.evidence_links) {
    if (!link.label || !link.url) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} has an incomplete evidence link`);
    }
  }
}

for (const example of examples) {
  const requiredFields = [
    "id",
    "label",
    "sample_contexts",
    "material_classes",
    "target_goals",
    "status_class",
    "route_summary",
    "selection_help"
  ];
  for (const field of requiredFields) {
    if (!(field in example)) {
      fail(`Example ${example.id || "<unknown>"} is missing ${field}`);
    }
  }

  if (!allowedExampleStatuses.has(example.status_class)) {
    fail(`Example ${example.id} has unsupported status_class ${example.status_class}`);
  }

  for (const [questionId, values] of [
    ["sample_context", example.sample_contexts],
    ["material_class", example.material_classes],
    ["target_goal", example.target_goals]
  ]) {
    if (!Array.isArray(values) || values.length === 0) {
      fail(`Example ${example.id} must define ${questionId}-compatible values`);
    }

    for (const value of values) {
      if (!questionOptions.get(questionId).has(value)) {
        fail(`Example ${example.id} references invalid ${questionId}:${value}`);
      }
    }
  }

  if (example.status_class === "exact") {
    if (!example.pipeline_id) {
      fail(`Exact example ${example.id} must define pipeline_id`);
    }
    if (!pipelineIds.has(example.pipeline_id)) {
      fail(`Exact example ${example.id} references unknown pipeline ${example.pipeline_id}`);
    }
    if (example.track_id !== null && !tracksByPipeline.get(example.pipeline_id).has(example.track_id)) {
      fail(`Exact example ${example.id} references unknown track ${example.track_id}`);
    }
  }

  if (example.status_class === "unsupported_nearest") {
    if (!example.nearest_pipeline_id) {
      fail(`Unsupported example ${example.id} must define nearest_pipeline_id`);
    }
    if (!pipelineIds.has(example.nearest_pipeline_id)) {
      fail(`Unsupported example ${example.id} references unknown nearest pipeline ${example.nearest_pipeline_id}`);
    }
    if (example.nearest_track_id !== null && !tracksByPipeline.get(example.nearest_pipeline_id).has(example.nearest_track_id)) {
      fail(`Unsupported example ${example.id} references unknown nearest track ${example.nearest_track_id}`);
    }
    if (!example.unsupported_reason) {
      fail(`Unsupported example ${example.id} must define unsupported_reason`);
    }
  }
}

for (const rule of expertRules) {
  const requiredFields = [
    "id",
    "applies_to_example_ids",
    "when",
    "effect_type",
    "title",
    "summary",
    "priority"
  ];
  for (const field of requiredFields) {
    if (!(field in rule)) {
      fail(`Expert rule ${rule.id || "<unknown>"} is missing ${field}`);
    }
  }

  if (!allowedRuleEffects.has(rule.effect_type)) {
    fail(`Expert rule ${rule.id} has unsupported effect_type ${rule.effect_type}`);
  }

  if ("pipeline_id" in rule || "track_id" in rule || "reroute_to" in rule) {
    fail(`Expert rule ${rule.id} may not reroute the backend`);
  }

  for (const exampleId of rule.applies_to_example_ids) {
    if (!exampleIds.has(exampleId)) {
      fail(`Expert rule ${rule.id} references unknown example ${exampleId}`);
    }
  }

  validateVisibilityDependency(`Expert rule ${rule.id}`, rule.when, null);

  if (rule.effect_type === "tool_swap" && !rule.tool_override) {
    fail(`Expert rule ${rule.id} must define tool_override`);
  }

  if (rule.effect_type === "step_insert") {
    if (!rule.step_insertion?.id || !rule.step_insertion?.title || !rule.step_insertion?.summary) {
      fail(`Expert rule ${rule.id} must define a complete step_insertion`);
    }
  }

  if (rule.effect_type === "step_skip" && (!Array.isArray(rule.target_step_ids) || rule.target_step_ids.length === 0)) {
    fail(`Expert rule ${rule.id} must define target_step_ids`);
  }
}

console.log("selector data ok");
