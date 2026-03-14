const {
  WIZARD_ORDER,
  allQuestions,
  pageById,
  questionById,
  optionFor,
  isQuestionVisible,
  visibleOptionsForQuestion,
  routeComplete,
  pageComplete,
  getEligibleExamples,
  needsExampleSelection,
  resolveSelectedExample,
  getWizardPageSequence,
  canReachPage,
  firstReachablePage,
  computeRecommendation
} = globalThis.SelectorEngine || {};

const progressRoot = document.getElementById("progress-root");
const statusBanner = document.getElementById("status-banner");
const pageRoot = document.getElementById("page-root");
const backButton = document.getElementById("back-button");
const nextButton = document.getElementById("next-button");
const resetButton = document.getElementById("reset-button");

const LIBRARY_DEFAULTS = {
  lsk114: { multiplexing: "no", demultiplexing: "not_needed" },
  rbk114_24: { multiplexing: "yes", demultiplexing: "needed" },
  nbd114_24: { multiplexing: "yes", demultiplexing: "needed" },
  barcoded_metagenome: { multiplexing: "yes", demultiplexing: "needed" }
};

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
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function allDatasetQuestions() {
  return allQuestions(datasets.questionSpec);
}

function labelForValue(questionId, value) {
  const question = questionById(datasets.questionSpec, questionId);
  return optionFor(question, value)?.label || value || "";
}

function routeLabelSummary(answerSet = answers) {
  return [
    labelForValue("sample_context", answerSet.sample_context),
    labelForValue("material_class", answerSet.material_class),
    labelForValue("target_goal", answerSet.target_goal)
  ].filter(Boolean).join(" -> ");
}

function dynamicOptionsForQuestion(question, answerSet = answers) {
  if (question.dynamic_options_from !== "examples") {
    return visibleOptionsForQuestion(datasets.questionSpec, question, answerSet);
  }

  return getEligibleExamples(answerSet, datasets).map((example) => ({
    value: example.id,
    label: example.label,
    help: example.selection_help,
    status_class: example.status_class
  }));
}

function isValidAnswer(question, value, answerSet) {
  return dynamicOptionsForQuestion(question, answerSet).some((option) => option.value === value);
}

function pruneInvalidAnswers(answerSet) {
  const normalized = { ...answerSet };
  let changed = true;

  while (changed) {
    changed = false;

    for (const question of allDatasetQuestions()) {
      const value = normalized[question.id];
      if (!value) {
        continue;
      }

      if (!isQuestionVisible(datasets.questionSpec, question, normalized)) {
        delete normalized[question.id];
        changed = true;
        continue;
      }

      if (!isValidAnswer(question, value, normalized)) {
        delete normalized[question.id];
        changed = true;
      }
    }

    if (!needsExampleSelection(normalized, datasets) && normalized.example_context) {
      delete normalized.example_context;
      changed = true;
    }
  }

  return normalized;
}

function applyLibraryDefaults(answerSet, changedQuestionId) {
  const normalized = { ...answerSet };
  if (changedQuestionId !== "library_mode") {
    return normalized;
  }

  const defaults = LIBRARY_DEFAULTS[normalized.library_mode];
  if (!defaults) {
    return normalized;
  }

  for (const [questionId, value] of Object.entries(defaults)) {
    if (!normalized[questionId] || normalized[questionId] === "unsure") {
      normalized[questionId] = value;
    }
  }

  return normalized;
}

function normalizeAnswers(nextAnswers, changedQuestionId = null) {
  let normalized = { ...nextAnswers };

  if (["sample_context", "material_class", "target_goal"].includes(changedQuestionId)) {
    delete normalized.example_context;
  }

  normalized = pruneInvalidAnswers(normalized);
  normalized = applyLibraryDefaults(normalized, changedQuestionId);
  normalized = pruneInvalidAnswers(normalized);
  return normalized;
}

function pageQuestions(page) {
  return (page.questions || []).filter((question) => isQuestionVisible(datasets.questionSpec, question, answers));
}

function currentPageId() {
  const requested = location.hash.replace(/^#/, "") || "sample";
  if (!WIZARD_ORDER.includes(requested)) {
    return firstReachablePage(datasets.questionSpec, answers, datasets);
  }
  if (!canReachPage(requested, answers, datasets)) {
    return firstReachablePage(datasets.questionSpec, answers, datasets);
  }
  return requested;
}

function syncHash() {
  const pageId = currentPageId();
  const nextHash = `#${pageId}`;
  if (location.hash !== nextHash) {
    history.replaceState(null, "", nextHash);
  }
  return pageId;
}

function navigateTo(pageId) {
  location.hash = `#${pageId}`;
}

function previousPageId(pageId) {
  const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
  const index = sequence.indexOf(pageId);
  if (index <= 0) {
    return null;
  }
  return sequence[index - 1];
}

function nextPageId(pageId) {
  const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
  const index = sequence.indexOf(pageId);
  if (index === -1 || index === sequence.length - 1) {
    return null;
  }
  return sequence[index + 1];
}

function updateStatusBanner(pageId) {
  let tone = "is-idle";
  let text = "Choose one option per step. Repo-specific workflows appear only after the route has been narrowed.";

  if (pageId === "example") {
    const total = getEligibleExamples(answers, datasets).length;
    tone = "is-success";
    text = `${total} published example contexts fit the current route. Choose the closest study context for your case.`;
  } else if (pageId === "expert") {
    tone = "is-success";
    text = "Expert tuning changes preprocessing, tool emphasis, and warnings inside the selected backend. It does not choose a different backend.";
  } else if (pageId === "results") {
    const recommendation = computeRecommendation(answers, datasets);
    tone = recommendation?.status === "unsupported" ? "is-warning" : "is-success";
    text = recommendation?.status_label || text;
  } else if (routeComplete(datasets.questionSpec, answers)) {
    tone = "is-success";
    text = "The generic route is defined. Continue to the study-context and expert pages to finish the recommendation.";
  }

  statusBanner.className = `status-banner ${tone}`;
  statusBanner.textContent = text;
}

function renderProgress(pageId) {
  const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
  progressRoot.innerHTML = `
    <ol class="progress-list">
      ${sequence
        .map((id) => {
          const page = pageById(datasets.questionSpec, id);
          const isCurrent = id === pageId;
          const isComplete = !isCurrent && pageComplete(datasets.questionSpec, answers, id, datasets);
          return `
            <li class="progress-item ${isCurrent ? "is-current" : ""} ${isComplete ? "is-complete" : ""}">
              <button type="button" class="progress-button" data-progress-page="${id}">
                <span class="progress-index">${sequence.indexOf(id) + 1}</span>
                <span class="progress-label">${escapeHtml(page?.title || id)}</span>
              </button>
            </li>
          `;
        })
        .join("")}
    </ol>
  `;

  progressRoot.querySelectorAll("[data-progress-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const targetPage = button.dataset.progressPage;
      if (canReachPage(targetPage, answers, datasets)) {
        navigateTo(targetPage);
      }
    });
  });
}

function renderOptionCard(question, option, checked, context) {
  const inputId = `${question.id}_${option.value}`;
  const badge = option.status_class === "unsupported_nearest"
    ? `<span class="option-badge is-warning">Unsupported -> nearest example</span>`
    : option.status_class === "exact"
      ? `<span class="option-badge">Published example</span>`
      : "";

  return `
    <div class="option-card ${context.cardClass || ""}">
      <input type="radio" name="${question.id}" id="${inputId}" value="${escapeHtml(option.value)}" ${checked ? "checked" : ""} data-question-id="${question.id}">
      <label for="${inputId}">
        ${badge}
        <span class="option-label">${escapeHtml(option.label)}</span>
        ${option.help ? `<span class="option-help">${escapeHtml(option.help)}</span>` : ""}
      </label>
    </div>
  `;
}

function renderQuestion(question, context = {}) {
  const options = dynamicOptionsForQuestion(question);
  const answer = answers[question.id] || "";

  return `
    <section class="question-block ${context.questionClass || ""}">
      <div class="question-head">
        <h3>${escapeHtml(question.label)}</h3>
        ${question.optional ? `<span class="question-badge">Optional</span>` : ""}
      </div>
      ${question.description ? `<p class="question-description">${escapeHtml(question.description)}</p>` : ""}
      <div class="option-grid ${context.gridClass || ""}">
        ${options.map((option) => renderOptionCard(question, option, answer === option.value, context)).join("")}
      </div>
    </section>
  `;
}

function renderSampleMaterialTargetPage(pageId) {
  const page = pageById(datasets.questionSpec, pageId);
  const questions = pageQuestions(page);
  return `
    <section class="wizard-page route-page">
      <div class="page-header">
        <p class="page-kicker">Step ${getWizardPageSequence(datasets.questionSpec, answers, datasets).indexOf(pageId) + 1}</p>
        <h2>${escapeHtml(page.title)}</h2>
        <p>${escapeHtml(page.summary)}</p>
      </div>
      ${questions
        .map((question) =>
          renderQuestion(question, {
            gridClass: "is-route-grid",
            cardClass: "is-route-card"
          })
        )
        .join("")}
    </section>
  `;
}

function renderExamplePage() {
  const page = pageById(datasets.questionSpec, "example");
  const question = pageQuestions(page)[0];
  return `
    <section class="wizard-page">
      <div class="page-header">
        <p class="page-kicker">Published Example Context</p>
        <h2>${escapeHtml(page.title)}</h2>
        <p>${escapeHtml(page.summary)}</p>
      </div>
      ${renderQuestion(question, {
        gridClass: "is-example-grid",
        cardClass: "is-example-card"
      })}
    </section>
  `;
}

function renderExpertPage() {
  const page = pageById(datasets.questionSpec, "expert");
  const questions = pageQuestions(page);
  const sections = [];

  for (const question of questions) {
    const existing = sections.find((section) => section.name === (question.section || "Additional settings"));
    if (existing) {
      existing.questions.push(question);
    } else {
      sections.push({
        name: question.section || "Additional settings",
        questions: [question]
      });
    }
  }

  const recommendation = resolveSelectedExample(answers, datasets);
  const expertIntro = recommendation
    ? `Current example context: ${recommendation.label}`
    : "Finish route selection before expert tuning.";

  return `
    <section class="wizard-page expert-page">
      <div class="page-header">
        <p class="page-kicker">Expert Tuning</p>
        <h2>${escapeHtml(page.title)}</h2>
        <p>${escapeHtml(page.summary)}</p>
      </div>
      <div class="inline-note">${escapeHtml(expertIntro)}</div>
      ${sections
        .map(
          (section) => `
            <section class="expert-section">
              <div class="section-head">
                <h3>${escapeHtml(section.name)}</h3>
              </div>
              <div class="expert-question-stack">
                ${section.questions
                  .map((question) =>
                    renderQuestion(question, {
                      gridClass: "is-expert-grid",
                      cardClass: "is-expert-card"
                    })
                  )
                  .join("")}
              </div>
            </section>
          `
        )
        .join("")}
    </section>
  `;
}

function uniqueLinks(groups) {
  const seen = new Set();
  return groups.flat().filter((link) => {
    if (!link?.url || seen.has(link.url)) {
      return false;
    }
    seen.add(link.url);
    return true;
  });
}

function renderLinks(links) {
  return `
    <ul class="link-list">
      ${links
        .map(
          (link) => `
            <li><a href="${escapeHtml(link.url)}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}</a></li>
          `
        )
        .join("")}
    </ul>
  `;
}

function renderCommands(commands, entryActions) {
  if (commands.length === 0) {
    const entry = entryActions[0];
    if (!entry) {
      return `<p class="muted">No documented command is available for this backend.</p>`;
    }
    return `
      <p class="muted">No copy-ready command is documented for this route. Start from the documented entry point instead.</p>
      <div class="command-fallback">
        <strong>${escapeHtml(entry.title)}</strong>
        <p>${escapeHtml(entry.summary)}</p>
        <a href="${escapeHtml(entry.doc_url)}" target="_blank" rel="noreferrer">${escapeHtml(entry.entry_file)}</a>
      </div>
    `;
  }

  return `
    <div class="command-stack">
      ${commands
        .map(
          (command) => `
            <div class="command-card">
              <div class="command-head">
                <strong>${escapeHtml(command.label)}</strong>
                <a href="${escapeHtml(command.source_url)}" target="_blank" rel="noreferrer">Source</a>
              </div>
              <pre><code>${escapeHtml(command.command)}</code></pre>
              ${command.notes ? `<p class="muted">${escapeHtml(command.notes)}</p>` : ""}
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderDefinitionList(entries) {
  return `
    <dl class="definition-list">
      ${entries
        .map(
          ([label, value]) => `
            <div class="definition-row">
              <dt>${escapeHtml(label)}</dt>
              <dd>${escapeHtml(value || "Not specified")}</dd>
            </div>
          `
        )
        .join("")}
    </dl>
  `;
}

function renderResultsPage() {
  const recommendation = computeRecommendation(answers, datasets);
  if (!recommendation) {
    return `
      <section class="wizard-page">
        <div class="page-header">
          <p class="page-kicker">Results</p>
          <h2>No recommendation yet</h2>
          <p>Complete the route first, then use the expert page if needed before opening the results.</p>
        </div>
      </section>
    `;
  }

  const playbook = recommendation.backend.playbook;
  const backendTitle = recommendation.backend.track
    ? `${recommendation.backend.pipeline.title} (${recommendation.backend.track.title})`
    : recommendation.backend.pipeline.title;
  const links = uniqueLinks([
    recommendation.docs.primary,
    recommendation.docs.setup,
    recommendation.docs.evidence
  ]);
  const preprocessingRows = [
    ["Input expectation", recommendation.preprocessing.input_expectation],
    ["Basecalling", recommendation.preprocessing.basecalling],
    ["Demultiplexing", recommendation.preprocessing.demultiplexing],
    ["Adapter trimming", recommendation.preprocessing.adapter_trimming],
    ["Length / quality filtering", recommendation.preprocessing.length_quality_filtering],
    ["Additional preprocessing", recommendation.preprocessing.additional_preprocessing]
  ].filter(([, value]) => Boolean(value));

  const routeSummary = routeLabelSummary();
  const expertEffectList = recommendation.expert_effects.length > 0
    ? `
        <ul class="detail-list">
          ${recommendation.expert_effects
            .map(
              (effect) => `
                <li>
                  <strong>${escapeHtml(effect.title)}.</strong>
                  ${escapeHtml(effect.summary)}
                </li>
              `
            )
            .join("")}
        </ul>
      `
    : `<p class="muted">No expert overrides were applied. The result uses the base published backend guidance.</p>`;

  const warningsMarkup = recommendation.warnings.length > 0
    ? `
        <ul class="detail-list">
          ${recommendation.warnings
            .map(
              (warning) => `
                <li>
                  <strong>${escapeHtml(warning.title)}.</strong>
                  ${escapeHtml(warning.text)}
                </li>
              `
            )
            .join("")}
        </ul>
      `
    : `<p class="muted">No additional caveats were added for this configuration.</p>`;

  const toolsMarkup = (playbook?.required_tools || []).length > 0
    ? `
        <ul class="detail-list">
          ${playbook.required_tools
            .map((tool) => `<li><strong>${escapeHtml(tool.name)}.</strong> ${escapeHtml(tool.note)}</li>`)
            .join("")}
        </ul>
      `
    : `<p class="muted">No route-specific tool prerequisites were listed.</p>`;

  const databasesMarkup = (playbook?.required_databases || []).length > 0
    ? `
        <ul class="detail-list">
          ${playbook.required_databases
            .map((database) => `<li><strong>${escapeHtml(database.name)}.</strong> ${escapeHtml(database.note)}</li>`)
            .join("")}
        </ul>
      `
    : `<p class="muted">No route-specific database prerequisites were listed.</p>`;

  const ontMarkup = recommendation.ont_notes.length > 0
    ? renderLinks(recommendation.ont_notes.map((note) => ({ label: note.title, url: note.url })))
    : `<p class="muted">No additional Oxford Nanopore reference note is attached to the current expert configuration.</p>`;

  return `
    <section class="wizard-page results-page">
      <div class="page-header">
        <p class="page-kicker">Results</p>
        <h2>Recommended route and backend</h2>
        <p>The final recommendation is built from the generic route, the published example context, and any expert tuning you applied.</p>
      </div>

      <section class="result-hero">
        <div>
          <p class="result-label">Status</p>
          <h3>${escapeHtml(recommendation.status_label)}</h3>
          <p class="result-text">${escapeHtml(recommendation.explanation)}</p>
        </div>
        <span class="result-chip ${recommendation.status === "unsupported" ? "is-warning" : "is-success"}">${escapeHtml(recommendation.status_label)}</span>
      </section>

      <section class="summary-grid">
        <article class="summary-card">
          <p class="summary-label">Recommended generalized route</p>
          <h3>${escapeHtml(routeSummary)}</h3>
          <p>${escapeHtml(recommendation.route.summary)}</p>
        </article>
        <article class="summary-card">
          <p class="summary-label">Published example backend</p>
          <h3>${escapeHtml(backendTitle)}</h3>
          <p>${escapeHtml(recommendation.example.label)}</p>
          ${playbook?.example_badge ? `<span class="inline-badge">${escapeHtml(playbook.example_badge)}</span>` : ""}
        </article>
      </section>

      <section class="result-block">
        <h3>Why this backend was chosen</h3>
        <p>${escapeHtml(recommendation.example.selection_help || recommendation.explanation)}</p>
      </section>

      <section class="result-block">
        <h3>What your expert selections changed</h3>
        ${expertEffectList}
      </section>

      <section class="result-block">
        <h3>What the selected kit changes</h3>
        ${
          recommendation.kit_consequences
            ? renderDefinitionList([
                ["Demultiplexing", recommendation.kit_consequences.demultiplexing],
                ["Barcode trimming", recommendation.kit_consequences.barcode_trimming],
                ["Route shape", recommendation.kit_consequences.route_shape],
                ["First preprocessing changes", recommendation.kit_consequences.first_changes]
              ])
            : `<p class="muted">No kit-specific expert selection was made. Use the expert page if you want kit-driven preprocessing guidance.</p>`
        }
      </section>

      <section class="result-block">
        <h3>Next steps</h3>
        <ol class="step-list">
          ${recommendation.entry_actions
            .map(
              (action) => `
                <li>
                  <strong>${escapeHtml(action.title)}</strong>
                  <p>${escapeHtml(action.summary)}</p>
                  <a href="${escapeHtml(action.doc_url)}" target="_blank" rel="noreferrer">${escapeHtml(action.entry_file)}</a>
                </li>
              `
            )
            .join("")}
        </ol>
      </section>

      <details class="detail-panel" open>
        <summary>Documented entry point / commands</summary>
        ${renderCommands(recommendation.curated_commands, recommendation.entry_actions)}
      </details>

      <details class="detail-panel">
        <summary>Preprocessing defaults</summary>
        ${renderDefinitionList(preprocessingRows)}
      </details>

      <details class="detail-panel">
        <summary>Required tools and databases</summary>
        <div class="two-column-detail">
          <div>
            <h4>Tools</h4>
            ${toolsMarkup}
          </div>
          <div>
            <h4>Databases</h4>
            ${databasesMarkup}
          </div>
        </div>
      </details>

      <details class="detail-panel">
        <summary>Warnings / caveats</summary>
        ${warningsMarkup}
      </details>

      <details class="detail-panel">
        <summary>Oxford Nanopore reference notes</summary>
        ${ontMarkup}
      </details>

      <details class="detail-panel">
        <summary>Documentation links</summary>
        ${renderLinks(links)}
      </details>
    </section>
  `;
}

function attachQuestionListeners() {
  pageRoot.querySelectorAll("[data-question-id]").forEach((input) => {
    input.addEventListener("change", (event) => {
      const questionId = event.target.dataset.questionId;
      answers = normalizeAnswers(
        {
          ...answers,
          [questionId]: event.target.value
        },
        questionId
      );
      render();
    });
  });
}

function renderPage(pageId) {
  if (pageId === "sample" || pageId === "material" || pageId === "target") {
    pageRoot.innerHTML = renderSampleMaterialTargetPage(pageId);
  } else if (pageId === "example") {
    pageRoot.innerHTML = renderExamplePage();
  } else if (pageId === "expert") {
    pageRoot.innerHTML = renderExpertPage();
  } else {
    pageRoot.innerHTML = renderResultsPage();
  }

  attachQuestionListeners();
}

function updateControls(pageId) {
  const previous = previousPageId(pageId);
  const next = nextPageId(pageId);

  backButton.disabled = !previous;
  backButton.hidden = !previous;

  if (pageId === "results") {
    nextButton.hidden = true;
    nextButton.disabled = true;
    nextButton.textContent = "Continue";
    return;
  }

  nextButton.hidden = false;
  nextButton.textContent = pageId === "expert" ? "Show results" : "Continue";

  const complete = pageId === "expert"
    ? canReachPage("results", answers, datasets)
    : pageComplete(datasets.questionSpec, answers, pageId, datasets);
  nextButton.disabled = !complete || !next;

  backButton.onclick = () => {
    if (previous) {
      navigateTo(previous);
    }
  };

  nextButton.onclick = () => {
    if (next) {
      navigateTo(next);
    }
  };
}

function render() {
  if (!datasets || !allQuestions || !computeRecommendation) {
    return;
  }

  const pageId = syncHash();
  renderProgress(pageId);
  updateStatusBanner(pageId);
  renderPage(pageId);
  updateControls(pageId);
}

function renderFatal(error) {
  const message = error instanceof Error ? error.message : String(error);
  statusBanner.className = "status-banner is-warning";
  statusBanner.textContent = `Selector failed to load: ${message}`;
  pageRoot.innerHTML = `
    <section class="wizard-page">
      <div class="page-header">
        <p class="page-kicker">Error</p>
        <h2>Selector unavailable</h2>
        <p>The selector data or runtime could not be loaded. Check the repository files and reload the page.</p>
      </div>
    </section>
  `;
  progressRoot.innerHTML = "";
  backButton.hidden = true;
  nextButton.hidden = true;
}

window.addEventListener("hashchange", () => {
  if (datasets) {
    render();
  }
});

resetButton.addEventListener("click", () => {
  answers = {};
  navigateTo("sample");
});

Promise.all([
  fetchJson("data/questions.json"),
  fetchJson("data/pipelines.json"),
  fetchJson("data/playbooks.json"),
  fetchJson("data/examples.json"),
  fetchJson("data/expert_rules.json")
])
  .then(([questionSpec, pipelines, playbooks, examples, expertRules]) => {
    datasets = {
      questionSpec,
      pipelines,
      playbooks,
      examples,
      expertRules
    };
    render();
  })
  .catch(renderFatal);
