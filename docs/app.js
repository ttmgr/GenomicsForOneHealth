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

function optionFor(question, value) {
  return question.options.find((option) => option.value === value);
}

function isPresetActive(preset) {
  return Object.entries(preset.prefill_answers).every(([key, value]) => answers[key] === value);
}

function renderPresets() {
  const featuredPresets = datasets.presets.filter((preset) => preset.featured);
  presetRoot.innerHTML = `
    <section class="preset-panel">
      <div class="stage-head">
        <div>
          <p class="section-label">Common Starting Scenarios</p>
          <p class="stage-summary">Use a published starting pattern to prefill the selector, then adjust any answer manually.</p>
        </div>
      </div>
      <div class="preset-grid">
        ${featuredPresets
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
  `;

  presetRoot.querySelectorAll("[data-preset-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const preset = datasets.presets.find((entry) => entry.id === button.dataset.presetId);
      answers = { ...preset.prefill_answers };
      render();
    });
  });
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

function renderSelector() {
  selectorRoot.innerHTML = datasets.questionSpec.stages.map(renderStage).join("");

  selectorRoot.querySelectorAll("input[type='radio']").forEach((input) => {
    input.addEventListener("change", (event) => {
      answers[event.target.name] = event.target.value;
      render();
    });
  });
}

function renderStatus(recommendation) {
  if (!stageComplete(datasets.questionSpec, answers, "stage1")) {
    statusBanner.className = "status-banner is-idle";
    statusBanner.textContent = "Answer all Stage 1 questions to narrow the collection to biologically compatible workflows, or start from a preset above.";
    return;
  }

  if (!recommendation) {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "The selector could not derive a recommendation from the current answers.";
    return;
  }

  if (recommendation.status === "unsupported") {
    statusBanner.className = "status-banner is-warning";
    statusBanner.textContent = "This scenario falls outside the currently published collection. The selector is showing the nearest documented starting point without claiming exact support.";
    return;
  }

  if (recommendation.status === "closest_supported") {
    statusBanner.className = recommendation.confidence === "low" ? "status-banner is-warning" : "status-banner is-success";
    statusBanner.textContent = "No exact workflow matches all Stage 1 answers. The selector is showing the nearest documented starting point and the most relevant next actions.";
    return;
  }

  if (recommendation.decision_trace.exactCandidateCount > 1) {
    statusBanner.className = "status-banner is-success";
    statusBanner.textContent = `${recommendation.decision_trace.exactCandidateCount} exact current workflows remain after Stage 1. The action sheet below shows the strongest practical fit and nearby alternatives.`;
    return;
  }

  statusBanner.className = "status-banner is-success";
  statusBanner.textContent = "One exact current workflow matches your biological and analytical criteria. Use the action sheet below to start at the correct entry point.";
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

function renderBulletCard(title, items, className = "detail-list") {
  if (!items || items.length === 0) {
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

function renderStructuredList(title, items) {
  if (!items || items.length === 0) {
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

function renderActions(actions) {
  if (!actions || actions.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">What to Do Next</p>
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
  const playbook = recommendation.primary.playbook;
  const fallbackAction = recommendation.primary.entryActions[0];
  const supportedEntryPoints = recommendation.primary.pipeline.supported_entry_points || [];

  if (!command && !fallbackAction && supportedEntryPoints.length === 0) {
    return "";
  }

  const additionalCommands = recommendation.primary.curatedCommands.slice(1, 3);

  return `
    <div class="sub-card">
      <p class="section-label">Entry Point and Curated Command</p>
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
      ${
        playbook?.required_inputs?.length
          ? `
            <div class="resource-list compact">
              ${playbook.required_inputs
                .map(
                  (input) => `
                    <div class="resource-item">
                      <strong>Required input</strong>
                      <span>${input}</span>
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

function renderConfidenceCard(recommendation) {
  const readiness = recommendation.primary.pipeline.readiness_level.replaceAll("_", " ");

  return `
    <div class="sub-card">
      <p class="section-label">Confidence and Fit</p>
      <div class="chip-row">
        <span class="result-chip ${recommendation.status === "unsupported" ? "is-nearest" : "is-exact"}">${recommendation.statusLabel}</span>
        <span class="result-chip confidence-${recommendation.confidence}">${recommendation.confidenceLabel} confidence</span>
      </div>
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

function renderReasons(recommendation) {
  if (!recommendation.decision_trace.reasons.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Why this matched</p>
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

function renderWarnings(recommendation) {
  const warnings = recommendation.warnings || [];
  if (warnings.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">${recommendation.status === "unsupported" ? "Unsupported / Partial-Fit Warning" : "Warnings and Compatibility Notes"}</p>
      <div class="warning-list">
        ${warnings
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
  `;
}

function renderTrackCard(recommendation) {
  const track = recommendation.primary.track;
  const playbook = recommendation.primary.playbook;
  if (!track && !playbook) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Branch-Specific Notes</p>
      ${
        track
          ? `
            <h4>${track.title}</h4>
            <p>${track.summary}</p>
          `
          : ""
      }
      ${playbook?.recommended_when?.length ? `<p><strong>Best used when:</strong> ${playbook.recommended_when.join(" ")}</p>` : ""}
      ${playbook?.avoid_when?.length ? `<p><strong>Avoid when:</strong> ${playbook.avoid_when.join(" ")}</p>` : ""}
      ${playbook?.runtime_notes?.length ? `<ul class="detail-list">${playbook.runtime_notes.map((note) => `<li>${note}</li>`).join("")}</ul>` : ""}
    </div>
  `;
}

function renderOntReferenceCard(recommendation) {
  if (!recommendation.ontNotes || recommendation.ontNotes.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Oxford Nanopore Reference</p>
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

function renderAlternatives(recommendation) {
  const shouldShow = recommendation.status === "unsupported" || recommendation.confidence !== "high" || recommendation.decision_trace.exactCandidateCount > 1;
  if (!shouldShow || !recommendation.alternatives.length) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Closest Alternatives</p>
      <div class="resource-list">
        ${recommendation.alternatives
          .map(
            (pipeline) => `
              <div class="resource-item">
                <strong>${pipeline.title}</strong>
                <span>${(pipeline.decision_notes || pipeline.notes || []).slice(0, 1).join(" ")}</span>
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
        <p class="empty-text">Answer the Stage 1 questions or apply a preset to generate the lab-ready action sheet.</p>
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
        ${renderConfidenceCard(recommendation)}
        ${renderTrackCard(recommendation)}
        ${renderActions(recommendation.primary.entryActions)}
        ${renderEntryCard(recommendation)}
        ${renderPreprocessingTable(recommendation.primary.preprocessing)}
        ${renderOntReferenceCard(recommendation)}
        ${renderStructuredList("Required Tools", playbook?.required_tools)}
        ${renderStructuredList("Required Databases", playbook?.required_databases)}
        ${renderBulletCard("Expected Outputs", playbook?.expected_outputs, "detail-list")}
        ${renderReasons(recommendation)}
        ${renderWarnings(recommendation)}
        ${renderAlternatives(recommendation)}
        ${renderLinks("Primary documentation", recommendation.primary.pipeline.primary_docs)}
        ${renderLinks("Setup and execution", recommendation.primary.pipeline.setup_docs)}
        ${renderLinks("Evidence links", playbook?.evidence_links)}
        ${
          recommendation.outOfScopeRule?.read_first_links?.length
            ? renderLinks("Read first", recommendation.outOfScopeRule.read_first_links)
            : ""
        }
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
  if (!stageComplete || !computeRecommendation) {
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
