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

function linkHref(url) {
  if (!url) {
    return "#";
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return url.replace(/^docs\//, "");
}

function datasetQuestions() {
  return allQuestions(datasets.questionSpec);
}

function dynamicOptionsForQuestion(question, answerSet = answers) {
  if (question.dynamic_options_from !== "examples") {
    return visibleOptionsForQuestion(datasets.questionSpec, question, answerSet);
  }

  return getEligibleExamples(answerSet, datasets).map((example) => ({
    value: example.id,
    label: example.label,
    help: example.selection_help,
    status_class: example.status_class,
    unsupported_reason: example.unsupported_reason
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

    for (const question of datasetQuestions()) {
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

function normalizeAnswers(nextAnswers, changedQuestionId = null) {
  const normalized = pruneInvalidAnswers(nextAnswers);

  if (["sample_context", "material_class", "target_goal"].includes(changedQuestionId)) {
    delete normalized.example_context;
  }

  return pruneInvalidAnswers(normalized);
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

function pageQuestions(pageId) {
  const page = pageById(datasets.questionSpec, pageId);
  return (page?.questions || []).filter((question) => isQuestionVisible(datasets.questionSpec, question, answers));
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

function setupGuideLink() {
  return `
    <a class="learn-link" href="nanopore-guide.html" target="_blank" rel="noreferrer">
      Learn why
    </a>
  `;
}

function phaseForPage(pageId) {
  if (["sample", "material", "target", "example"].includes(pageId)) {
    return "Route";
  }
  if (["setup", "kit", "flowcell", "basecalling", "analysis", "conditions"].includes(pageId)) {
    return "Nanopore Setup";
  }
  return "Results";
}

function updateStatusBanner(pageId) {
  const recommendation = pageId === "results" ? computeRecommendation(answers, datasets) : null;

  if (pageId === "results" && recommendation) {
    statusBanner.className = `status-banner ${recommendation.status === "unsupported" ? "is-warning" : "is-success"}`;
    statusBanner.textContent = recommendation.status_label;
    return;
  }

  if (["setup", "kit", "flowcell", "basecalling", "analysis", "conditions"].includes(pageId)) {
    statusBanner.className = "status-banner is-success";
    statusBanner.textContent = "Setup pages refine kit, flow cell, basecalling, and analysis environment without changing the selected backend.";
    return;
  }

  if (pageId === "example") {
    statusBanner.className = "status-banner is-success";
    statusBanner.textContent = "Choose the closest published study context. Unsupported options stay visible instead of being hidden behind a false exact match.";
    return;
  }

  statusBanner.className = "status-banner is-idle";
  statusBanner.textContent = "Start sparse: sample, material, and target first. Repo-specific backends appear later.";
}

function renderProgress(pageId) {
  const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
  progressRoot.innerHTML = `
    <div class="phase-strip">
      <span class="phase-pill ${phaseForPage(pageId) === "Route" ? "is-current" : ""}">Route</span>
      <span class="phase-pill ${phaseForPage(pageId) === "Nanopore Setup" ? "is-current" : ""}">Nanopore setup</span>
      <span class="phase-pill ${phaseForPage(pageId) === "Results" ? "is-current" : ""}">Results</span>
    </div>
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

function kitProfile(option) {
  return datasets.nanoporeProfiles.kits.find((profile) => profile.id === option.value) || null;
}

function flowcellProfile(option) {
  return datasets.nanoporeProfiles.flow_cells.find((profile) => profile.id === option.value) || null;
}

function basecallingProfile(option) {
  return datasets.nanoporeProfiles.basecalling_profiles.find((profile) => profile.id === option.value) || null;
}

function renderOptionCard(question, option, checked, context = {}) {
  const inputId = `${question.id}_${option.value}`;
  let metaMarkup = "";

  if (question.id === "library_mode") {
    const profile = kitProfile(option);
    if (profile) {
      metaMarkup = `
        <ul class="card-facts">
          <li><strong>Demux:</strong> ${escapeHtml(profile.consequences.demultiplexing)}</li>
          <li><strong>Barcode trimming:</strong> ${escapeHtml(profile.consequences.barcode_trimming)}</li>
          <li><strong>Typical use:</strong> ${escapeHtml(profile.consequences.typical_use)}</li>
          <li><strong>Route implication:</strong> ${escapeHtml(profile.consequences.route_implication)}</li>
        </ul>
      `;
    }
  } else if (question.id === "flowcell_family") {
    const profile = flowcellProfile(option);
    if (profile) {
      metaMarkup = `<p class="option-meta">${escapeHtml(profile.summary)}</p>`;
    }
  } else if (question.id === "basecalling_goal") {
    const profile = basecallingProfile(option);
    if (profile) {
      metaMarkup = `<p class="option-meta">${escapeHtml(profile.summary)}</p>`;
    }
  } else if (question.id === "analysis_environment" && option.value === "cz_id") {
    metaMarkup = `<p class="option-meta">Cloud-first long-read metagenomic interpretation.</p>`;
  } else if (question.id === "analysis_environment" && option.value === "epi2me_labs") {
    metaMarkup = `<p class="option-meta">ONT-curated local workflows for isolate, metagenomic, and amplicon routes.</p>`;
  }

  const badge = option.status_class === "unsupported_nearest"
    ? `<span class="option-badge is-warning">Unsupported</span>`
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
        ${option.unsupported_reason ? `<span class="option-warning">${escapeHtml(option.unsupported_reason)}</span>` : ""}
        ${metaMarkup}
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
        <div>
          <h3>${escapeHtml(question.label)}</h3>
          ${question.description ? `<p class="question-description">${escapeHtml(question.description)}</p>` : ""}
        </div>
        ${context.showGuideLink ? setupGuideLink() : ""}
      </div>
      <div class="option-grid ${context.gridClass || ""}">
        ${options.map((option) => renderOptionCard(question, option, answer === option.value, context)).join("")}
      </div>
    </section>
  `;
}

function renderPageHeader(pageId) {
  const page = pageById(datasets.questionSpec, pageId);
  const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
  const index = sequence.indexOf(pageId) + 1;

  return `
    <div class="page-header">
      <div class="page-header-top">
        <p class="page-kicker">Step ${index}</p>
        <span class="inline-badge">${escapeHtml(phaseForPage(pageId))}</span>
      </div>
      <h2>${escapeHtml(page.title)}</h2>
      <p>${escapeHtml(page.summary)}</p>
    </div>
  `;
}

function renderRoutePage(pageId) {
  const questions = pageQuestions(pageId);
  return `
    <section class="wizard-page">
      ${renderPageHeader(pageId)}
      ${questions.map((question) => renderQuestion(question, { gridClass: "is-route-grid", cardClass: "is-route-card" })).join("")}
    </section>
  `;
}

function renderExamplePage() {
  const question = pageQuestions("example")[0];
  return `
    <section class="wizard-page">
      ${renderPageHeader("example")}
      ${renderQuestion(question, { gridClass: "is-example-grid", cardClass: "is-example-card" })}
    </section>
  `;
}

function renderSetupIntroPage() {
  const example = resolveSelectedExample(answers, datasets);
  return `
    <section class="wizard-page">
      ${renderPageHeader("setup")}
      <div class="setup-intro">
        <p class="setup-route-label">Route defined</p>
        <h3>${escapeHtml(routeLabelSummary())}</h3>
        <p>
          ${escapeHtml(example ? `Closest published example: ${example.label}.` : "The route is ready for setup refinement.")}
        </p>
        <p>
          Next, refine the Nanopore setup and analysis environment. These pages do not change the selected backend.
        </p>
        <div class="setup-links">
          ${setupGuideLink()}
        </div>
      </div>
    </section>
  `;
}

function renderSetupQuestionPage(pageId) {
  const questions = pageQuestions(pageId);
  const question = questions[0];
  return `
    <section class="wizard-page">
      ${renderPageHeader(pageId)}
      ${renderQuestion(question, {
        gridClass: pageId === "kit" ? "is-kit-grid" : "is-route-grid",
        cardClass: pageId === "kit" ? "is-kit-card" : "is-route-card",
        showGuideLink: true
      })}
    </section>
  `;
}

function renderConditionControl(question) {
  const answer = answers[question.id] || "";
  return `
    <article class="condition-card">
      <div class="condition-copy">
        <h3>${escapeHtml(question.label)}</h3>
        <p>${escapeHtml(question.description || "")}</p>
      </div>
      <div class="condition-toggle">
        ${question.options
          .map((option) => {
            const inputId = `${question.id}_${option.value}`;
            return `
              <input type="radio" id="${inputId}" name="${question.id}" value="${escapeHtml(option.value)}" ${answer === option.value ? "checked" : ""} data-question-id="${question.id}">
              <label class="toggle-pill ${answer === option.value ? "is-selected" : ""}" for="${inputId}">
                <span>${escapeHtml(option.label)}</span>
                <small>${escapeHtml(option.help)}</small>
              </label>
            `;
          })
          .join("")}
      </div>
    </article>
  `;
}

function renderConditionsPage() {
  const questions = pageQuestions("conditions");
  const sectionNames = [...new Set(questions.map((question) => question.section).filter(Boolean))];

  return `
    <section class="wizard-page">
      ${renderPageHeader("conditions")}
      <div class="condition-note">
        <p>Keep this page short. Leave any toggle untouched if you do not know the answer.</p>
        ${setupGuideLink()}
      </div>
      ${sectionNames
        .map((sectionName) => {
          const sectionQuestions = questions.filter((question) => question.section === sectionName);
          return `
            <section class="conditions-section">
              <div class="section-head">
                <h3>${escapeHtml(sectionName)}</h3>
              </div>
              <div class="condition-stack">
                ${sectionQuestions.map(renderConditionControl).join("")}
              </div>
            </section>
          `;
        })
        .join("")}
    </section>
  `;
}

function renderLinks(links) {
  if (!links.length) {
    return `<p class="muted">No documentation links are attached to this section.</p>`;
  }

  return `
    <ul class="link-list">
      ${links
        .map(
          (link) => `
            <li><a href="${escapeHtml(linkHref(link.url))}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}</a></li>
          `
        )
        .join("")}
    </ul>
  `;
}

function renderDefinitionList(entries) {
  if (entries.length === 0) {
    return `<p class="muted">No structured details were attached for this section.</p>`;
  }

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

function renderCommands(commands) {
  if (!commands.length) {
    return `<p class="muted">No copy-ready internal command is attached to this backend.</p>`;
  }

  return `
    <div class="command-stack">
      ${commands
        .map(
          (command) => `
            <article class="command-card">
              <div class="command-head">
                <strong>${escapeHtml(command.label)}</strong>
                <a href="${escapeHtml(linkHref(command.source_url))}" target="_blank" rel="noreferrer">Source</a>
              </div>
              <pre><code>${escapeHtml(command.command)}</code></pre>
              ${command.notes ? `<p class="muted">${escapeHtml(command.notes)}</p>` : ""}
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderExternalWorkflows(recommendation) {
  if (!recommendation.external_fallbacks.length) {
    return `<p class="muted">No external workflow options were surfaced for this route.</p>`;
  }

  const heading = recommendation.status === "unsupported"
    ? "External fallback options"
    : "Alternative analysis environments";

  return `
    <section class="result-block">
      <h3>${heading}</h3>
      <div class="external-grid">
        ${recommendation.external_fallbacks
          .map(
            (workflow) => `
              <article class="external-card">
                <div class="external-head">
                  <h4>${escapeHtml(workflow.label)}</h4>
                  <span class="option-badge ${workflow.emphasis === "fallback" ? "is-warning" : ""}">
                    ${workflow.emphasis === "fallback" ? "Fallback" : "Alternative"}
                  </span>
                </div>
                <p>${escapeHtml((workflow.recommended_when || [])[0] || "")}</p>
                <a href="${escapeHtml(workflow.url)}" target="_blank" rel="noreferrer">Open workflow docs</a>
              </article>
            `
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderResultsPage() {
  const recommendation = computeRecommendation(answers, datasets);
  if (!recommendation) {
    return `
      <section class="wizard-page">
        ${renderPageHeader("results")}
        <p class="muted">Complete the route and setup pages before opening the results.</p>
      </section>
    `;
  }

  const backendTitle = recommendation.backend.track
    ? `${recommendation.backend.pipeline.title} (${recommendation.backend.track.title})`
    : recommendation.backend.pipeline.title;

  const preprocessingRows = [
    ["Input expectation", recommendation.preprocessing.input_expectation],
    ["Basecalling", recommendation.preprocessing.basecalling],
    ["Demultiplexing", recommendation.preprocessing.demultiplexing],
    ["Adapter trimming", recommendation.preprocessing.adapter_trimming],
    ["Length / quality filtering", recommendation.preprocessing.length_quality_filtering],
    ["Additional preprocessing", recommendation.preprocessing.additional_preprocessing]
  ].filter(([, value]) => Boolean(value));

  const tools = recommendation.backend.playbook.required_tools || [];
  const databases = recommendation.backend.playbook.required_databases || [];

  return `
    <section class="wizard-page results-page">
      ${renderPageHeader("results")}

      <section class="result-hero">
        <div>
          <p class="result-label">Recommendation status</p>
          <h3>${escapeHtml(recommendation.status_label)}</h3>
          <p class="result-text">${escapeHtml(recommendation.explanation)}</p>
        </div>
        <span class="result-chip ${recommendation.status === "unsupported" ? "is-warning" : "is-success"}">${escapeHtml(recommendation.status_label)}</span>
      </section>

      <section class="summary-grid">
        <article class="summary-card">
          <p class="summary-label">Generalized route</p>
          <h3>${escapeHtml(routeLabelSummary())}</h3>
          <p>${escapeHtml(recommendation.route.summary)}</p>
        </article>
        <article class="summary-card">
          <p class="summary-label">Published example backend</p>
          <h3>${escapeHtml(backendTitle)}</h3>
          <p>${escapeHtml(recommendation.example.selection_help || recommendation.example.label)}</p>
        </article>
        <article class="summary-card">
          <p class="summary-label">Nanopore setup recommendation</p>
          <h3>${escapeHtml(recommendation.setup_summary.recommendation)}</h3>
          <p>${escapeHtml(recommendation.setup_summary.result_note || "Setup defaults were resolved from the selected route.")}</p>
          <p class="summary-meta">Primary environment: ${escapeHtml(recommendation.analysis_environment.label)}</p>
        </article>
      </section>

      <section class="result-block">
        <h3>Why this was chosen</h3>
        <p>${escapeHtml(recommendation.example.selection_help || recommendation.explanation)}</p>
        ${recommendation.example.unsupported_reason ? `<p class="warning-inline">${escapeHtml(recommendation.example.unsupported_reason)}</p>` : ""}
      </section>

      <section class="result-block">
        <h3>What your conditions changed</h3>
        ${
          recommendation.expert_effects.length > 0
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
            : `<p class="muted">No extra condition-based changes were applied.</p>`
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
                  <a href="${escapeHtml(linkHref(action.doc_url))}" target="_blank" rel="noreferrer">${escapeHtml(action.entry_file)}</a>
                </li>
              `
            )
            .join("")}
        </ol>
      </section>

      ${renderExternalWorkflows(recommendation)}

      <details class="detail-panel" open>
        <summary>Documented commands and docs</summary>
        ${renderCommands(recommendation.curated_commands)}
        ${renderLinks(recommendation.docs.primary)}
      </details>

      <details class="detail-panel">
        <summary>Expandable details</summary>
        <div class="detail-group">
          <h4>Preprocessing defaults</h4>
          ${renderDefinitionList(preprocessingRows)}
        </div>
        <div class="detail-group">
          <h4>Kit consequences</h4>
          ${
            recommendation.kit_consequences
              ? renderDefinitionList([
                  ["Demultiplexing", recommendation.kit_consequences.demultiplexing],
                  ["Barcode trimming", recommendation.kit_consequences.barcode_trimming],
                  ["Route shape", recommendation.kit_consequences.route_shape],
                  ["Early preprocessing shift", recommendation.kit_consequences.first_changes]
                ])
              : `<p class="muted">No kit-specific consequences were attached.</p>`
          }
        </div>
        <div class="detail-group">
          <h4>Warnings / caveats</h4>
          ${
            recommendation.warnings.length > 0
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
              : `<p class="muted">No extra caveats were attached.</p>`
          }
        </div>
        <div class="detail-group two-column-detail">
          <div>
            <h4>Required tools</h4>
            ${
              tools.length > 0
                ? `<ul class="detail-list">${tools.map((tool) => `<li><strong>${escapeHtml(tool.name)}.</strong> ${escapeHtml(tool.note)}</li>`).join("")}</ul>`
                : `<p class="muted">No route-specific tool list was attached.</p>`
            }
          </div>
          <div>
            <h4>Required databases</h4>
            ${
              databases.length > 0
                ? `<ul class="detail-list">${databases.map((database) => `<li><strong>${escapeHtml(database.name)}.</strong> ${escapeHtml(database.note)}</li>`).join("")}</ul>`
                : `<p class="muted">No route-specific database list was attached.</p>`
            }
          </div>
        </div>
        <div class="detail-group">
          <h4>Guide and setup links</h4>
          ${renderLinks(recommendation.guide_links.map((link) => ({ label: link.title, url: link.url })))}
        </div>
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
  if (["sample", "material", "target"].includes(pageId)) {
    pageRoot.innerHTML = renderRoutePage(pageId);
  } else if (pageId === "example") {
    pageRoot.innerHTML = renderExamplePage();
  } else if (pageId === "setup") {
    pageRoot.innerHTML = renderSetupIntroPage();
  } else if (["kit", "flowcell", "basecalling", "analysis"].includes(pageId)) {
    pageRoot.innerHTML = renderSetupQuestionPage(pageId);
  } else if (pageId === "conditions") {
    pageRoot.innerHTML = renderConditionsPage();
  } else {
    pageRoot.innerHTML = renderResultsPage();
  }

  attachQuestionListeners();
}

function updateControls(pageId) {
  const previous = previousPageId(pageId);
  const next = nextPageId(pageId);

  backButton.hidden = !previous;
  backButton.disabled = !previous;
  backButton.onclick = () => {
    if (previous) {
      navigateTo(previous);
    }
  };

  if (pageId === "results") {
    nextButton.hidden = true;
    nextButton.disabled = true;
    return;
  }

  nextButton.hidden = false;
  nextButton.textContent = pageId === "conditions" ? "Show results" : "Continue";
  nextButton.disabled = !next || !pageComplete(datasets.questionSpec, answers, pageId, datasets);
  nextButton.onclick = () => {
    if (next) {
      navigateTo(next);
    }
  };
}

function render() {
  if (!datasets || !computeRecommendation) {
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
  progressRoot.innerHTML = "";
  pageRoot.innerHTML = `
    <section class="wizard-page">
      <div class="page-header">
        <p class="page-kicker">Error</p>
        <h2>Selector unavailable</h2>
        <p>The selector runtime or data could not be loaded. Check the repository files and reload the page.</p>
      </div>
    </section>
  `;
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
  fetchJson("data/expert_rules.json"),
  fetchJson("data/nanopore_profiles.json"),
  fetchJson("data/external_workflows.json")
])
  .then(([questionSpec, pipelines, playbooks, examples, expertRules, nanoporeProfiles, externalWorkflows]) => {
    datasets = {
      questionSpec,
      pipelines,
      playbooks,
      examples,
      expertRules,
      nanoporeProfiles,
      externalWorkflows
    };
    render();
  })
  .catch(renderFatal);
