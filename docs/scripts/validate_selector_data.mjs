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
const presets = readJson("presets.json");
const outOfScopeRules = readJson("out_of_scope.json");

const requiredPipelineFields = [
  "id",
  "title",
  "short_title",
  "readiness_level",
  "selector_groups",
  "category",
  "sample_types",
  "analysis_goals",
  "molecule_types",
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

const questionOptions = new Map();
for (const stage of questions.stages) {
  for (const question of stage.questions) {
    questionOptions.set(
      question.id,
      new Set(question.options.map((option) => option.value))
    );
  }
}

const pipelineIds = new Set(pipelines.map((pipeline) => pipeline.id));
const tracksByPipeline = new Map(
  pipelines.map((pipeline) => [pipeline.id, new Set((pipeline.track_notes || []).map((track) => track.id))])
);

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
      fail(`Pipeline ${pipeline.id} has an incomplete link entry`);
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
      fail(`Playbook for ${playbook.pipeline_id}/${playbook.track_id} is missing ${field}`);
    }
  }

  if (!pipelineIds.has(playbook.pipeline_id)) {
    fail(`Playbook references unknown pipeline ${playbook.pipeline_id}`);
  }

  if (playbook.track_id !== null && !tracksByPipeline.get(playbook.pipeline_id).has(playbook.track_id)) {
    fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} references an unknown track`);
  }

  if (playbook.entry_actions.length === 0) {
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
    if (command.when) {
      for (const [questionId, values] of Object.entries(command.when)) {
        if (!questionOptions.has(questionId)) {
          fail(`Curated command in ${playbook.pipeline_id}/${playbook.track_id} references unknown question ${questionId}`);
        }
        for (const value of values) {
          if (!questionOptions.get(questionId).has(value)) {
            fail(`Curated command in ${playbook.pipeline_id}/${playbook.track_id} references invalid value ${questionId}:${value}`);
          }
        }
      }
    }
  }

  for (const link of playbook.evidence_links) {
    if (!link.label || !link.url) {
      fail(`Playbook ${playbook.pipeline_id}/${playbook.track_id} has an incomplete evidence link`);
    }
  }
}

for (const preset of presets) {
  if (!preset.id || !preset.title || !preset.summary || !preset.audience || typeof preset.featured !== "boolean") {
    fail(`Preset ${preset.id || "<unknown>"} is incomplete`);
  }

  for (const [questionId, value] of Object.entries(preset.prefill_answers)) {
    if (!questionOptions.has(questionId)) {
      fail(`Preset ${preset.id} references unknown question ${questionId}`);
    }
    if (!questionOptions.get(questionId).has(value)) {
      fail(`Preset ${preset.id} references invalid option ${questionId}:${value}`);
    }
  }
}

for (const rule of outOfScopeRules) {
  if (!rule.id || !rule.when || !rule.message || !rule.why_not_exact || !rule.primary_nearest_pipeline) {
    fail(`Out-of-scope rule ${rule.id || "<unknown>"} is incomplete`);
  }

  if (!pipelineIds.has(rule.primary_nearest_pipeline)) {
    fail(`Out-of-scope rule ${rule.id} references unknown primary pipeline ${rule.primary_nearest_pipeline}`);
  }

  for (const pipelineId of rule.secondary_nearest_pipelines || []) {
    if (!pipelineIds.has(pipelineId)) {
      fail(`Out-of-scope rule ${rule.id} references unknown secondary pipeline ${pipelineId}`);
    }
  }

  for (const conditionSet of [rule.when, rule.unless]) {
    if (!conditionSet) {
      continue;
    }
    for (const [questionId, values] of Object.entries(conditionSet)) {
      if (!questionOptions.has(questionId)) {
        fail(`Out-of-scope rule ${rule.id} references unknown question ${questionId}`);
      }
      for (const value of values) {
        if (!questionOptions.get(questionId).has(value)) {
          fail(`Out-of-scope rule ${rule.id} references invalid value ${questionId}:${value}`);
        }
      }
    }
  }

  for (const link of rule.read_first_links || []) {
    if (!link.label || !link.url) {
      fail(`Out-of-scope rule ${rule.id} has an incomplete read_first_links entry`);
    }
  }
}

console.log("selector data ok");
