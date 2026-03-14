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

const ONT_LIBRARY_REFERENCE = {
  rbk114_24: {
    title: "Rapid Barcoding Kit 24 V14",
    description: "Oxford Nanopore positions SQK-RBK114.24 as a rapid, PCR-free, transposase-based workflow for multiplexing up to 24 genomic DNA samples.",
    url: "https://store.nanoporetech.com/rapid-barcoding-sequencing-kit-24-v14.html",
    urlLabel: "Official kit page"
  },
  nbd114_24: {
    title: "Native Barcoding Kit 24 V14",
    description: "Oxford Nanopore positions SQK-NBD114.24 as a PCR-free ligation workflow that preserves full fragment length and aligns with Q20+ chemistry.",
    url: "https://store.nanoporetech.com/native-barcoding-kit-24-v14.html",
    urlLabel: "Official kit page"
  },
  direct_rna002: {
    title: "Direct RNA002 legacy chemistry",
    description: "RNA002 is an older native-RNA branch. Current Dorado model guidance treats RNA002 as a legacy condition, so chemistry-specific legacy handling may still matter.",
    url: "https://nanoporetech.com/document/direct-rna-sequencing-sqk-rna002",
    urlLabel: "Legacy protocol"
  },
  direct_rna004: {
    title: "Direct RNA Sequencing Kit (SQK-RNA004)",
    description: "Oxford Nanopore positions SQK-RNA004 for sequencing native RNA directly, without cDNA conversion or PCR, to reduce reverse-transcription and amplification bias.",
    url: "https://store.nanoporetech.com/us/direct-rna-sequencing-kit-004.html",
    urlLabel: "Official kit page"
  },
  cdna_rbk: {
    title: "PCR-cDNA Sequencing V14 - Barcoding",
    description: "This branch is distinct from native direct RNA. The official ONT protocol uses reverse transcription, cDNA amplification, and barcode primers before loading.",
    url: "https://nanoporetech.com/document/pcr-cdna-sequencing-v14-barcoding-sqk-pcb114-24",
    urlLabel: "Official protocol"
  }
};

const DORADO_REFERENCE = {
  raw_signal_not_basecalled: {
    title: "Dorado simplex basecalling",
    description: "If you are entering from POD5 or FAST5, use Dorado's simplex basecalling documentation to select the latest compatible model for your chemistry and pore type.",
    url: "https://software-docs.nanoporetech.com/dorado/latest/basecaller/simplex/",
    urlLabel: "Simplex basecalling docs"
  },
  prefer_fast: {
    title: "Dorado FAST",
    description: "FAST is the quickest Dorado tier and the least computationally expensive, but it is also the least accurate of the standard simplex options.",
    url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
    urlLabel: "Model selection guide"
  },
  prefer_hac: {
    title: "Dorado HAC",
    description: "Oxford Nanopore recommends HAC for most users because it provides the best balance between basecalling accuracy and computational cost.",
    url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
    urlLabel: "Model selection guide"
  },
  prefer_sup: {
    title: "Dorado SUP",
    description: "SUP is the most accurate standard simplex tier, with the highest computational cost. It is often a sensible choice when assembly quality or difficult calls are the priority.",
    url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
    urlLabel: "Model selection guide"
  }
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

function allQuestions() {
  return questionSpec.stages.flatMap((stage) => stage.questions);
}

function questionById(questionId) {
  return allQuestions().find((question) => question.id === questionId);
}

function questionByField(field) {
  return allQuestions().find((question) => question.field === field);
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
      const question = questionByField(field);
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

function labelForValue(question, value) {
  if (!question) {
    return value;
  }
  return optionFor(question, value)?.label || value;
}

function formatFieldValues(field, values) {
  const question = questionByField(field);
  return values.map((value) => labelForValue(question, value)).join(", ");
}

function buildCompatibilityNotes(pipeline, exactMatch, track) {
  const notes = [];

  if (!exactMatch) {
    notes.push({
      title: "No exact current pipeline",
      text: "The current collection does not contain a workflow that exactly matches all Stage 1 answers. This recommendation is the nearest documented starting point in the existing repository."
    });
  }

  const inputQuestion = questionById("input_format");
  const inputValue = answers.input_format;
  if (inputValue && !isNeutral(inputQuestion, inputValue) && !matchesFieldValue(pipeline, "input_formats", inputValue)) {
    notes.push({
      title: "Input-format adaptation required",
      text: `Your current input format is ${labelForValue(inputQuestion, inputValue)}. The documented workflow is written primarily for ${formatFieldValues("input_formats", pipeline.input_formats)}. Some adaptation may be required before you can run it exactly as published.`
    });
  }

  const libraryQuestion = questionById("library_mode");
  const libraryValue = answers.library_mode;
  if (libraryValue && !isNeutral(libraryQuestion, libraryValue) && pipeline.library_modes.length > 0 && !matchesFieldValue(pipeline, "library_modes", libraryValue)) {
    notes.push({
      title: "Library-mode mismatch",
      text: `You selected ${labelForValue(libraryQuestion, libraryValue)}, but this workflow is documented mainly for ${formatFieldValues("library_modes", pipeline.library_modes)}. Treat the recommendation as a starting point rather than an exact protocol match.`
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
      text: `This recommendation assumes a raw-data entry point that is compatible with ${formatFieldValues("input_formats", pipeline.input_formats)}. Use the documented basecalling branch before downstream preprocessing.`
    });
  } else if (answers.basecalling_state === "prefer_fast") {
    notes.push({
      title: "FAST tier selected",
      text: "FAST is appropriate when turnaround time or available compute matters most, but it is the lowest-accuracy standard Dorado tier. Treat it as a speed-first choice."
    });
  } else if (answers.basecalling_state === "prefer_sup") {
    notes.push({
      title: "SUP tier selected",
      text: "SUP can be a sensible accuracy-first choice for harder datasets or assembly-sensitive work, but it has the highest compute cost among the standard simplex tiers."
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

function buildOntNotes() {
  const notes = [];

  const libraryReference = ONT_LIBRARY_REFERENCE[answers.library_mode];
  if (libraryReference) {
    notes.push(libraryReference);
  }

  const basecallingReference = DORADO_REFERENCE[answers.basecalling_state];
  if (basecallingReference) {
    notes.push(basecallingReference);
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

function renderOntReferenceCard() {
  const notes = buildOntNotes();
  if (notes.length === 0) {
    return "";
  }

  return `
    <div class="sub-card">
      <p class="section-label">Oxford Nanopore Reference</p>
      <div class="ont-list">
        ${notes
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
        ${renderOntReferenceCard()}
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
