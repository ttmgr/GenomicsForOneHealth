const PAGES_URL = "https://ttmgr.github.io/GenomicsForOneHealth/";

const PREPROCESSING_LABELS = {
  input_expectation: "Input expectation",
  basecalling: "Basecalling",
  demultiplexing: "Demultiplexing",
  adapter_trimming: "Adapter trimming",
  length_quality_filtering: "Length / quality filtering",
  additional_preprocessing: "Additional preprocessing"
};

const {
  allQuestions,
  stageComplete,
  computeRecommendation
} = globalThis.SelectorEngine || {};

const presetRoot = document.getElementById("preset-root");
const selectorRoot = document.getElementById("selector-root");
const resultRoot = document.getElementById("result-root");
const statusBanner = document.getElementById("status-banner");
const resetButton = document.getElementById("reset-button");

let datasets = null;
let answers = {};

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function questionById(questionId) {
  return allQuestions?.(datasets.questionSpec).find((question) => question.id === questionId) || null;
}

function optionFor(question, value) {
  return question?.options.find((option) => option.value === value) || null;
}

function labelForAnswer(questionId, answerSet = answers) {
  const question = questionById(questionId);
  const value = answerSet[questionId];
  return optionFor(question, value)?.label || value || "";
}

function isNeutralAnswer(questionId, value) {
  return Boolean(optionFor(questionById(questionId), value)?.neutral);
}

function visibleOptionsForQuestion(question, answerSet = answers) {
  const hasConditionalOptions = question.options.some((option) => option.visible_when);
  if (!hasConditionalOptions) {
    return question.options;
  }

  return question.options.filter((option) => {
    if (!option.visible_when) {
      return true;
    }

    return Object.entries(option.visible_when).every(([dependencyId, acceptedValues]) => {
      const dependencyValue = answerSet[dependencyId];
      if (!dependencyValue) {
        return false;
      }
      if (isNeutralAnswer(dependencyId, dependencyValue)) {
        return true;
      }
      return acceptedValues.includes(dependencyValue);
    });
  });
}

function pruneInvisibleAnswers(answerSet) {
  const normalized = { ...answerSet };
  let changed = true;

  while (changed) {
    changed = false;

    for (const question of allQuestions(datasets.questionSpec)) {
      const value = normalized[question.id];
      if (!value) {
        continue;
      }

      const visibleValues = new Set(visibleOptionsForQuestion(question, normalized).map((option) => option.value));
      if (!visibleValues.has(value)) {
        delete normalized[question.id];
        changed = true;
      }
    }
  }

  return normalized;
}

function applyLibraryAutofill(answerSet) {
  const normalized = { ...answerSet };
  const libraryQuestion = questionById("library_mode");
  const libraryOption = optionFor(libraryQuestion, normalized.library_mode);

  if (!libraryOption?.autofill) {
    return normalized;
  }

  for (const [questionId, value] of Object.entries(libraryOption.autofill)) {
    if (!normalized[questionId]) {
      normalized[questionId] = value;
    }
  }

  return normalized;
}

function normalizeAnswers(nextAnswers, changedQuestionId = null) {
  let normalized = { ...nextAnswers };

  if (changedQuestionId === "library_mode") {
    delete normalized.multiplexing;
    delete normalized.demultiplexing;
  }

  normalized = pruneInvisibleAnswers(normalized);

  if (!normalized.library_mode) {
    delete normalized.multiplexing;
    delete normalized.demultiplexing;
  }

  normalized = applyLibraryAutofill(normalized);
  return normalized;
}

function isPresetActive(preset) {
  return Object.entries(preset.prefill_answers).every(([key, value]) => answers[key] === value);
}

function renderPresets() {
  const featuredPresets = datasets.presets.filter((preset) => preset.featured);
  const groupOrder = ["Environmental examples", "Clinical / isolate examples", "Food safety examples"];
  const groupedPresets = groupOrder
    .map((group) => ({
      group,
      presets: featuredPresets.filter((preset) => preset.group === group)
    }))
    .filter((entry) => entry.presets.length > 0);

  presetRoot.innerHTML = `
    <section class="preset-panel">
      <div class="stage-head">
        <div>
          <p class="section-label">Published Examples</p>
          <p class="stage-summary">These are published examples of broader sequencing routes. Apply one, then edit the answers if your own setup differs.</p>
        </div>
      </div>
      <div class="preset-stack">
        ${groupedPresets
          .map(
            (entry) => `
              <section class="preset-group">
                <div class="preset-group-head">
                  <p class="preset-group-title">${entry.group}</p>
                </div>
                <div class="preset-grid">
                  ${entry.presets
                    .map(
                      (preset) => `
                        <button class="preset-card ${isPresetActive(preset) ? "is-active" : ""}" type="button" data-preset-id="${preset.id}">
                          <span class="preset-audience">${preset.audience}</span>
                          <strong>${preset.title}</strong>
                          <span>${preset.summary}</span>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
          )
          .join("")}
      </div>
    </section>
  `;

  presetRoot.querySelectorAll("[data-preset-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const preset = datasets.presets.find((entry) => entry.id === button.dataset.presetId);
      answers = normalizeAnswers({ ...preset.prefill_answers });
      render();
    });
  });
}

function renderOptionDetails(question, option) {
  if (question.id !== "library_mode" || !option.consequences) {
    return "";
  }

  const rows = [
    ["Demux", option.consequences.demultiplexing],
    ["Barcode trim", option.consequences.barcode_trimming],
    ["Typical use", option.consequences.typical_use],
    ["Route", option.consequences.route_implication]
  ].filter(([, value]) => value);

  return `
    <div class="option-meta-list">
      ${rows
        .map(
          ([label, value]) => `
            <span class="option-meta-item">
              <strong>${label}</strong>
              <span>${value}</span>
            </span>
          `
        )
        .join("")}
    </div>
  `;
}

function renderStage(stage) {
  const stageIsActive = stage.id === "stage1" || stageComplete(datasets.questionSpec, answers, "stage1");
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
            const visibleOptions = visibleOptionsForQuestion(question);
            const gridClass =
              question.id === "sequencing_context"
                ? "option-grid is-route-grid"
                : question.id === "library_mode"
                  ? "option-grid is-kit-grid"
                  : "option-grid";
            const cardClass =
              question.id === "sequencing_context"
                ? "question-card is-route-question"
                : question.id === "library_mode"
                  ? "question-card is-kit-question"
                  : "";

            return `
              <article class="question-card ${cardClass}">
                <h4>${question.label}</h4>
                <p>${question.description}</p>
                <div class="${gridClass}">
                  ${visibleOptions
                    .map(
                      (option, index) => `
                        <div class="option-card ${question.id === "sequencing_context" ? "is-route-card" : ""} ${question.id === "library_mode" ? "is-kit-card" : ""}">
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
                            ${renderOptionDetails(question, option)}
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

function renderSelector() {
  selectorRoot.innerHTML = datasets.questionSpec.stages.map(renderStage).join("");

  selectorRoot.querySelectorAll("input[type='radio']").forEach((input) => {
    input.addEventListener("change", (event) => {
      answers = normalizeAnswers(
        {
          ...answers,
          [event.target.name]: event.target.value
        },
        event.target.name
      );
      render();
    });
  });
}

function renderStatus(recommendation) {
  if (!stageComplete(datasets.questionSpec, answers, "stage1")) {
    statusBanner.className = "status-banner is-idle";
    statusBanner.textContent = "Start with sequencing context, then kit or run mode, goal, and sample context, or apply one of the published examples above.";
    return;
  }

  if (!recommendation) {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "The selector could not derive a recommendation from the current answers.";
    return;
  }

  if (recommendation.status === "unsupported") {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "This route falls outside the current published boundary. The action sheet below shows the nearest documented backend only.";
    return;
  }

  if (recommendation.status === "closest_supported") {
    statusBanner.className = recommendation.confidence === "low" ? "status-banner is-warning" : "status-banner is-success";
    statusBanner.textContent = "The selector mapped your generalized route to the nearest published example backend in the repository.";
    return;
  }

  if (recommendation.status === "track_exact") {
    statusBanner.className = "status-banner is-success";
    statusBanner.textContent = "The selected route maps directly to a published workflow and a specific internal branch.";
    return;
  }

  statusBanner.className = "status-banner is-success";
  statusBanner.textContent = "The selected route maps directly to a published workflow example in the repository.";
}

function renderLinks(title, links) {
  if (!links?.length) {
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

function renderStructuredList(title, items) {
  if (!items?.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">${title}</p>
      <div class="resource-list">
        ${items
          .map(
            (item) => `
              <div class="resource-item">
                <strong>${item.name}</strong>
                <span>${item.note}</span>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderBulletCard(title, items, className = "detail-list") {
  if (!items?.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">${title}</p>
      <ul class="${className}">
        ${items.map((item) => `<li>${item}</li>`).join("")}
      </ul>
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
      <p class="section-label">Preprocessing defaults</p>
      <table class="preprocessing-table">
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderGeneralizedRouteCard(recommendation) {
  const route = [
    labelForAnswer("sequencing_context"),
    labelForAnswer("library_mode"),
    labelForAnswer("analysis_goal"),
    labelForAnswer("sample_type")
  ]
    .filter(Boolean)
    .join(" -> ");
  const readiness = recommendation.primary.pipeline.readiness_level.replaceAll("_", " ");

  return `
    <div class="sub-card">
      <p class="section-label">Recommended generalized route</p>
      <div class="chip-row">
        <span class="result-chip ${recommendation.status === "unsupported" || recommendation.status === "closest_supported" ? "is-nearest" : "is-exact"}">${recommendation.statusLabel}</span>
        <span class="result-chip confidence-${recommendation.confidence}">${recommendation.confidenceLabel}</span>
      </div>
      <div class="route-callout">${route}</div>
      <p>${recommendation.fitSummary}</p>
      <div class="resource-list compact">
        <div class="resource-item">
          <strong>Readiness level</strong>
          <span>${readiness}</span>
        </div>
        <div class="resource-item">
          <strong>Execution model</strong>
          <span>${recommendation.primary.pipeline.execution_model}</span>
        </div>
      </div>
    </div>
  `;
}

function renderPublishedBackendCard(recommendation) {
  const primaryDoc = recommendation.primary.pipeline.primary_docs?.[0];
  const alternative = recommendation.alternatives[0];
  const alternativeDoc = alternative?.primary_docs?.[0];
  const playbook = recommendation.primary.playbook;

  return `
    <div class="sub-card">
      <p class="section-label">Published example backend</p>
      <div class="example-list">
        <div class="example-item example-item-primary">
          <div class="chip-row">
            <span class="result-chip is-exact">${playbook?.example_badge || "Published example"}</span>
            ${playbook?.route_summary ? `<span class="example-route">${playbook.route_summary}</span>` : ""}
          </div>
          <strong>${recommendation.primary.pipeline.title}${recommendation.primary.track ? ` · ${recommendation.primary.track.title}` : ""}</strong>
          <p>${recommendation.explanation}</p>
          ${primaryDoc ? `<a href="${primaryDoc.url}" target="_blank" rel="noreferrer">Open primary example documentation</a>` : ""}
        </div>
        ${
          alternative
            ? `
              <div class="example-item">
                <div class="chip-row">
                  <span class="result-chip is-nearest">Nearby example</span>
                </div>
                <strong>${alternative.title}</strong>
                <p>${(alternative.decision_notes || alternative.notes || []).slice(0, 1).join(" ")}</p>
                ${alternativeDoc ? `<a href="${alternativeDoc.url}" target="_blank" rel="noreferrer">Open nearby example</a>` : ""}
              </div>
            `
            : ""
        }
      </div>
    </div>
  `;
}

function renderReasons(recommendation) {
  if (!recommendation.decision_trace.reasons.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Why this example was chosen</p>
      <div class="match-list">
        ${recommendation.decision_trace.reasons
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
  `;
}

function renderKitConsequencesCard() {
  const libraryQuestion = questionById("library_mode");
  const selectedLibrary = optionFor(libraryQuestion, answers.library_mode);
  const consequences = selectedLibrary?.consequences;

  if (!consequences) {
    return "";
  }

  const rows = [
    ["Demultiplexing", consequences.demultiplexing],
    ["Barcode trimming", consequences.barcode_trimming],
    ["Typical use", consequences.typical_use],
    ["Route implication", consequences.route_implication],
    ["First preprocessing steps", consequences.first_steps]
  ].filter(([, value]) => value);

  return `
    <div class="sub-card">
      <p class="section-label">What the selected kit changes</p>
      <div class="kit-effects">
        ${rows
          .map(
            ([label, value]) => `
              <div class="resource-item">
                <strong>${label}</strong>
                <span>${value}</span>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderActions(actions) {
  if (!actions?.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">What to do next</p>
      <ol class="step-list">
        ${actions
          .slice(0, 6)
          .map(
            (action) => `
              <li class="step-item">
                <strong>${action.title}</strong>
                <span>${action.summary}</span>
                <a href="${action.doc_url}" target="_blank" rel="noreferrer">${action.entry_file}</a>
              </li>
            `
          )
          .join("")}
      </ol>
    </div>
  `;
}

function renderEntryCard(recommendation) {
  const command = recommendation.primary.curatedCommands[0];
  const additionalCommands = recommendation.primary.curatedCommands.slice(1, 3);
  const fallbackAction = recommendation.primary.entryActions[0];
  const supportedEntryPoints = recommendation.primary.pipeline.supported_entry_points || [];

  if (!command && !fallbackAction && supportedEntryPoints.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Entry point and documented command</p>
      ${
        command
          ? `
            <div class="command-card">
              <strong>${command.label}</strong>
              <p>${command.notes}</p>
              <pre><code>${escapeHtml(command.command)}</code></pre>
              <a href="${command.source_url}" target="_blank" rel="noreferrer">Command source</a>
            </div>
          `
          : fallbackAction
            ? `
              <div class="command-card">
                <strong>${fallbackAction.title}</strong>
                <p>${fallbackAction.summary}</p>
                <p class="entry-file">${fallbackAction.entry_file}</p>
                <a href="${fallbackAction.doc_url}" target="_blank" rel="noreferrer">Open documented entry point</a>
              </div>
            `
            : ""
      }
      ${
        supportedEntryPoints.length
          ? `
            <div class="resource-list compact">
              ${supportedEntryPoints
                .map(
                  (entryPoint) => `
                    <div class="resource-item">
                      <strong>${entryPoint.label}</strong>
                      <span>${entryPoint.notes}</span>
                    </div>
                  `
                )
                .join("")}
            </div>
          `
          : ""
      }
      ${
        additionalCommands.length
          ? `
            <div class="command-stack">
              ${additionalCommands
                .map(
                  (item) => `
                    <div class="command-card">
                      <strong>${item.label}</strong>
                      <p>${item.notes}</p>
                      <pre><code>${escapeHtml(item.command)}</code></pre>
                      <a href="${item.source_url}" target="_blank" rel="noreferrer">Command source</a>
                    </div>
                  `
                )
                .join("")}
            </div>
          `
          : ""
      }
    </div>
  `;
}

function renderOntReferenceCard(recommendation) {
  if (!recommendation.ontNotes?.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Oxford Nanopore reference</p>
      <div class="ont-list">
        ${recommendation.ontNotes
          .map(
            (note) => `
              <div class="ont-item">
                <strong>${note.title}</strong>
                <p>${note.description}</p>
                <a href="${note.url}" target="_blank" rel="noreferrer">${note.urlLabel}</a>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderWarnings(recommendation) {
  if (!recommendation.warnings?.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Warnings / not-exact caveats</p>
      <div class="warning-list">
        ${recommendation.warnings
          .map(
            (warning) => `
              <div class="warning-item">
                <strong>${warning.title}</strong>
                <span>${warning.text}</span>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderResult(recommendation) {
  if (!recommendation) {
    resultRoot.innerHTML = `
      <div class="empty-state">
        <p class="empty-title">No recommendation yet</p>
        <p class="empty-text">Answer the sequencing context, kit or run mode, goal, and sample-context questions or start from a published example.</p>
      </div>
    `;
    return;
  }

  const playbook = recommendation.primary.playbook;

  resultRoot.innerHTML = `
    <div class="recommendation-card">
      <div class="recommendation-top">
        <div>
          <p class="section-label">Primary recommendation</p>
          <h3>${recommendation.primary.pipeline.title}</h3>
          <p class="recommendation-text">${recommendation.explanation}</p>
        </div>
        <span class="result-chip ${recommendation.status === "unsupported" || recommendation.status === "closest_supported" ? "is-nearest" : "is-exact"}">${recommendation.statusLabel}</span>
      </div>

      <div class="sub-grid">
        ${renderGeneralizedRouteCard(recommendation)}
        ${renderPublishedBackendCard(recommendation)}
        ${renderReasons(recommendation)}
        ${renderKitConsequencesCard()}
        ${renderActions(recommendation.primary.entryActions)}
        ${renderEntryCard(recommendation)}
        ${renderPreprocessingTable(recommendation.primary.preprocessing)}
        ${renderStructuredList("Required tools", playbook?.required_tools)}
        ${renderStructuredList("Required databases", playbook?.required_databases)}
        ${renderOntReferenceCard(recommendation)}
        ${renderBulletCard("Expected outputs", playbook?.expected_outputs)}
        ${renderWarnings(recommendation)}
        ${renderLinks("Primary documentation", recommendation.primary.pipeline.primary_docs)}
        ${renderLinks("Setup and execution", recommendation.primary.pipeline.setup_docs)}
        ${renderLinks("Evidence links", playbook?.evidence_links)}
        ${recommendation.outOfScopeRule?.read_first_links?.length ? renderLinks("Read first", recommendation.outOfScopeRule.read_first_links) : ""}
      </div>
    </div>
  `;
}

function render() {
  if (!datasets) {
    return;
  }

  renderPresets();
  renderSelector();
  const recommendation = computeRecommendation(answers, datasets);
  renderStatus(recommendation);
  renderResult(recommendation);
}

async function init() {
  if (!allQuestions || !stageComplete || !computeRecommendation) {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "The selector engine could not be loaded. Refresh the page or check that docs/selector-engine.js is available.";
    selectorRoot.innerHTML = `
      <div class="error-box">
        The selector engine is missing. If you are reading the repository source on GitHub, open the GitHub Pages URL instead.
      </div>
    `;
    return;
  }

  try {
    const [pipelines, questionSpec, playbooks, presets, outOfScopeRules] = await Promise.all([
      fetchJson("data/pipelines.json"),
      fetchJson("data/questions.json"),
      fetchJson("data/playbooks.json"),
      fetchJson("data/presets.json"),
      fetchJson("data/out_of_scope.json")
    ]);

    datasets = { pipelines, questionSpec, playbooks, presets, outOfScopeRules };
    answers = normalizeAnswers({});
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
  answers = normalizeAnswers({});
  render();
});

init();
