/* ──────────────────────────────────────────────────────────────
   recommendation-engine.js
   Pure decision logic — no DOM access.
   Scores kits, basecalling, flowcells, and pipelines
   based on user answers and JSON rules.
   ────────────────────────────────────────────────────────────── */

// ── Condition matching ──────────────────────────────────────

/**
 * Evaluate a `when` clause against current answers.
 * Standard fields use exact-match (value in array).
 * `priority_includes` matches if ANY listed priority is in the user's multi-select.
 */
function matchesWhen(when, answers) {
  if (!when || Object.keys(when).length === 0) return true;
  for (const [field, acceptedValues] of Object.entries(when)) {
    if (field === 'priority_includes') {
      const selected = answers.priority || [];
      if (!acceptedValues.some(v => selected.includes(v))) return false;
    } else {
      const val = answers[field];
      if (val === undefined || val === null) return false;
      if (!acceptedValues.includes(val)) return false;
    }
  }
  return true;
}

// ── Scoring helpers ─────────────────────────────────────────

function collectCandidates(rules, answers, catalogKeys) {
  const scores = {};
  for (const key of catalogKeys) scores[key] = 50; // base score

  for (const rule of rules) {
    if (matchesWhen(rule.when, answers) && scores[rule.recommend] !== undefined) {
      scores[rule.recommend] += rule.score_bonus;
    }
  }
  return scores;
}

function applyConstraintModifiers(scores, modifiers, answers) {
  const applied = [];
  for (const mod of modifiers) {
    if (!matchesWhen(mod.when, answers)) continue;
    if (mod.block) {
      for (const id of mod.block) {
        if (scores[id] !== undefined) {
          scores[id] = -1;
          applied.push(mod);
        }
      }
    }
    if (mod.prefer) {
      for (const id of mod.prefer) {
        if (scores[id] !== undefined && scores[id] > 0) {
          scores[id] += 5;
          applied.push(mod);
        }
      }
    }
  }
  return applied;
}

function filterByMolecule(scores, catalog, molecule) {
  if (!molecule) return;
  for (const [id, info] of Object.entries(catalog)) {
    if (info.molecule && info.molecule !== molecule && scores[id] !== undefined) {
      scores[id] = -1;
    }
  }
}

function rankScores(scores) {
  return Object.entries(scores)
    .filter(([, s]) => s > 0)
    .sort((a, b) => b[1] - a[1]);
}

// ── Confidence ──────────────────────────────────────────────

function computeConfidence(answers, topScore, secondScore) {
  const answered = ['molecule', 'study_type', 'priority'].filter(
    f => answers[f] !== undefined && answers[f] !== null &&
         (Array.isArray(answers[f]) ? answers[f].length > 0 : true)
  ).length;

  if (answered < 1) return 'low';
  if (answered < 2) return 'low';
  if (answered < 3) return 'medium';

  const gap = (topScore || 0) - (secondScore || 0);
  if (gap >= 15) return 'high';
  return 'medium';
}

// ── Kit scoring ─────────────────────────────────────────────

function scoreKits(answers, rules) {
  const catalog = rules.kit_catalog || {};
  const kitIds = Object.keys(catalog);
  const scores = collectCandidates(rules.kit_rules || [], answers, kitIds);

  // Filter kits by molecule
  filterByMolecule(scores, catalog, answers.molecule);

  // Apply constraint modifiers
  const appliedMods = applyConstraintModifiers(scores, rules.constraint_modifiers || [], answers);

  const ranked = rankScores(scores);
  return { ranked, scores, appliedMods };
}

// ── Basecalling scoring ─────────────────────────────────────

function scoreBasecalling(answers, rules) {
  const catalog = rules.basecalling_catalog || {};
  const ids = Object.keys(catalog);
  const scores = collectCandidates(rules.basecalling_rules || [], answers, ids);

  const appliedMods = applyConstraintModifiers(scores, rules.constraint_modifiers || [], answers);

  const ranked = rankScores(scores);
  return { ranked, scores, appliedMods };
}

// ── Flowcell scoring ────────────────────────────────────────

function scoreFlowcells(answers, rules) {
  const ids = ['minion_r10_4_1', 'promethion_r10_4_1', 'rna_flow_cell'];
  const scores = collectCandidates(rules.flowcell_rules || [], answers, ids);

  // RNA flow cell only valid for direct RNA
  if (answers.molecule !== 'rna' || !answers.priority?.includes('native_modifications')) {
    scores['rna_flow_cell'] = -1;
  }

  const appliedMods = applyConstraintModifiers(scores, rules.constraint_modifiers || [], answers);

  // Apply device constraint directly
  if (answers.device === 'promethion') {
    if (scores['promethion_r10_4_1'] > 0) scores['promethion_r10_4_1'] += 30;
  } else if (answers.device === 'minion') {
    if (scores['minion_r10_4_1'] > 0) scores['minion_r10_4_1'] += 30;
  }

  const ranked = rankScores(scores);
  return { ranked, scores, appliedMods };
}

// ── Pipeline scoring ────────────────────────────────────────

function scorePipelines(answers, rules) {
  const catalog = rules.pipeline_catalog || {};
  const ids = Object.keys(catalog);
  const scores = collectCandidates(rules.pipeline_rules || [], answers, ids);

  const ranked = rankScores(scores);
  return { ranked, scores };
}

// ── Route mapping ───────────────────────────────────────────

function findRouteMapping(answers, routeMappings) {
  if (!answers.molecule || !answers.study_type) return null;
  return routeMappings.find(
    m => m.molecule === answers.molecule && m.study_type === answers.study_type
  ) || null;
}

// ── Dorado command builder ──────────────────────────────────

function buildDoradoCommand(basecallingId, rules) {
  const modelMap = rules.dorado_models || {};
  const model = modelMap[basecallingId];
  if (!model) return null;
  return `dorado basecaller ${model} /path/to/pod5/ > calls.bam`;
}

// ── Nextflow command builder ────────────────────────────────

function buildNextflowCommand(pipelineId) {
  if (!pipelineId) return null;
  return `nextflow run epi2me-labs/${pipelineId} \\
    --fastq /path/to/fastq/ \\
    --out_dir results/`;
}

// ── Main recommendation function ────────────────────────────

function computeLiveRecommendation(answers, datasets) {
  const rules = datasets.recommendationRules;
  const routeMappings = datasets.routeMapping?.mappings || [];

  const result = {
    workflow: null,
    kit: null,
    kitInfo: null,
    basecalling: null,
    basecallingInfo: null,
    flowcell: null,
    pipeline: null,
    pipelineInfo: null,
    rationale: [],
    alternative: null,
    confidence: 'low',
    doradoCommand: null,
    nextflowCommand: null,
    routeMapping: null,
    checklist: null,
    protocolUrls: [],
    warnings: [],
    appliedModifiers: []
  };

  if (!rules) return result;

  // Workflow path label
  const parts = [];
  if (answers.molecule) parts.push(answers.molecule.toUpperCase());
  if (answers.study_type) {
    const labels = {
      isolate: 'Isolate', metagenomic: 'Metagenomic',
      transcriptome: 'Transcriptome', targeted: 'Targeted / Amplicon',
      virome: 'Virome'
    };
    parts.push(labels[answers.study_type] || answers.study_type);
  }
  if (answers.priority?.length) {
    const prioLabels = {
      speed: 'Speed', accuracy: 'Accuracy',
      native_modifications: 'Native mods', yield: 'Yield',
      low_input: 'Low input', multiplexing: 'Multiplexing'
    };
    parts.push(answers.priority.map(p => prioLabels[p] || p).join(' + '));
  }
  result.workflow = parts.length ? parts.join(' → ') : null;

  // Score all categories
  const kitResult = scoreKits(answers, rules);
  const bcResult = scoreBasecalling(answers, rules);
  const fcResult = scoreFlowcells(answers, rules);
  const plResult = scorePipelines(answers, rules);

  // Best kit
  if (kitResult.ranked.length > 0) {
    const [kitId, kitScore] = kitResult.ranked[0];
    result.kit = kitId;
    result.kitInfo = rules.kit_catalog?.[kitId] || null;

    // Alternative kit
    if (kitResult.ranked.length > 1) {
      const [altId, altScore] = kitResult.ranked[1];
      const altInfo = rules.kit_catalog?.[altId];
      result.alternative = {
        kit: altId,
        kitInfo: altInfo,
        scoreDiff: kitScore - altScore,
        gain: findGainRationale(altId, rules.kit_rules, answers),
        tradeoff: findTradeoff(kitId, altId, rules.kit_catalog)
      };
    }

    // Collect kit rationale
    for (const rule of rules.kit_rules || []) {
      if (rule.recommend === kitId && matchesWhen(rule.when, answers)) {
        result.rationale.push(rule.rationale);
      }
    }
  }

  // Best basecalling
  if (bcResult.ranked.length > 0) {
    const [bcId] = bcResult.ranked[0];
    result.basecalling = bcId;
    result.basecallingInfo = rules.basecalling_catalog?.[bcId] || null;

    for (const rule of rules.basecalling_rules || []) {
      if (rule.recommend === bcId && matchesWhen(rule.when, answers)) {
        result.rationale.push(rule.rationale);
      }
    }
  }

  // Best flowcell
  if (fcResult.ranked.length > 0) {
    result.flowcell = fcResult.ranked[0][0];
  }

  // Best pipeline
  if (plResult.ranked.length > 0) {
    const [plId] = plResult.ranked[0];
    result.pipeline = plId;
    result.pipelineInfo = rules.pipeline_catalog?.[plId] || null;

    for (const rule of rules.pipeline_rules || []) {
      if (rule.recommend === plId && matchesWhen(rule.when, answers)) {
        result.rationale.push(rule.rationale);
      }
    }
  }

  // Confidence
  const kitTop = kitResult.ranked[0]?.[1] || 0;
  const kitSecond = kitResult.ranked[1]?.[1] || 0;
  result.confidence = computeConfidence(answers, kitTop, kitSecond);

  // Commands
  if (result.basecalling) {
    result.doradoCommand = buildDoradoCommand(result.basecalling, rules);
  }
  if (result.pipeline) {
    result.nextflowCommand = buildNextflowCommand(result.pipeline);
  }

  // Route mapping (bridge to legacy data)
  const mapping = findRouteMapping(answers, routeMappings);
  if (mapping) {
    result.routeMapping = mapping;
    result.protocolUrls = mapping.protocol_urls || [];
  }

  // Checklist
  if (result.kit && rules.checklists?.[result.kit]) {
    result.checklist = rules.checklists[result.kit];
  }

  // Collect warnings from applied constraint modifiers
  const allMods = [
    ...kitResult.appliedMods,
    ...bcResult.appliedMods,
    ...fcResult.appliedMods
  ];
  const seenMods = new Set();
  for (const mod of allMods) {
    if (!seenMods.has(mod.id)) {
      seenMods.add(mod.id);
      result.warnings.push(mod.rationale);
      result.appliedModifiers.push(mod);
    }
  }

  // Deduplicate rationale
  result.rationale = [...new Set(result.rationale)];

  return result;
}

// ── Helpers for alternative comparison ──────────────────────

function findGainRationale(kitId, kitRules, answers) {
  for (const rule of kitRules || []) {
    if (rule.recommend === kitId && matchesWhen(rule.when, answers)) {
      return rule.rationale;
    }
  }
  return null;
}

function findTradeoff(primaryId, altId, catalog) {
  const primary = catalog?.[primaryId];
  const alt = catalog?.[altId];
  if (!primary || !alt) return null;

  const tradeoffs = [];
  if (primary.pcr_free && !alt.pcr_free) tradeoffs.push('Introduces PCR bias');
  if (!primary.pcr_free && alt.pcr_free) tradeoffs.push('PCR-free but more hands-on');
  if (primary.prep_time && alt.prep_time && primary.prep_time < alt.prep_time) {
    tradeoffs.push('Longer preparation time');
  }
  if (primary.multiplexing === 'single sample' && alt.multiplexing !== 'single sample') {
    tradeoffs.push('Single sample only — no multiplexing');
  }
  return tradeoffs.length ? tradeoffs.join('; ') : 'Different trade-off profile';
}

// ── Page navigation helpers ─────────────────────────────────

const PAGE_ORDER = ['molecule', 'study_type', 'priority', 'constraints', 'results'];

function getPageSequence() {
  return PAGE_ORDER.slice();
}

function isPageComplete(pageId, answers, questionSpec) {
  if (pageId === 'results') return true;

  const page = questionSpec.pages.find(p => p.id === pageId);
  if (!page) return false;

  if (pageId === 'constraints') return true; // all optional

  for (const q of page.questions || []) {
    // Check if any visible option exists
    const visibleOpts = (q.options || []).filter(
      opt => !opt.visible_when || matchesWhen(opt.visible_when, answers)
    );
    if (visibleOpts.length === 0) continue;

    const val = answers[q.field];
    if (q.question_type === 'multi_select') {
      if (!val || !Array.isArray(val) || val.length === 0) return false;
    } else {
      if (val === undefined || val === null) return false;
      // Check the selected value is still visible
      if (!visibleOpts.some(opt => opt.value === val)) return false;
    }
  }
  return true;
}

function canReachPage(pageId, answers, questionSpec) {
  const seq = getPageSequence();
  const idx = seq.indexOf(pageId);
  if (idx < 0) return false;
  for (let i = 0; i < idx; i++) {
    if (!isPageComplete(seq[i], answers, questionSpec)) return false;
  }
  return true;
}

function nextPageId(currentId, answers, questionSpec) {
  const seq = getPageSequence();
  const idx = seq.indexOf(currentId);
  if (idx < 0 || idx >= seq.length - 1) return null;
  const next = seq[idx + 1];
  return canReachPage(next, answers, questionSpec) ? next : null;
}

function previousPageId(currentId) {
  const seq = getPageSequence();
  const idx = seq.indexOf(currentId);
  return idx > 0 ? seq[idx - 1] : null;
}

function firstIncompletePage(answers, questionSpec) {
  const seq = getPageSequence();
  for (const pid of seq) {
    if (!isPageComplete(pid, answers, questionSpec)) return pid;
  }
  return 'results';
}

// ── Normalize answers when upstream changes ─────────────────

function normalizeAnswers(answers, changedField, questionSpec) {
  const seq = ['molecule', 'study_type', 'priority', 'constraints'];
  const changedIdx = seq.indexOf(changedField);

  if (changedField === 'molecule') {
    // Changing molecule may invalidate study_type
    const studyPage = questionSpec.pages.find(p => p.id === 'study_type');
    if (studyPage) {
      const q = studyPage.questions[0];
      const visibleOpts = (q.options || []).filter(
        opt => !opt.visible_when || matchesWhen(opt.visible_when, answers)
      );
      if (answers.study_type && !visibleOpts.some(o => o.value === answers.study_type)) {
        delete answers.study_type;
      }
    }
  }

  return answers;
}
