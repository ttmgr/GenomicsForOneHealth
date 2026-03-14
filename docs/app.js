const PAGES_URL = "https://ttmgr.github.io/GenomicsForOneHealth/";

const WEIGHTS = {
  category: 60,
  sample_types: 42,
  molecule_types: 34,
  analysis_goals: 44,
  input_formats: 24,
  library_modes: 18,
  supports_multiplexing: 6
};

const PREPROCESSING_LABELS = {
  input_expectation: "Input expectation",
  basecalling: "Basecalling",
  demultiplexing: "Demultiplexing",
  adapter_trimming: "Adapter trimming",
  length_quality_filtering: "Length / quality filtering",
  additional_preprocessing: "Additional preprocessing"
};

const selectorRoot = document.getElementById("selector-root");
const resultRoot = document.getElementById("result-root");
const statusBanner = document.getElementById("status-banner");
const resetButton = document.getElementById("reset-button");

let pipelines = [];
let questionSpec = null;
let answers = {};

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

function optionFor(question, value) {
  return question.options.find((option) => option.value === value);
}

function isNeutral(question, value) {
  if (!value) {
    return false;
  }
  const option = optionFor(question, value);
  return Boolean(option && option.neutral);
}

function stageQuestions(stageId) {
  return questionSpec.stages.find((stage) => stage.id === stageId)?.questions || [];
}

function stageComplete(stageId) {
  return stageQuestions(stageId).every((question) => Boolean(answers[question.id]));
}

function hardFilterQuestion(question) {
  return question.stage === "stage1";
}

function matchesFieldValue(pipeline, field, value) {
  if (!value) {
    return false;
  }

  if (field === "category") {
    return pipeline.category === value;
  }

  if (field === "supports_multiplexing") {
    if (value === "yes") {
      return pipeline.supports_multiplexing;
    }
    if (value === "no") {
      return !pipeline.supports_multiplexing;
    }
    return false;
  }

  const collection = pipeline[field];
  return Array.isArray(collection) ? collection.includes(value) : false;
}

function passesHardFilters(pipeline) {
  for (const stage of questionSpec.stages) {
    for (const question of stage.questions) {
      if (!hardFilterQuestion(question)) {
        continue;
      }
      const value = answers[question.id];
      if (!value || isNeutral(question, value)) {
        continue;
      }
      if (!matchesFieldValue(pipeline, question.field, value)) {
        return false;
      }
    }
  }
  return true;
}

function scorePipeline(pipeline) {
  let score = 0;
  const reasons = [];

  for (const stage of questionSpec.stages) {
    for (const question of stage.questions) {
      const value = answers[question.id];
      if (!value || isNeutral(question, value)) {
        continue;
      }

      if (question.field === "supports_multiplexing") {
        if (matchesFieldValue(pipeline, question.field, value)) {
          score += WEIGHTS.supports_multiplexing;
          reasons.push(`${question.label}: ${optionFor(question, value).label}`);
        }
        continue;
      }

      if (matchesFieldValue(pipeline, question.field, value)) {
        const weight = WEIGHTS[question.field] || 0;
        score += weight;
        reasons.push(`${question.label}: ${optionFor(question, value).label}`);
      }
    }
  }

  return { score, reasons };
}

function chooseTrack(pipeline) {
  if (!Array.isArray(pipeline.track_notes) || pipeline.track_notes.length === 0) {
    return null;
  }

  let bestTrack = null;
  let bestScore = -1;

  for (const track of pipeline.track_notes) {
    const when = track.when || {};
    let score = 0;

    for (const [field, acceptedValues] of Object.entries(when)) {
      const question = questionSpec.stages.flatMap((stage) => stage.questions).find((item) => item.field === field);
      const value = question ? answers[question.id] : null;
      if (!value || (question && isNeutral(question, value))) {
        continue;
      }
      if (acceptedValues.includes(value)) {
        score += 1;
      } else {
        score = -1;
        break;
      }
    }

    if (score > bestScore) {
      bestScore = score;
      bestTrack = score > 0 ? track : null;
    }
  }

  return bestTrack;
}

function derivePreprocessing(pipeline, track) {
  return {
    ...pipeline.default_preprocessing,
    ...(track?.preprocessing_override || {})
  };
}

function buildCompatibilityNotes(pipeline, exactMatch, track) {
  const notes = [];
  const questions = questionSpec.stages.flatMap((stage) => stage.questions);

  if (!exactMatch) {
    notes.push({
      title: "No exact current pipeline",
      text: "The current collection does not contain a workflow that exactly matches all Stage 1 answers. This recommendation is the nearest documented starting point in the existing repository."
    });
  }

  const inputQuestion = questions.find((question) => question.id === "input_format");
  const inputValue = answers.input_format;
  if (inputValue && !isNeutral(inputQuestion, inputValue) && !matchesFieldValue(pipeline, "input_formats", inputValue)) {
    notes.push({
      title: "Input-format adaptation required",
      text: `Your current input format is ${optionFor(inputQuestion, inputValue).label}. The documented workflow is written primarily for ${pipeline.input_formats.join(", ")}. Some adaptation may be required before you can run it exactly as published.`
    });
  }

  const libraryQuestion = questions.find((question) => question.id === "library_mode");
  const libraryValue = answers.library_mode;
  if (libraryValue && !isNeutral(libraryQuestion, libraryValue) && pipeline.library_modes.length > 0 && !matchesFieldValue(pipeline, "library_modes", libraryValue)) {
    notes.push({
      title: "Library-mode mismatch",
      text: `You selected ${optionFor(libraryQuestion, libraryValue).label}, but this workflow is documented mainly for ${pipeline.library_modes.join(", ")}. Treat the recommendation as a starting point rather than an exact protocol match.`
    });
  }

  const demuxValue = answers.demultiplexing;
  if (demuxValue === "needed" && !pipeline.supports_multiplexing) {
    notes.push({
      title: "Demultiplexing not central to this workflow",
      text: "You indicated that demultiplexing is still needed, but multiplexing is not a central documented mode for this workflow. Confirm whether your data should be separated upstream before using this pipeline."
    });
  }

  if (answers.basecalling_state === "already_basecalled") {
    notes.push({
      title: "Basecalling can likely be skipped",
      text: "You indicated that reads are already basecalled. Start at the read-level preprocessing stage and verify that the current read files and quality thresholds match the documented workflow."
    });
  } else if (answers.basecalling_state === "raw_signal_not_basecalled") {
    notes.push({
      title: "Raw-data entry point",
      text: `This recommendation assumes a raw-data entry point that is compatible with ${pipeline.input_formats.join(", ")}. Use the documented basecalling branch before downstream preprocessing.`
    });
  }

  if (answers.preprocessing_state === "already_trimmed_and_filtered") {
    notes.push({
      title: "Read preprocessing may already be complete",
      text: "You indicated that adapter trimming and read filtering are already done. Verify that the published thresholds still match your processed reads before skipping those steps."
    });
  }

  if (track?.notes?.length) {
    for (const note of track.notes) {
      notes.push({
        title: track.title,
        text: note
      });
    }
  }

  return notes;
}

function explainRecommendation(pipeline, exactMatch, track) {
  if (exactMatch) {
    const trackText = track ? ` The closest internal branch is ${track.title}.` : "";
    return `${pipeline.title} is the strongest current fit for your biological use case, sample type, and analytical objective within the published collection.${trackText}`;
  }

  return `${pipeline.title} is the nearest documented starting point in the current collection, but at least one of your Stage 1 answers falls outside the workflows that are presently published in this repository.`;
}

function computeRecommendation() {
  if (!stageComplete("stage1")) {
    return null;
  }

  const exactCandidates = pipelines.filter(passesHardFilters);
  const pool = exactCandidates.length > 0 ? exactCandidates : pipelines;
  const ranked = pool
    .map((pipeline) => ({
      pipeline,
      ...scorePipeline(pipeline)
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.pipeline.title.localeCompare(right.pipeline.title);
    });

  const best = ranked[0];
  const track = chooseTrack(best.pipeline);
  const preprocessing = derivePreprocessing(best.pipeline, track);
  const exactMatch = exactCandidates.length > 0;

  return {
    exactMatch,
    candidateCount: exactCandidates.length,
    pipeline: best.pipeline,
    track,
    preprocessing,
    reasons: best.reasons,
    explanation: explainRecommendation(best.pipeline, exactMatch, track),
    compatibilityNotes: buildCompatibilityNotes(best.pipeline, exactMatch, track)
  };
}

function renderLinks(title, links) {
  if (!links || links.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">${title}</p>
      <div class="link-list">
        ${links
          .map(
            (link) => `
            <div class="link-item">
              <strong>${link.label}</strong>
              <a href="${link.url}" target="_blank" rel="noreferrer">${link.url_label || link.url}</a>
            </div>
          `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderPreprocessingTable(preprocessing) {
  const rows = Object.entries(PREPROCESSING_LABELS)
    .filter(([key]) => preprocessing[key])
    .map(
      ([key, label]) => `
        <tr>
          <th scope="row">${label}</th>
          <td>${preprocessing[key]}</td>
        </tr>
      `
    )
    .join("");

  return `
    <div class="sub-card">
      <p class="section-label">Preprocessing Defaults</p>
      <table class="preprocessing-table">
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderResult() {
  const recommendation = computeRecommendation();
  if (!recommendation) {
    resultRoot.innerHTML = `
      <div class="empty-state">
        <p class="empty-title">No recommendation yet</p>
        <p class="empty-text">Answer the Stage 1 questions to narrow the collection to compatible workflows.</p>
      </div>
    `;
    return;
  }

  const statusClass = recommendation.exactMatch ? "is-exact" : "is-nearest";
  const statusLabel = recommendation.exactMatch ? "Exact current match" : "Nearest current starting point";

  const trackHtml = recommendation.track
    ? `
      <div class="sub-card">
        <p class="section-label">Relevant branch</p>
        <h4>${recommendation.track.title}</h4>
        <p>${recommendation.track.summary}</p>
      </div>
    `
    : "";

  const reasonsHtml = recommendation.reasons.length
    ? `
      <div class="sub-card">
        <p class="section-label">Why this matched</p>
        <div class="match-list">
          ${recommendation.reasons
            .slice(0, 6)
            .map(
              (reason) => `
                <div class="match-item">
                  <strong>Matched field</strong>
                  <span>${reason}</span>
                </div>
              `
            )
            .join("")}
        </div>
      </div>
    `
    : "";

  const warningsHtml = recommendation.compatibilityNotes.length
    ? `
      <div class="sub-card">
        <p class="section-label">Compatibility Notes</p>
        <div class="warning-list">
          ${recommendation.compatibilityNotes
            .map(
              (note) => `
                <div class="warning-item">
                  <strong>${note.title}</strong>
                  <span>${note.text}</span>
                </div>
              `
            )
            .join("")}
        </div>
      </div>
    `
    : "";

  resultRoot.innerHTML = `
    <div class="recommendation-card">
      <div class="recommendation-top">
        <div>
          <p class="section-label">Primary recommendation</p>
          <h3>${recommendation.pipeline.title}</h3>
          <p class="recommendation-text">${recommendation.explanation}</p>
        </div>
        <span class="result-chip ${statusClass}">${statusLabel}</span>
      </div>

      <div class="sub-grid">
        ${trackHtml}
        ${renderPreprocessingTable(recommendation.preprocessing)}
        <div class="sub-card">
          <p class="section-label">Execution model</p>
          <p>${recommendation.pipeline.execution_model}</p>
        </div>
        ${reasonsHtml}
        ${warningsHtml}
        ${renderLinks("Primary documentation", recommendation.pipeline.primary_docs)}
        ${renderLinks("Setup and execution", recommendation.pipeline.setup_docs)}
      </div>
    </div>
  `;
}

function renderStage(stage) {
  const stageIsActive = stage.id === "stage1" || stageComplete("stage1");
  const badgeText = stage.id === "stage1" ? "Required" : stageIsActive ? "Active" : "Locked";

  return `
    <section class="selector-stage ${stageIsActive ? "is-active" : ""}" data-stage="${stage.id}">
      <div class="stage-head">
        <div>
          <p class="section-label">${stage.title}</p>
          <p class="stage-summary">${stage.summary}</p>
        </div>
        <span class="stage-badge">${badgeText}</span>
      </div>
      <div class="question-grid">
        ${stage.questions
          .map((question) => {
            const value = answers[question.id] || "";
            return `
              <article class="question-card">
                <h4>${question.label}</h4>
                <p>${question.description}</p>
                <div class="option-grid">
                  ${question.options
                    .map(
                      (option, index) => `
                        <div class="option-card">
                          <input
                            type="radio"
                            id="${question.id}-${index}"
                            name="${question.id}"
                            value="${option.value}"
                            ${value === option.value ? "checked" : ""}
                            ${stage.id === "stage2" && !stageIsActive ? "disabled" : ""}
                          >
                          <label for="${question.id}-${index}">
                            <span class="option-label">${option.label}</span>
                            <span class="option-help">${option.help}</span>
                          </label>
                        </div>
                      `
                    )
                    .join("")}
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    </section>
  `;
}

function renderStatus() {
  if (!stageComplete("stage1")) {
    statusBanner.className = "status-banner is-idle";
    statusBanner.textContent = "Answer all Stage 1 questions to narrow the collection to biologically compatible workflows.";
    return;
  }

  const exactCandidates = pipelines.filter(passesHardFilters);
  if (exactCandidates.length === 0) {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "No exact current pipeline matches all Stage 1 answers. The selector will show the nearest documented starting point in the collection.";
    return;
  }

  if (exactCandidates.length === 1) {
    statusBanner.className = "status-banner is-success";
    statusBanner.textContent = "One exact current workflow matches your biological and analytical criteria. Use Stage 2 to refine preprocessing guidance.";
    return;
  }

  statusBanner.className = "status-banner is-success";
  statusBanner.textContent = `${exactCandidates.length} exact current workflows remain after Stage 1. Use Stage 2 to resolve the strongest practical fit.`;
}

function renderSelector() {
  selectorRoot.innerHTML = questionSpec.stages.map(renderStage).join("");

  selectorRoot.querySelectorAll("input[type='radio']").forEach((input) => {
    input.addEventListener("change", (event) => {
      answers[event.target.name] = event.target.value;
      render();
    });
  });
}

function render() {
  renderStatus();
  renderSelector();
  renderResult();
}

async function init() {
  try {
    [pipelines, questionSpec] = await Promise.all([
      fetchJson("data/pipelines.json"),
      fetchJson("data/questions.json")
    ]);
    render();
  } catch (error) {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = `The selector assets could not be loaded. Open ${PAGES_URL} or check that the docs/data files are present in the repository.`;
    selectorRoot.innerHTML = `
      <div class="error-box">
        Failed to load selector data. If you are viewing the repository source on GitHub, use the GitHub Pages URL instead.
      </div>
    `;
  }
}

resetButton.addEventListener("click", () => {
  answers = {};
  render();
});

init();
