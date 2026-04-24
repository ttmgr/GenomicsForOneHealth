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
const skipToResultsButton = document.getElementById("skip-to-results-button");
const resetButton = document.getElementById("reset-button");

// Mobile rec bar
const mobileRecBar = document.getElementById("mobile-rec-bar");
const mobileRecValue = document.getElementById("mobile-rec-value");
const mobileRecConfidence = document.getElementById("mobile-rec-confidence");
const mobileRecExpand = document.getElementById("mobile-rec-expand");

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
const rationaleCompare = document.getElementById("rationale-compare");
const rationaleCompareContent = document.getElementById("rationale-compare-content");
const rationaleAlt = document.getElementById("rationale-alternative");
const rationaleAltContent = document.getElementById("rationale-alt-content");
const rationaleCommands = document.getElementById("rationale-commands");
const rationaleCommandsContent = document.getElementById("rationale-commands-content");
const rationaleChecklist = document.getElementById("rationale-checklist");
const rationaleChecklistContent = document.getElementById("rationale-checklist-content");
const rationaleProtocols = document.getElementById("rationale-protocols");
const rationaleProtocolsContent = document.getElementById("rationale-protocols-content");
const rationalePlaceholder = document.getElementById("rationale-placeholder");

// Confidence popover (shared by all confidence chips)
const confidencePopover = document.getElementById("confidence-popover");
const confidencePopoverClose = document.getElementById("confidence-popover-close");
const recLive = document.getElementById("rec-live");
let confidenceChipTrigger = null;
let lastAnnouncedKit = null;

// ── State ───────────────────────────────────────────────────

const STORAGE_KEY = 'advisor.answers.v1';

let datasets = null;
let answers = {};
let lastRecommendation = null;
let previousConfidence = 'low';
let isTransitioning = false;
let pendingFlashField = null;

function loadAnswersFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return (parsed && typeof parsed === 'object') ? parsed : null;
  } catch {
    return null;
  }
}

function saveAnswersToStorage(state) {
  try {
    const toSave = { ...state };
    // Don't persist UI-only override across sessions
    delete toSave.__kit_override;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch {
    // localStorage may be unavailable (private mode) — silently ignore
  }
}

function clearStoredAnswers() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}

function loadAnswersFromUrl() {
  // Share-link form: #results?m=dna&s=isolate&...
  const hash = location.hash || '';
  const qIdx = hash.indexOf('?');
  if (qIdx < 0) return null;
  const query = hash.slice(qIdx + 1);
  const parsed = hashDecodeAnswers(query);
  if (!parsed || Object.keys(parsed).length === 0) return null;
  // Strip the query so navigation works on a clean #pageId
  const target = hash.slice(1, qIdx) || 'results';
  history.replaceState(null, '', `#${target}`);
  return parsed;
}

const CHECK_SVG = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3.5 8.5 6.5 11.5 12.5 5.5"/></svg>';
const ARROW_SVG = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 4 11 8 5 12"/></svg>';

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
  const resultsReady = canPreviewResults(answers);

  progressRoot.innerHTML = `
    <div class="progress-steps">
      ${pages
        .map((id, i) => {
          const page = datasets.questionSpec.pages.find(p => p.id === id);
          const isResults = id === 'results';
          const isCurrent = id === currentPageId;
          const isDone = i < currentIdx;
          const label = isResults ? 'Results' : (page?.title || id);
          const indexContent = isDone
            ? CHECK_SVG
            : (isResults ? '<span class="progress-results-icon" aria-hidden="true">✦</span>' : (i + 1));
          const connector = i < pages.length - 1
            ? `<span class="progress-connector ${isDone ? 'is-filled' : ''}"></span>`
            : '';
          // Reachability: standard pages use canReachPage; results step only enables once core answers are in
          const reachable = isResults ? resultsReady : canReachPage(id, answers, datasets.questionSpec);
          const disabled = !isCurrent && !reachable;
          return `
            <button type="button"
              class="progress-step ${isCurrent ? 'is-current' : ''} ${isDone ? 'is-complete' : ''} ${isResults ? 'is-results-step' : ''}"
              data-progress-page="${id}"
              ${disabled ? 'disabled' : ''}>
              <span class="progress-index">${indexContent}</span>
              <span class="progress-label">${escapeHtml(label)}</span>
            </button>
            ${connector}
          `;
        })
        .join('')}
    </div>
  `;

  progressRoot.querySelectorAll("[data-progress-page]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.progressPage;
      if (target === 'results') {
        if (canPreviewResults(answers)) navigateTo(target);
      } else if (canReachPage(target, answers, datasets.questionSpec)) {
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
    attachToolbarHandlers();
    attachComparisonHandlers();
    attachEditAnswersHandlers();
    attachConflictHandlers();
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

const FIELD_LABELS_UI = {
  molecule: 'Molecule',
  study_type: 'Study type',
  priority: 'Priorities',
  input_amount: 'Input amount',
  input_quality: 'Input quality',
  host_background: 'Host-DNA background',
  barcoding_needed: 'Multiplexing',
  device: 'Device',
  compute_gpu: 'Compute / GPU'
};

function findOptionLabel(field, value) {
  if (!datasets?.questionSpec) return value;
  for (const page of datasets.questionSpec.pages || []) {
    for (const q of page.questions || []) {
      if (q.field !== field) continue;
      const opt = (q.options || []).find(o => o.value === value);
      if (opt) return opt.label;
    }
  }
  return value;
}

function fieldToPageId(field) {
  if (['molecule', 'study_type', 'priority'].includes(field)) return field;
  return 'constraints';
}

function renderResultsToolbar(rec) {
  return `
    <div class="results-toolbar" role="toolbar" aria-label="Recommendation actions">
      <button type="button" class="ghost-button results-toolbar-btn" data-toolbar="edit">
        <span aria-hidden="true">←</span> Edit answers
      </button>
      <button type="button" class="ghost-button results-toolbar-btn" data-toolbar="print">
        Print report
      </button>
      <button type="button" class="ghost-button results-toolbar-btn" data-toolbar="share">
        Copy share link
      </button>
      ${rec.doradoCommandSpec || rec.nextflowCommandSpec ? `
        <button type="button" class="ghost-button results-toolbar-btn" data-toolbar="download-script">
          Download .sh
        </button>
      ` : ''}
    </div>
  `;
}

function renderResultsHero(rec) {
  const kitInfo = rec.kitInfo || {};
  const bcInfo = rec.basecallingInfo || {};
  return `
    <div class="results-hero">
      <p class="results-hero-kicker">Your recommendation</p>
      <h3>${escapeHtml(rec.workflow || 'Sequencing workflow')}</h3>
      <div class="results-hero-meta">
        <button type="button"
          class="confidence-badge confidence-chip is-on-hero"
          data-level="${rec.confidence}"
          aria-haspopup="dialog"
          aria-expanded="false"
          aria-controls="confidence-popover">
          <span class="confidence-dot"></span>
          <span class="confidence-label">${confidenceLabel(rec.confidence)}</span>
          <span class="confidence-info-icon" aria-hidden="true">i</span>
        </button>
        <span>${escapeHtml(kitInfo.label || rec.kit)}</span>
        <span>${escapeHtml(bcInfo.label || rec.basecalling)}</span>
      </div>
    </div>
  `;
}

function renderPrimaryTriptych(rec) {
  const kitInfo = rec.kitInfo || {};
  const bcInfo = rec.basecallingInfo || {};
  const plInfo = rec.pipelineInfo || {};
  return `
    <div class="result-cards">
      <div class="result-rec-card has-recommended-ribbon">
        <span class="recommended-ribbon">Recommended</span>
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
  `;
}

function renderComparisonTable(rec, opts = {}) {
  const compact = !!opts.compact;
  const candidates = rec.topCandidates?.kits || [];
  if (candidates.length < 2) return '';

  const rows = [
    {
      label: 'Kit',
      cell: c => `<strong>${escapeHtml(c.info?.label || c.id)}</strong>${c.info?.sku ? `<br><span class="compare-sku">${escapeHtml(c.info.sku)}</span>` : ''}`
    },
    { label: 'Prep time', cell: c => escapeHtml(c.info?.prep_time || '—') },
    { label: 'Input range', cell: c => escapeHtml(c.info?.input_range || '—') },
    { label: 'Multiplexing', cell: c => escapeHtml(c.info?.multiplexing || '—') },
    { label: 'PCR-free', cell: c => c.info?.pcr_free ? '<span class="compare-yes">✓</span>' : '<span class="compare-no">–</span>' },
    {
      label: 'Why it fits',
      cell: c => c.rationale?.length ? escapeHtml(c.rationale[0]) : '<span class="muted">—</span>'
    },
    {
      label: 'Trade-off',
      cell: c => c.tradeoff ? escapeHtml(c.tradeoff) : '<span class="muted">—</span>',
      hideOnFirst: true
    },
    {
      label: 'Score gap',
      cell: c => c.lostBy > 0
        ? `<span class="compare-lost-chip">−${c.lostBy} pts</span>`
        : `<span class="compare-won-chip">leader</span>`
    }
  ];

  const cols = candidates.map((c, idx) => `
    <div class="compare-col ${idx === 0 ? 'compare-col--winner' : ''}" role="columnheader">
      <p class="compare-col-rank">${idx === 0 ? 'Top pick' : `Option ${idx + 1}`}</p>
      <p class="compare-col-name">${escapeHtml(c.info?.label || c.id)}</p>
      ${idx > 0 ? `<button type="button" class="compare-swap-btn" data-swap-kit="${escapeHtml(c.id)}">Swap to this</button>` : ''}
    </div>
  `).join('');

  const body = rows.map(row => `
    <div class="compare-row" role="row">
      <div class="compare-cell compare-cell--label" role="rowheader">${row.label}</div>
      ${candidates.map((c, idx) => `
        <div class="compare-cell ${idx === 0 ? 'compare-cell--winner' : ''}" role="cell">
          ${row.hideOnFirst && idx === 0 ? '<span class="muted">—</span>' : row.cell(c)}
        </div>
      `).join('')}
    </div>
  `).join('');

  return `
    <div class="compare-table ${compact ? 'compare-table--compact' : ''}" role="table" aria-label="Top kit candidates">
      <div class="compare-row compare-row--header" role="row">
        <div class="compare-cell compare-cell--label" role="columnheader"></div>
        ${cols}
      </div>
      ${body}
    </div>
  `;
}

function renderWhyThisWins(rec) {
  if (!rec.rationale || rec.rationale.length === 0) return '';
  const lead = rec.rationale[0];
  const rest = rec.rationale.slice(1);
  return `
    <div class="result-block">
      <h3>Why this is the best fit</h3>
      <p class="why-lead">${escapeHtml(lead)}</p>
      ${rest.length ? `
        <ul class="detail-list">
          ${rest.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
        </ul>
      ` : ''}
    </div>
  `;
}

function renderAnnotatedCommand(spec, opts = {}) {
  if (!spec) return '';
  const { language, fullCommand, placeholders = [] } = spec;
  const label = opts.label || 'Command';

  // Wrap each placeholder occurrence with a span for tooltips.
  let rendered = escapeHtml(fullCommand);
  for (const ph of placeholders) {
    const escapedToken = escapeHtml(ph.token);
    rendered = rendered.split(escapedToken).join(
      `<span class="command-placeholder" data-tooltip="${escapeHtml(ph.annotation)}">${escapedToken}</span>`
    );
  }

  return `
    <div class="command-card">
      <div class="command-head">
        <div class="command-head-left">
          <span class="command-lang-chip">${escapeHtml(language)}</span>
          <strong>${escapeHtml(label)}</strong>
        </div>
        <div class="command-actions">
          <button type="button" class="ghost-button copy-button" data-copy="${escapeHtml(fullCommand)}">Copy</button>
        </div>
      </div>
      <pre><code>${rendered}</code></pre>
      ${placeholders.length ? `
        <ul class="command-annotations">
          ${placeholders.map(p => `
            <li><code>${escapeHtml(p.token)}</code> — ${escapeHtml(p.annotation)}</li>
          `).join('')}
        </ul>
      ` : ''}
    </div>
  `;
}

function renderCommandsSection(rec) {
  const blocks = [];
  if (rec.nextflowCommandSpec) {
    blocks.push(`
      <div class="result-block">
        <h3>Run the analysis pipeline</h3>
        ${renderAnnotatedCommand(rec.nextflowCommandSpec, { label: 'Nextflow' })}
      </div>
    `);
  }
  if (rec.doradoCommandSpec) {
    blocks.push(`
      <div class="result-block">
        <h3>Also needed: basecall the raw signal</h3>
        ${renderAnnotatedCommand(rec.doradoCommandSpec, { label: 'Dorado' })}
      </div>
    `);
  }
  return blocks.join('');
}

function renderWarningsSection(rec) {
  if (!rec.warnings || rec.warnings.length === 0) return '';
  return `
    <div class="result-block warning-block">
      <h3>Warnings</h3>
      <ul class="detail-list">
        ${rec.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
      </ul>
    </div>
  `;
}

function renderChecklistSection(rec) {
  if (!rec.checklist) return '';
  return `
    <div class="result-block">
      <h3>Wet-lab checklist</h3>
      <ol class="step-list">
        ${rec.checklist.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
      </ol>
    </div>
  `;
}

function renderProtocolsSection(rec) {
  if (!rec.protocolUrls || rec.protocolUrls.length === 0) return '';
  return `
    <div class="result-block">
      <h3>Protocol links</h3>
      <ul class="link-list">
        ${rec.protocolUrls.map(p => `
          <li><a href="${escapeHtml(p.url)}" target="_blank" rel="noreferrer">${escapeHtml(p.label)}</a></li>
        `).join('')}
      </ul>
    </div>
  `;
}

function renderEditAnswersDrawer(answers) {
  const rows = Object.entries(answers || {})
    .filter(([key, val]) => !key.startsWith('__') && val !== undefined && val !== null && (!Array.isArray(val) || val.length > 0))
    .map(([key, val]) => {
      const valueStr = Array.isArray(val)
        ? val.map(v => findOptionLabel(key, v)).join(', ')
        : findOptionLabel(key, val);
      return `
        <li class="edit-row">
          <span class="edit-row-field">${escapeHtml(FIELD_LABELS_UI[key] || key)}</span>
          <span class="edit-row-value">${escapeHtml(valueStr)}</span>
          <button type="button" class="ghost-button edit-row-btn" data-edit-field="${escapeHtml(key)}">Change</button>
        </li>
      `;
    });

  if (rows.length === 0) return '';

  return `
    <details class="edit-answers-drawer">
      <summary>Edit your answers</summary>
      <ul class="edit-answers-list">${rows.join('')}</ul>
    </details>
  `;
}

function renderConflictCard(rec) {
  const conflict = rec.conflict;
  if (!conflict?.hasNoMatch) return '';
  return `
    <div class="results-conflict" role="alert">
      <p class="panel-kicker">No match</p>
      <h3>No kit matches all your constraints</h3>
      <p>${escapeHtml(conflict.message)}</p>
      <div class="results-conflict-actions">
        ${conflict.culpritPageId ? `
          <button type="button" class="primary-button" data-conflict-revisit="${escapeHtml(conflict.culpritPageId)}" data-conflict-field="${escapeHtml(conflict.culprit || '')}">
            Revisit ${escapeHtml(FIELD_LABELS_UI[conflict.culprit] || conflict.culprit || 'answers')}
          </button>
        ` : ''}
        <button type="button" class="ghost-button" id="relax-constraints">Relax constraints</button>
      </div>
    </div>
  `;
}

function printHeader(rec) {
  const date = new Date().toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  return `
    <div class="print-header" aria-hidden="true">
      Pipeline Advisor — ${escapeHtml(rec.workflow || 'Sequencing workflow')} — Generated ${escapeHtml(date)}
    </div>
  `;
}

function renderResultsPage() {
  const rec = lastRecommendation;
  if (!rec || !rec.kit) {
    if (rec?.conflict?.hasNoMatch) {
      return `
        <section class="wizard-page results-page">
          <div class="page-header">
            <h2>Your recommendation</h2>
          </div>
          ${renderResultsToolbar(rec)}
          ${renderConflictCard(rec)}
          ${renderComparisonTable(rec)}
          ${renderEditAnswersDrawer(answers)}
        </section>
      `;
    }
    return `
      <section class="wizard-page">
        <div class="page-header">
          <h2>Your recommendation</h2>
          <p class="muted">Answer more questions to generate a recommendation.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="wizard-page results-page">
      ${printHeader(rec)}
      <div class="page-header">
        <div class="page-header-top">
          <p class="page-kicker">Your recommendation</p>
        </div>
        <h2>${escapeHtml(rec.workflow || 'Sequencing workflow')}</h2>
      </div>
      ${renderResultsToolbar(rec)}
      ${renderResultsHero(rec)}
      ${renderPrimaryTriptych(rec)}
      ${renderComparisonTable(rec)}
      ${renderWhyThisWins(rec)}
      ${renderWarningsSection(rec)}
      ${renderCommandsSection(rec)}
      ${renderChecklistSection(rec)}
      ${renderProtocolsSection(rec)}
      ${renderEditAnswersDrawer(answers)}
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
  const isEmpty = !text;
  const newText = text || '';
  if (el.textContent !== newText || el.classList.contains('is-empty') !== isEmpty) {
    el.classList.toggle('is-empty', isEmpty);
    if (isEmpty) {
      el.textContent = '';
    } else {
      el.classList.add('rec-slot-updating');
      el.textContent = newText;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => el.classList.remove('rec-slot-updating'));
      });
    }
  }
}

function updateRecommendationCard() {
  const rec = computeLiveRecommendation(answers, datasets);
  lastRecommendation = rec;

  // Confidence badge with pulse on change
  if (rec.confidence !== previousConfidence) {
    recConfidence.classList.add('is-changing');
    mobileRecConfidence.classList.add('is-changing');
    setTimeout(() => {
      recConfidence.classList.remove('is-changing');
      mobileRecConfidence.classList.remove('is-changing');
    }, 400);
    previousConfidence = rec.confidence;
  }
  recConfidence.dataset.level = rec.confidence;
  recConfidence.querySelector('.confidence-label').textContent = confidenceLabel(rec.confidence);

  // Live confidence popover content (only matters when popover is currently open)
  updateConfidencePopover(rec.confidence, rec.confidenceSignals);

  // Announce kit change to screen readers
  const currentKit = rec.kitInfo?.label || rec.kit;
  if (currentKit && currentKit !== lastAnnouncedKit && recLive) {
    recLive.textContent = `Recommendation updated to ${currentKit}`;
    lastAnnouncedKit = currentKit;
  }

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

  // Warnings (and conflict surfaced inline when no kit qualifies)
  const conflict = rec.conflict;
  if (conflict?.hasNoMatch) {
    recWarnings.hidden = false;
    recWarnings.innerHTML = `
      <p class="rec-slot-label rec-slot-conflict-label">No match yet</p>
      <p class="rec-slot-conflict">${escapeHtml(conflict.message)}</p>
    `;
    recCard.classList.add('rec-card--conflict');
  } else if (rec.warnings.length > 0) {
    recCard.classList.remove('rec-card--conflict');
    recWarnings.hidden = false;
    recWarnings.innerHTML = `
      <p class="rec-slot-label">Warnings</p>
      ${rec.warnings.map(w => `<p class="warning-inline">${escapeHtml(w)}</p>`).join('')}
    `;
  } else {
    recCard.classList.remove('rec-card--conflict');
    recWarnings.hidden = true;
    recWarnings.innerHTML = '';
  }

  // Update rationale pane
  updateRationalePane(rec);

  // Update mobile sticky bar
  updateMobileRecBar(rec);
}

// ── Rationale pane ──────────────────────────────────────────

function updateRationalePane(rec) {
  const hasContent = rec.kit || rec.pipeline;
  rationalePlaceholder.hidden = hasContent;

  // Compare table (visible once we have at least 2 candidates)
  if (rationaleCompare && rec.topCandidates?.kits?.length >= 2) {
    rationaleCompare.hidden = false;
    rationaleCompareContent.innerHTML = renderComparisonTable(rec, { compact: true });
    rationaleCompareContent.querySelectorAll('[data-swap-kit]').forEach(btn => {
      btn.onclick = () => {
        answers.__kit_override = btn.dataset.swapKit;
        render();
      };
    });
  } else if (rationaleCompare) {
    rationaleCompare.hidden = true;
    rationaleCompareContent.innerHTML = '';
  }

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
        const orig = btn.innerHTML;
        btn.innerHTML = `<span class="copy-check">${CHECK_SVG}</span> Copied`;
        btn.classList.add('is-copied');
        setTimeout(() => {
          btn.innerHTML = orig;
          btn.classList.remove('is-copied');
        }, 1500);
      });
    };
  });
}

function flashCopyFeedback(btn, label = 'Copied') {
  const orig = btn.innerHTML;
  btn.innerHTML = `<span class="copy-check">${CHECK_SVG}</span> ${escapeHtml(label)}`;
  btn.classList.add('is-copied');
  setTimeout(() => {
    btn.innerHTML = orig;
    btn.classList.remove('is-copied');
  }, 1800);
}

function buildShareUrl() {
  const url = new URL(location.href);
  // Strip any existing query to avoid duplication on repeated copies.
  const base = url.origin + url.pathname;
  const encoded = hashEncodeAnswers(answers);
  url.href = base + '#results' + (encoded ? '?' + encoded : '');
  return url.toString();
}

function downloadShellScript(rec) {
  const lines = ['#!/usr/bin/env bash', 'set -euo pipefail', ''];
  if (rec.doradoCommand) {
    lines.push('# Basecall raw signal with Dorado');
    lines.push(rec.doradoCommand);
    lines.push('');
  }
  if (rec.nextflowCommand) {
    lines.push('# Run analysis pipeline with Nextflow');
    lines.push(rec.nextflowCommand);
    lines.push('');
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/x-shellscript' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pipeline-advisor-${(rec.kit || 'recipe').replace(/[^a-z0-9_-]/gi, '_')}.sh`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function attachToolbarHandlers() {
  document.querySelectorAll('[data-toolbar]').forEach(btn => {
    btn.onclick = () => {
      const action = btn.dataset.toolbar;
      const rec = lastRecommendation;
      if (action === 'print') {
        window.print();
      } else if (action === 'share') {
        navigator.clipboard.writeText(buildShareUrl()).then(() => flashCopyFeedback(btn, 'Link copied'));
      } else if (action === 'download-script' && rec) {
        downloadShellScript(rec);
      } else if (action === 'edit') {
        const drawer = document.querySelector('.edit-answers-drawer');
        if (drawer) {
          drawer.open = true;
          drawer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          navigateTo(firstIncompletePage(answers, datasets.questionSpec));
        }
      }
    };
  });
}

function attachComparisonHandlers() {
  document.querySelectorAll('[data-swap-kit]').forEach(btn => {
    btn.onclick = () => {
      answers.__kit_override = btn.dataset.swapKit;
      render();
    };
  });
}

function attachEditAnswersHandlers() {
  document.querySelectorAll('[data-edit-field]').forEach(btn => {
    btn.onclick = () => {
      const field = btn.dataset.editField;
      navigateTo(fieldToPageId(field));
    };
  });
}

function attachConflictHandlers() {
  document.querySelectorAll('[data-conflict-revisit]').forEach(btn => {
    btn.onclick = () => {
      const pageId = btn.dataset.conflictRevisit;
      const field = btn.dataset.conflictField;
      if (field) pendingFlashField = field;
      navigateTo(pageId);
    };
  });
  const relax = document.getElementById('relax-constraints');
  if (relax) {
    relax.onclick = () => {
      const constraintFields = ['input_amount', 'input_quality', 'host_background', 'barcoding_needed', 'device', 'compute_gpu'];
      for (const f of constraintFields) delete answers[f];
      delete answers.__kit_override;
      saveAnswersToStorage(answers);
      render();
    };
  }
}

function applyPendingFlash() {
  if (!pendingFlashField) return;
  const field = pendingFlashField;
  pendingFlashField = null;
  // Find the relevant inputs and flash their option-card or constraint-card parent
  const inputs = pageRoot.querySelectorAll(`[data-field="${field}"]`);
  inputs.forEach(input => {
    const card = input.closest('.option-card') || input.closest('.constraint-card');
    if (card) {
      card.classList.add('is-flash');
      setTimeout(() => card.classList.remove('is-flash'), 1700);
    }
  });
}

// ── Confidence popover ──────────────────────────────────────

function updateConfidencePopover(level, signals) {
  if (!confidencePopover) return;
  const setText = (selector, text) => {
    const el = confidencePopover.querySelector(selector);
    if (el) el.textContent = text;
  };
  setText('[data-popover-level]', level);
  if (signals) {
    setText('[data-popover-core]', `${signals.coreFieldsAnswered} of ${signals.coreFieldsTotal}`);
    setText('[data-popover-gap]', signals.coreFieldsAnswered >= signals.coreFieldsTotal
      ? `${signals.scoreGap} pts`
      : '—');
    setText('[data-popover-top]', signals.topScore > 0 ? signals.topScore : '—');
    setText('[data-popover-reason]', signals.reason || '');
  }
  confidencePopover.dataset.level = level;
}

function openConfidencePopover(triggerBtn) {
  if (!confidencePopover) return;
  confidenceChipTrigger = triggerBtn;
  confidencePopover.hidden = false;
  // Position popover beneath the trigger.
  const rect = triggerBtn.getBoundingClientRect();
  const popWidth = Math.min(320, window.innerWidth - 24);
  const left = Math.max(12, Math.min(rect.left + window.scrollX, window.innerWidth - popWidth - 12));
  confidencePopover.style.top = `${rect.bottom + window.scrollY + 8}px`;
  confidencePopover.style.left = `${left}px`;
  confidencePopover.style.width = `${popWidth}px`;
  document.querySelectorAll('.confidence-chip').forEach(b => b.setAttribute('aria-expanded', 'false'));
  triggerBtn.setAttribute('aria-expanded', 'true');
}

function closeConfidencePopover() {
  if (!confidencePopover) return;
  confidencePopover.hidden = true;
  document.querySelectorAll('.confidence-chip').forEach(b => b.setAttribute('aria-expanded', 'false'));
  if (confidenceChipTrigger) {
    confidenceChipTrigger.focus();
    confidenceChipTrigger = null;
  }
}

function attachConfidenceChipHandlers() {
  // Use event delegation so dynamically-rendered hero chip works too.
  document.addEventListener('click', (e) => {
    const chip = e.target.closest('.confidence-chip');
    if (chip) {
      e.stopPropagation();
      if (confidencePopover && !confidencePopover.hidden && confidenceChipTrigger === chip) {
        closeConfidencePopover();
      } else {
        const rec = lastRecommendation;
        updateConfidencePopover(rec?.confidence || 'low', rec?.confidenceSignals);
        openConfidencePopover(chip);
      }
      return;
    }
    if (confidencePopover && !confidencePopover.hidden && !confidencePopover.contains(e.target)) {
      closeConfidencePopover();
    }
  });
  if (confidencePopoverClose) {
    confidencePopoverClose.onclick = closeConfidencePopover;
  }
}

function updateMobileRecBar(rec) {
  const hasContent = rec.kit || rec.pipeline;
  mobileRecBar.classList.toggle('is-hidden', !hasContent);
  mobileRecValue.textContent = rec.kitInfo?.label || rec.pipelineInfo?.label || '—';
  mobileRecConfidence.dataset.level = rec.confidence;
  mobileRecConfidence.querySelector('.confidence-label').textContent =
    rec.confidence === 'high' ? 'High' : rec.confidence === 'medium' ? 'Moderate' : 'Low';
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

      // Changing any answer invalidates the user's prior swap-primary choice
      delete answers.__kit_override;

      // Normalize when upstream changes
      answers = normalizeAnswers(answers, field, datasets.questionSpec);

      saveAnswersToStorage(answers);
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
    if (skipToResultsButton) skipToResultsButton.hidden = true;
    return;
  }

  nextButton.hidden = false;
  nextButton.textContent = pageId === "constraints" ? "Show recommendation" : "Continue";
  nextButton.disabled = !next || !isPageComplete(pageId, answers, datasets.questionSpec);
  nextButton.onclick = () => { if (next) navigateTo(next); };

  // Persistent skip-to-results: visible whenever the engine has enough to score
  if (skipToResultsButton) {
    const canSkip = canPreviewResults(answers) && pageId !== "constraints";
    skipToResultsButton.hidden = !canSkip;
    skipToResultsButton.onclick = () => navigateTo("results");
  }
}

// ── Main render ─────────────────────────────────────────────

function render() {
  if (!datasets) return;

  const pageId = syncHash();
  renderProgress(pageId);
  updateRecommendationCard();
  renderPage(pageId);
  updateControls(pageId);
  applyPendingFlash();
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

attachConfidenceChipHandlers();

window.addEventListener("hashchange", () => {
  if (datasets) render();
});

resetButton.addEventListener("click", () => {
  const answeredCount = Object.keys(answers).filter(k => {
    const v = answers[k];
    return v !== undefined && v !== null && (!Array.isArray(v) || v.length > 0);
  }).length;

  if (answeredCount >= 3 && !resetButton.dataset.confirmed) {
    resetButton.classList.add('is-shaking');
    resetButton.textContent = 'Confirm reset?';
    resetButton.dataset.confirmed = 'pending';
    setTimeout(() => {
      resetButton.classList.remove('is-shaking');
    }, 400);
    setTimeout(() => {
      if (resetButton.dataset.confirmed === 'pending') {
        resetButton.textContent = 'Start over';
        delete resetButton.dataset.confirmed;
      }
    }, 3000);
    return;
  }

  delete resetButton.dataset.confirmed;
  resetButton.textContent = 'Start over';
  answers = {};
  previousConfidence = 'low';
  lastAnnouncedKit = null;
  clearStoredAnswers();
  navigateTo("molecule");
});

// Mobile expand button — scroll to recommendation pane
mobileRecExpand.addEventListener("click", () => {
  const recPane = document.getElementById("recommendation-pane");
  if (recPane) {
    // On mobile the pane is hidden, scroll to rationale instead
    const rationalePane = document.getElementById("rationale-pane");
    const target = rationalePane || recPane;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
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

    // Hydrate answers: URL share-link wins, then localStorage, then empty.
    const fromUrl = loadAnswersFromUrl();
    if (fromUrl) {
      answers = fromUrl;
      saveAnswersToStorage(answers);
    } else {
      const fromStorage = loadAnswersFromStorage();
      if (fromStorage) answers = fromStorage;
    }

    render();
  })
  .catch(renderFatal);
