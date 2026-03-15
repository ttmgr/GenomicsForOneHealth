/* ──────────────────────────────────────────────────────────────
   app.js — Advisor UI
   Renders questions, live recommendation card, and rationale pane.
   Uses recommendation-engine.js for pure decision logic.
   ────────────────────────────────────────────────────────────── */

// ── DOM refs ────────────────────────────────────────────────

const progressRoot = document.getElementById("progress-root");
const pageRoot = document.getElementById("page-root");
const backButton = document.getElementById("back-button");
const nextButton = document.getElementById("next-button");
const resetButton = document.getElementById("reset-button");

// Recommendation card slots
const recCard = document.getElementById("rec-card");
const recConfidence = document.getElementById("rec-confidence");
const recWorkflow = document.getElementById("rec-workflow");
const recKit = document.getElementById("rec-kit");
const recKitMeta = document.getElementById("rec-kit-meta");
const recBasecalling = document.getElementById("rec-basecalling");
const recBasecallingMeta = document.getElementById("rec-basecalling-meta");
const recPipeline = document.getElementById("rec-pipeline");
const recPipelineMeta = document.getElementById("rec-pipeline-meta");
const recRationale = document.getElementById("rec-rationale");
const recWarnings = document.getElementById("rec-warnings");

// Rationale pane
const rationaleAlt = document.getElementById("rationale-alternative");
const rationaleAltContent = document.getElementById("rationale-alt-content");
const rationaleCommands = document.getElementById("rationale-commands");
const rationaleCommandsContent = document.getElementById("rationale-commands-content");
const rationaleChecklist = document.getElementById("rationale-checklist");
const rationaleChecklistContent = document.getElementById("rationale-checklist-content");
const rationaleProtocols = document.getElementById("rationale-protocols");
const rationaleProtocolsContent = document.getElementById("rationale-protocols-content");
const rationalePlaceholder = document.getElementById("rationale-placeholder");

// ── State ───────────────────────────────────────────────────

let datasets = null;
let answers = {};
let lastRecommendation = null;

// ── Utilities ───────────────────────────────────────────────

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
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
  if (!url) return "#";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return url.replace(/^docs\//, "");
}

// ── Progress bar ────────────────────────────────────────────

function renderProgress(currentPageId) {
  const pages = getPageSequence();
  const currentIdx = pages.indexOf(currentPageId);

  progressRoot.innerHTML = `
    <div class="progress-steps">
      ${pages
        .filter(p => p !== 'results')
        .map((id, i) => {
          const page = datasets.questionSpec.pages.find(p => p.id === id);
          const isCurrent = id === currentPageId;
          const isDone = i < currentIdx;
          const label = page?.title || id;
          return `
            <button type="button"
              class="progress-step ${isCurrent ? 'is-current' : ''} ${isDone ? 'is-complete' : ''}"
              data-progress-page="${id}"
              ${!isDone && !isCurrent ? 'disabled' : ''}>
              <span class="progress-index">${i + 1}</span>
              <span class="progress-label">${escapeHtml(label)}</span>
            </button>
          `;
        })
        .join('<span class="progress-connector"></span>')}
    </div>
  `;

  progressRoot.querySelectorAll("[data-progress-page]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.progressPage;
      if (canReachPage(target, answers, datasets.questionSpec)) {
        navigateTo(target);
      }
    });
  });
}

// ── Question rendering ──────────────────────────────────────

function visibleOptions(question) {
  return (question.options || []).filter(
    opt => !opt.visible_when || matchesWhen(opt.visible_when, answers)
  );
}

function renderRadioQuestion(question, options) {
  const answer = answers[question.field] || "";
  return `
    <div class="option-grid is-route-grid">
      ${options.map(opt => {
        const inputId = `${question.id}_${opt.value}`;
        const checked = answer === opt.value;
        return `
          <div class="option-card is-route-card">
            <input type="radio" name="${question.id}" id="${inputId}"
              value="${escapeHtml(opt.value)}" ${checked ? "checked" : ""}
              data-question-id="${question.id}" data-field="${question.field}">
            <label for="${inputId}">
              <span class="option-label">${escapeHtml(opt.label)}</span>
              ${opt.help ? `<span class="option-help">${escapeHtml(opt.help)}</span>` : ""}
            </label>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderMultiSelectQuestion(question, options) {
  const selected = answers[question.field] || [];
  return `
    <div class="option-grid is-priority-grid">
      ${options.map(opt => {
        const inputId = `${question.id}_${opt.value}`;
        const checked = selected.includes(opt.value);
        return `
          <div class="option-card is-priority-card">
            <input type="checkbox" name="${question.id}" id="${inputId}"
              value="${escapeHtml(opt.value)}" ${checked ? "checked" : ""}
              data-question-id="${question.id}" data-field="${question.field}" data-multi="true">
            <label for="${inputId}">
              <span class="option-label">${escapeHtml(opt.label)}</span>
              ${opt.help ? `<span class="option-help">${escapeHtml(opt.help)}</span>` : ""}
            </label>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderConstraintQuestion(question) {
  const answer = answers[question.field] || "";
  return `
    <article class="constraint-card">
      <div class="constraint-copy">
        <h4>${escapeHtml(question.label)}</h4>
      </div>
      <div class="constraint-toggle">
        ${(question.options || []).map(opt => {
          const inputId = `${question.id}_${opt.value}`;
          const checked = answer === opt.value;
          return `
            <input type="radio" id="${inputId}" name="${question.id}"
              value="${escapeHtml(opt.value)}" ${checked ? "checked" : ""}
              data-question-id="${question.id}" data-field="${question.field}">
            <label class="toggle-pill ${checked ? "is-selected" : ""}" for="${inputId}">
              <span>${escapeHtml(opt.label)}</span>
              <small>${escapeHtml(opt.help)}</small>
            </label>
          `;
        }).join("")}
      </div>
    </article>
  `;
}

function renderPage(pageId) {
  const page = datasets.questionSpec.pages.find(p => p.id === pageId);
  if (!page) return;

  const pages = getPageSequence();
  const stepNum = pages.indexOf(pageId) + 1;

  if (pageId === "results") {
    pageRoot.innerHTML = renderResultsPage();
    attachCopyButtons();
    return;
  }

  let questionsHtml = "";

  if (page.page_type === "constraints") {
    const sections = {};
    for (const q of page.questions || []) {
      const sec = q.section || "general";
      if (!sections[sec]) sections[sec] = [];
      sections[sec].push(q);
    }

    questionsHtml = Object.entries(sections).map(([sectionName, questions]) => `
      <div class="constraints-section">
        <h3 class="section-head-label">${escapeHtml(sectionName)}</h3>
        <div class="constraint-stack">
          ${questions.map(renderConstraintQuestion).join("")}
        </div>
      </div>
    `).join("");
  } else {
    for (const q of page.questions || []) {
      const opts = visibleOptions(q);
      if (opts.length === 0) continue;
      if (q.question_type === "multi_select") {
        questionsHtml += renderMultiSelectQuestion(q, opts);
      } else {
        questionsHtml += renderRadioQuestion(q, opts);
      }
    }
  }

  pageRoot.innerHTML = `
    <section class="wizard-page">
      <div class="page-header">
        <p class="page-kicker">Step ${stepNum}</p>
        <h2>${escapeHtml(page.title)}</h2>
        <p>${escapeHtml(page.summary)}</p>
      </div>
      ${questionsHtml}
    </section>
  `;

  attachQuestionListeners();
}

// ── Results page ────────────────────────────────────────────

function renderResultsPage() {
  const rec = lastRecommendation;
  if (!rec || !rec.kit) {
    return `
      <section class="wizard-page">
        <div class="page-header">
          <h2>Your recommendation</h2>
          <p class="muted">Answer more questions to generate a recommendation.</p>
        </div>
      </section>
    `;
  }

  const kitInfo = rec.kitInfo || {};
  const bcInfo = rec.basecallingInfo || {};
  const plInfo = rec.pipelineInfo || {};

  return `
    <section class="wizard-page results-page">
      <div class="page-header">
        <div class="page-header-top">
          <p class="page-kicker">Your recommendation</p>
          <span class="confidence-badge is-inline" data-level="${rec.confidence}">
            <span class="confidence-dot"></span>
            <span class="confidence-label">${confidenceLabel(rec.confidence)}</span>
          </span>
        </div>
        <h2>${escapeHtml(rec.workflow || 'Sequencing workflow')}</h2>
      </div>

      <div class="result-cards">
        <div class="result-rec-card">
          <p class="result-label">Kit</p>
          <h3>${escapeHtml(kitInfo.label || rec.kit)}</h3>
          <p class="result-text">${escapeHtml(kitInfo.sku || '')}</p>
          ${kitInfo.prep_time ? `<p class="result-text">Prep: ${escapeHtml(kitInfo.prep_time)} · Input: ${escapeHtml(kitInfo.input_range || '—')}</p>` : ''}
          ${kitInfo.url ? `<a href="${escapeHtml(kitInfo.url)}" target="_blank" rel="noreferrer" class="result-link">Open protocol</a>` : ''}
        </div>

        <div class="result-rec-card">
          <p class="result-label">Basecalling</p>
          <h3>${escapeHtml(bcInfo.label || rec.basecalling)}</h3>
          <p class="result-text">${escapeHtml(bcInfo.description || '')}</p>
          <p class="result-text">Accuracy: ${escapeHtml(bcInfo.accuracy || '—')} · Compute: ${escapeHtml(bcInfo.compute || '—')}</p>
        </div>

        <div class="result-rec-card">
          <p class="result-label">Analysis pipeline</p>
          <h3>${escapeHtml(plInfo.label || rec.pipeline || '—')}</h3>
          <p class="result-text">${escapeHtml(plInfo.description || '')}</p>
          ${plInfo.docs_url ? `<a href="${escapeHtml(plInfo.docs_url)}" target="_blank" rel="noreferrer" class="result-link">Documentation</a>` : ''}
          ${plInfo.url ? `<a href="${escapeHtml(plInfo.url)}" target="_blank" rel="noreferrer" class="result-link">GitHub</a>` : ''}
        </div>
      </div>

      ${rec.rationale.length > 0 ? `
        <div class="result-block">
          <h3>Why this is the best fit</h3>
          <ul class="detail-list">
            ${rec.rationale.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      ${rec.warnings.length > 0 ? `
        <div class="result-block warning-block">
          <h3>Warnings</h3>
          <ul class="detail-list">
            ${rec.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      ${rec.doradoCommand ? `
        <div class="result-block">
          <h3>Dorado basecalling command</h3>
          <div class="command-card">
            <div class="command-head">
              <strong>Basecall with Dorado</strong>
              <button type="button" class="ghost-button copy-button" data-copy="${escapeHtml(rec.doradoCommand)}">Copy</button>
            </div>
            <pre><code>${escapeHtml(rec.doradoCommand)}</code></pre>
          </div>
        </div>
      ` : ''}

      ${rec.nextflowCommand ? `
        <div class="result-block">
          <h3>Nextflow pipeline command</h3>
          <div class="command-card">
            <div class="command-head">
              <strong>Run with Nextflow</strong>
              <button type="button" class="ghost-button copy-button" data-copy="${escapeHtml(rec.nextflowCommand)}">Copy</button>
            </div>
            <pre><code>${escapeHtml(rec.nextflowCommand)}</code></pre>
          </div>
        </div>
      ` : ''}

      ${rec.alternative ? `
        <div class="result-block alt-block">
          <h3>Alternative option</h3>
          <p><strong>${escapeHtml(rec.alternative.kitInfo?.label || rec.alternative.kit)}</strong></p>
          ${rec.alternative.gain ? `<p class="result-text"><strong>Gain:</strong> ${escapeHtml(rec.alternative.gain)}</p>` : ''}
          ${rec.alternative.tradeoff ? `<p class="result-text"><strong>Trade-off:</strong> ${escapeHtml(rec.alternative.tradeoff)}</p>` : ''}
        </div>
      ` : ''}

      ${rec.checklist ? `
        <div class="result-block">
          <h3>Wet-lab checklist</h3>
          <ol class="step-list">
            ${rec.checklist.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
          </ol>
        </div>
      ` : ''}

      ${rec.protocolUrls.length > 0 ? `
        <div class="result-block">
          <h3>Protocol links</h3>
          <ul class="link-list">
            ${rec.protocolUrls.map(p => `
              <li><a href="${escapeHtml(p.url)}" target="_blank" rel="noreferrer">${escapeHtml(p.label)}</a></li>
            `).join('')}
          </ul>
        </div>
      ` : ''}
    </section>
  `;
}

// ── Live recommendation card (slot-based updates) ───────────

function confidenceLabel(level) {
  if (level === 'high') return 'High confidence';
  if (level === 'medium') return 'Moderate — refine with constraints';
  return 'Needs more info';
}

function updateSlot(el, text) {
  const newText = text || '—';
  if (el.textContent !== newText) {
    el.classList.add('rec-slot-updating');
    el.textContent = newText;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => el.classList.remove('rec-slot-updating'));
    });
  }
}

function updateRecommendationCard() {
  const rec = computeLiveRecommendation(answers, datasets);
  lastRecommendation = rec;

  // Confidence badge
  recConfidence.dataset.level = rec.confidence;
  recConfidence.querySelector('.confidence-label').textContent = confidenceLabel(rec.confidence);

  // Slots
  updateSlot(recWorkflow, rec.workflow);
  updateSlot(recKit, rec.kitInfo?.label || (rec.kit ? rec.kit : null));
  recKitMeta.textContent = rec.kitInfo?.sku || '';
  updateSlot(recBasecalling, rec.basecallingInfo?.label || (rec.basecalling ? rec.basecalling : null));
  recBasecallingMeta.textContent = rec.basecallingInfo?.description || '';
  updateSlot(recPipeline, rec.pipelineInfo?.label || (rec.pipeline ? rec.pipeline : null));
  recPipelineMeta.textContent = rec.pipelineInfo?.description || '';

  // Rationale list
  if (rec.rationale.length > 0) {
    recRationale.innerHTML = rec.rationale.map(r => `<li>${escapeHtml(r)}</li>`).join('');
  } else {
    recRationale.innerHTML = '<li class="muted">Answer more questions to see rationale</li>';
  }

  // Warnings
  if (rec.warnings.length > 0) {
    recWarnings.hidden = false;
    recWarnings.innerHTML = `
      <p class="rec-slot-label">Warnings</p>
      ${rec.warnings.map(w => `<p class="warning-inline">${escapeHtml(w)}</p>`).join('')}
    `;
  } else {
    recWarnings.hidden = true;
    recWarnings.innerHTML = '';
  }

  // Update rationale pane
  updateRationalePane(rec);
}

// ── Rationale pane ──────────────────────────────────────────

function updateRationalePane(rec) {
  const hasContent = rec.kit || rec.pipeline;
  rationalePlaceholder.hidden = hasContent;

  // Alternative
  if (rec.alternative) {
    rationaleAlt.hidden = false;
    const alt = rec.alternative;
    rationaleAltContent.innerHTML = `
      <div class="alt-card">
        <p class="alt-name">${escapeHtml(alt.kitInfo?.label || alt.kit)}</p>
        ${alt.gain ? `<p class="alt-detail"><strong>Gain:</strong> ${escapeHtml(alt.gain)}</p>` : ''}
        ${alt.tradeoff ? `<p class="alt-detail"><strong>Trade-off:</strong> ${escapeHtml(alt.tradeoff)}</p>` : ''}
      </div>
    `;
  } else {
    rationaleAlt.hidden = true;
  }

  // Commands
  if (rec.doradoCommand || rec.nextflowCommand) {
    rationaleCommands.hidden = false;
    rationaleCommandsContent.innerHTML = `
      ${rec.doradoCommand ? `
        <div class="command-mini">
          <p class="command-mini-label">Dorado</p>
          <pre><code>${escapeHtml(rec.doradoCommand)}</code></pre>
          <button type="button" class="copy-button ghost-button" data-copy="${escapeHtml(rec.doradoCommand)}">Copy</button>
        </div>
      ` : ''}
      ${rec.nextflowCommand ? `
        <div class="command-mini">
          <p class="command-mini-label">Nextflow</p>
          <pre><code>${escapeHtml(rec.nextflowCommand)}</code></pre>
          <button type="button" class="copy-button ghost-button" data-copy="${escapeHtml(rec.nextflowCommand)}">Copy</button>
        </div>
      ` : ''}
    `;
  } else {
    rationaleCommands.hidden = true;
  }

  // Checklist
  if (rec.checklist) {
    rationaleChecklist.hidden = false;
    rationaleChecklistContent.innerHTML = rec.checklist.map(
      item => `<li>${escapeHtml(item)}</li>`
    ).join('');
  } else {
    rationaleChecklist.hidden = true;
  }

  // Protocol links
  if (rec.protocolUrls.length > 0) {
    rationaleProtocols.hidden = false;
    rationaleProtocolsContent.innerHTML = rec.protocolUrls.map(
      p => `<li><a href="${escapeHtml(p.url)}" target="_blank" rel="noreferrer">${escapeHtml(p.label)}</a></li>`
    ).join('');
  } else {
    rationaleProtocols.hidden = true;
  }

  // Attach copy buttons in rationale pane
  attachCopyButtons();
}

// ── Event wiring ────────────────────────────────────────────

function attachCopyButtons() {
  document.querySelectorAll('.copy-button[data-copy]').forEach(btn => {
    btn.onclick = () => {
      navigator.clipboard.writeText(btn.dataset.copy).then(() => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = orig; }, 1500);
      });
    };
  });
}

function attachQuestionListeners() {
  pageRoot.querySelectorAll("[data-question-id]").forEach((input) => {
    input.addEventListener("change", (event) => {
      const field = event.target.dataset.field;
      const isMulti = event.target.dataset.multi === "true";

      if (isMulti) {
        // Multi-select: toggle value in array
        const current = answers[field] || [];
        const val = event.target.value;
        if (event.target.checked) {
          answers[field] = [...current, val];
        } else {
          answers[field] = current.filter(v => v !== val);
        }
      } else {
        answers[field] = event.target.value;
      }

      // Normalize when upstream changes
      answers = normalizeAnswers(answers, field, datasets.questionSpec);

      render();
    });
  });
}

// ── Navigation ──────────────────────────────────────────────

function currentPageId() {
  const pages = getPageSequence();
  const requested = location.hash.replace(/^#/, "") || pages[0];
  if (!pages.includes(requested)) {
    return firstIncompletePage(answers, datasets.questionSpec);
  }
  if (!canReachPage(requested, answers, datasets.questionSpec)) {
    return firstIncompletePage(answers, datasets.questionSpec);
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

function updateControls(pageId) {
  const prev = previousPageId(pageId);
  const next = nextPageId(pageId, answers, datasets.questionSpec);

  backButton.hidden = !prev;
  backButton.disabled = !prev;
  backButton.onclick = () => { if (prev) navigateTo(prev); };

  if (pageId === "results") {
    nextButton.hidden = true;
    return;
  }

  nextButton.hidden = false;
  nextButton.textContent = pageId === "constraints" ? "Show recommendation" : "Continue";
  nextButton.disabled = !next || !isPageComplete(pageId, answers, datasets.questionSpec);
  nextButton.onclick = () => { if (next) navigateTo(next); };
}

// ── Main render ─────────────────────────────────────────────

function render() {
  if (!datasets) return;

  const pageId = syncHash();
  renderProgress(pageId);
  updateRecommendationCard();
  renderPage(pageId);
  updateControls(pageId);
}

function renderFatal(error) {
  const message = error instanceof Error ? error.message : String(error);
  pageRoot.innerHTML = `
    <section class="wizard-page">
      <div class="page-header">
        <p class="page-kicker">Error</p>
        <h2>Advisor unavailable</h2>
        <p>Failed to load: ${escapeHtml(message)}</p>
      </div>
    </section>
  `;
  backButton.hidden = true;
  nextButton.hidden = true;
}

// ── Init ────────────────────────────────────────────────────

window.addEventListener("hashchange", () => {
  if (datasets) render();
});

resetButton.addEventListener("click", () => {
  answers = {};
  navigateTo("molecule");
});

Promise.all([
  fetchJson("data/questions_v2.json"),
  fetchJson("data/recommendation_rules.json"),
  fetchJson("data/route_mapping.json"),
  fetchJson("data/pipelines.json"),
  fetchJson("data/playbooks.json"),
  fetchJson("data/examples.json"),
  fetchJson("data/expert_rules.json"),
  fetchJson("data/nanopore_profiles.json"),
  fetchJson("data/external_workflows.json"),
  fetchJson("data/matrix_profiles.json")
])
  .then(([questionSpec, recommendationRules, routeMapping, pipelines, playbooks, examples, expertRules, nanoporeProfiles, externalWorkflows, matrixProfiles]) => {
    datasets = {
      questionSpec,
      recommendationRules,
      routeMapping,
      pipelines,
      playbooks,
      examples,
      expertRules,
      nanoporeProfiles,
      externalWorkflows,
      matrixProfiles
    };
    render();
  })
  .catch(renderFatal);
