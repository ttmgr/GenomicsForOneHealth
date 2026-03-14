(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
    return;
  }

  root.SelectorEngine = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const WEIGHTS = {
    sequencing_contexts: 80,
    library_modes: 60,
    analysis_goals: 48,
    sample_types: 36,
    input_formats: 18,
    supports_multiplexing: 6
  };

  function allQuestions(questionSpec) {
    return questionSpec.stages.flatMap((stage) => stage.questions);
  }

  function stageQuestions(questionSpec, stageId) {
    return questionSpec.stages.find((stage) => stage.id === stageId)?.questions || [];
  }

  function questionById(questionSpec, questionId) {
    return allQuestions(questionSpec).find((question) => question.id === questionId) || null;
  }

  function questionByField(questionSpec, field) {
    return allQuestions(questionSpec).find((question) => question.field === field) || null;
  }

  function optionFor(question, value) {
    return question?.options.find((option) => option.value === value) || null;
  }

  function isNeutral(question, value) {
    return Boolean(optionFor(question, value)?.neutral);
  }

  function stageComplete(questionSpec, answers, stageId) {
    return stageQuestions(questionSpec, stageId)
      .filter((question) => !question.optional)
      .every((question) => Boolean(answers[question.id]));
  }

  function matchesFieldValue(pipeline, field, value) {
    if (!value) {
      return false;
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

  function stage1Questions(questionSpec) {
    return stageQuestions(questionSpec, "stage1");
  }

  function allSpecificStage1Answers(questionSpec, answers) {
    return stage1Questions(questionSpec).every((question) => {
      const value = answers[question.id];
      return Boolean(value) && !isNeutral(question, value);
    });
  }

  function passesHardFilters(pipeline, answers, questionSpec) {
    for (const question of stage1Questions(questionSpec)) {
      if (question.hard_filter === false || question.optional) {
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

    return true;
  }

  function scorePipeline(pipeline, answers, questionSpec) {
    let score = 0;
    const reasons = [];

    for (const question of allQuestions(questionSpec)) {
      const value = answers[question.id];
      if (!value || isNeutral(question, value)) {
        continue;
      }

      if (question.field === "supports_multiplexing") {
        if (matchesFieldValue(pipeline, question.field, value)) {
          score += WEIGHTS.supports_multiplexing;
          reasons.push(`${question.label}: ${optionFor(question, value)?.label || value}`);
        }
        continue;
      }

      const weight = WEIGHTS[question.field];
      if (!weight) {
        continue;
      }

      if (matchesFieldValue(pipeline, question.field, value)) {
        score += weight;
        reasons.push(`${question.label}: ${optionFor(question, value)?.label || value}`);
      }
    }

    return { score, reasons };
  }

  function chooseTrack(pipeline, answers, questionSpec) {
    if (!Array.isArray(pipeline.track_notes) || pipeline.track_notes.length === 0) {
      return null;
    }

    let bestTrack = null;
    let bestScore = -1;

    for (const track of pipeline.track_notes) {
      let score = 0;
      let failed = false;

      for (const [field, acceptedValues] of Object.entries(track.when || {})) {
        const question = questionByField(questionSpec, field);
        const value = question ? answers[question.id] : null;

        if (!value || isNeutral(question, value)) {
          continue;
        }

        if (!acceptedValues.includes(value)) {
          failed = true;
          break;
        }

        score += 1;
      }

      if (!failed && score > bestScore) {
        bestScore = score;
        bestTrack = score > 0 ? track : null;
      }
    }

    return bestTrack;
  }

  function matchesAnswerRule(answers, conditions) {
    if (!conditions) {
      return true;
    }

    return Object.entries(conditions).every(([questionId, acceptedValues]) => {
      const value = answers[questionId];
      return Boolean(value) && acceptedValues.includes(value);
    });
  }

  function resolveOutOfScopeCase(answers, outOfScopeRules) {
    for (const rule of outOfScopeRules) {
      if (!matchesAnswerRule(answers, rule.when)) {
        continue;
      }

      if (rule.unless && matchesAnswerRule(answers, rule.unless)) {
        continue;
      }

      return rule;
    }

    return null;
  }

  function resolvePlaybook(playbooks, pipelineId, trackId) {
    return (
      playbooks.find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === trackId) ||
      playbooks.find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === null) ||
      null
    );
  }

  function filterConditionalItems(items, answers) {
    return (items || []).filter((item) => !item.when || matchesAnswerRule(answers, item.when));
  }

  function derivePreprocessing(pipeline, track, playbook) {
    if (playbook?.preprocessing_defaults) {
      return playbook.preprocessing_defaults;
    }

    return {
      ...pipeline.default_preprocessing,
      ...(track?.preprocessing_override || {})
    };
  }

  function labelForValue(questionSpec, questionId, value) {
    const question = questionById(questionSpec, questionId);
    return optionFor(question, value)?.label || value;
  }

  function formatFieldValues(questionSpec, field, values) {
    const question = questionByField(questionSpec, field);
    return values.map((value) => (question ? optionFor(question, value)?.label || value : value)).join(", ");
  }

  function buildCompatibilityWarnings(pipeline, track, status, answers, questionSpec, rule) {
    const warnings = [];

    if (status === "unsupported" && rule) {
      warnings.push({
        title: "Unsupported scenario",
        text: rule.message
      });
      warnings.push({
        title: "Why this is not exact",
        text: rule.why_not_exact
      });
    } else if (status === "closest_supported") {
      warnings.push({
        title: "Generalized route, nearest backend",
        text: "The current repository does not contain an exact published example for all Stage 1 answers. This recommendation is the nearest documented backend already present in the collection."
      });
    }

    const inputQuestion = questionById(questionSpec, "input_format");
    const inputValue = answers.input_format;
    if (
      inputValue &&
      inputQuestion &&
      !isNeutral(inputQuestion, inputValue) &&
      Array.isArray(pipeline.input_formats) &&
      pipeline.input_formats.length > 0 &&
      !matchesFieldValue(pipeline, "input_formats", inputValue)
    ) {
      warnings.push({
        title: "Input-format adaptation required",
        text: `You selected ${labelForValue(questionSpec, "input_format", inputValue)}, but this published backend is documented primarily for ${formatFieldValues(questionSpec, "input_formats", pipeline.input_formats)}.`
      });
    }

    const libraryQuestion = questionById(questionSpec, "library_mode");
    const libraryValue = answers.library_mode;
    if (
      libraryValue &&
      libraryQuestion &&
      !isNeutral(libraryQuestion, libraryValue) &&
      Array.isArray(pipeline.library_modes) &&
      pipeline.library_modes.length > 0 &&
      !matchesFieldValue(pipeline, "library_modes", libraryValue)
    ) {
      warnings.push({
        title: "Kit or run-mode mismatch",
        text: `You selected ${labelForValue(questionSpec, "library_mode", libraryValue)}, but this published backend is documented mainly for ${formatFieldValues(questionSpec, "library_modes", pipeline.library_modes)}.`
      });
    }

    if (answers.demultiplexing === "needed" && !pipeline.supports_multiplexing) {
      warnings.push({
        title: "Demultiplexing is not central here",
        text: "You indicated that demultiplexing is still needed, but multiplexing is not a central documented mode for this published backend."
      });
    }

    if (answers.basecalling_state === "already_basecalled") {
      warnings.push({
        title: "Basecalling can likely be skipped",
        text: "You indicated that reads are already basecalled. Start at the read-level preprocessing stage and confirm that the current files still match the documented thresholds."
      });
    } else if (answers.basecalling_state === "raw_signal_not_basecalled") {
      warnings.push({
        title: "Raw-data entry point",
        text: "This recommendation assumes a raw-data entry path. Start with the published basecalling branch before trimming, filtering, or downstream analysis."
      });
    } else if (answers.basecalling_state === "prefer_fast") {
      warnings.push({
        title: "FAST tier selected",
        text: "FAST favors turnaround time over accuracy. That can be reasonable for screening, but it is less conservative for assembly-sensitive workflows."
      });
    } else if (answers.basecalling_state === "prefer_sup") {
      warnings.push({
        title: "SUP tier selected",
        text: "SUP favors accuracy over compute efficiency and is often sensible for assembly and variant-sensitive analyses."
      });
    }

    if (answers.preprocessing_state === "already_trimmed_and_filtered") {
      warnings.push({
        title: "Read preprocessing may already be complete",
        text: "You indicated that trimming and filtering are already done. Confirm that the documented thresholds still match your processed reads before skipping those steps."
      });
    }

    for (const note of track?.notes || []) {
      warnings.push({
        title: track.title,
        text: note
      });
    }

    return warnings;
  }

  function buildOntNotes(answers) {
    const libraryReference = {
      rbk114_24: {
        title: "Rapid Barcoding Kit 24 V14",
        description: "SQK-RBK114.24 is Oxford Nanopore's rapid, PCR-free barcoding workflow for multiplexed DNA sequencing.",
        url: "https://store.nanoporetech.com/rapid-barcoding-sequencing-kit-24-v14.html",
        urlLabel: "Official kit page"
      },
      nbd114_24: {
        title: "Native Barcoding Kit 24 V14",
        description: "SQK-NBD114.24 is Oxford Nanopore's ligation-based barcoding workflow for multiplexed DNA sequencing with preserved fragment length.",
        url: "https://store.nanoporetech.com/native-barcoding-kit-24-v14.html",
        urlLabel: "Official kit page"
      }
    };

    const doradoReference = {
      raw_signal_not_basecalled: {
        title: "Dorado simplex basecalling",
        description: "Use Dorado simplex basecalling guidance if you are entering from POD5 or FAST5 and still need a basecalling step.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/basecaller/simplex/",
        urlLabel: "Simplex basecalling docs"
      },
      prefer_fast: {
        title: "Dorado FAST",
        description: "FAST is the quickest standard Dorado tier and the least computationally expensive.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Model selection guide"
      },
      prefer_hac: {
        title: "Dorado HAC",
        description: "HAC is the balanced Dorado tier for most users when accuracy and compute cost both matter.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Model selection guide"
      },
      prefer_sup: {
        title: "Dorado SUP",
        description: "SUP is the most accurate standard Dorado tier and is useful when downstream accuracy matters most.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Model selection guide"
      }
    };

    const notes = [];
    if (libraryReference[answers.library_mode]) {
      notes.push(libraryReference[answers.library_mode]);
    }
    if (doradoReference[answers.basecalling_state]) {
      notes.push(doradoReference[answers.basecalling_state]);
    }
    return notes;
  }

  function statusLabel(status) {
    if (status === "exact") {
      return "Published example match";
    }
    if (status === "track_exact") {
      return "Published example + branch";
    }
    if (status === "closest_supported") {
      return "Generalized route -> nearest published example";
    }
    return "Unsupported / nearest published example";
  }

  function chooseConfidence(status, ranked, warnings) {
    const scoreGap = ranked.length > 1 ? ranked[0].score - ranked[1].score : ranked[0]?.score || 0;

    if (status === "unsupported") {
      return "low";
    }

    if (status === "closest_supported") {
      return warnings.length >= 3 || scoreGap < 20 ? "low" : "moderate";
    }

    if (warnings.length === 0 && scoreGap >= 24) {
      return "high";
    }

    return "moderate";
  }

  function confidenceSummary(status, confidence, exactCandidateCount, scoreGap) {
    if (status === "unsupported") {
      return "This case falls outside the published selector boundary. The action sheet below shows the nearest documented backend without claiming exact support.";
    }

    if (status === "closest_supported") {
      if (confidence === "low") {
        return "This is a generalized route with multiple adaptations likely required. Treat the recommended backend as a starting point rather than a validated protocol match.";
      }
      return "This is a generalized route mapped to the nearest published example currently available in the repository.";
    }

    if (status === "track_exact") {
      return "The selected workflow is an exact published match, and a specific internal wetland branch can be chosen directly from your answers.";
    }

    if (exactCandidateCount > 1 && scoreGap < 20) {
      return "More than one published example remains plausible, but the selector still found one dominant backend.";
    }

    return "The selected workflow is an exact published example match for the sequencing context, kit or run mode, goal, and sample context you provided.";
  }

  function explainRecommendation(status, pipeline, track) {
    if (status === "unsupported") {
      return `${pipeline.title} is the nearest published backend in the collection, but your stated route is outside the workflows that are currently documented here.`;
    }

    if (status === "closest_supported") {
      return `${pipeline.title} is the nearest published backend for the generalized route you selected. Use it as a documented starting point rather than as an exact one-to-one protocol match.`;
    }

    if (track) {
      return `${pipeline.title} is the exact published example for your route, and ${track.title} is the matching internal branch.`;
    }

    return `${pipeline.title} is the exact published example backend for the route you selected.`;
  }

  function buildAlternatives(primary, ranked, exactCandidates, pipelinesById, outOfScopeRule) {
    if (outOfScopeRule) {
      return (outOfScopeRule.secondary_nearest_pipelines || [])
        .map((pipelineId) => pipelinesById.get(pipelineId))
        .filter(Boolean)
        .slice(0, 2);
    }

    const rankedAlternatives = ranked
      .map((entry) => entry.pipeline)
      .filter((pipeline) => pipeline.id !== primary.id);

    const fallbackAlternatives = (primary.closest_alternatives || [])
      .map((pipelineId) => pipelinesById.get(pipelineId))
      .filter(Boolean);

    return [...rankedAlternatives, ...fallbackAlternatives]
      .filter((pipeline, index, collection) => collection.findIndex((candidate) => candidate.id === pipeline.id) === index)
      .slice(0, exactCandidates.length > 1 ? 2 : 1);
  }

  function computeRecommendation(answers, datasets) {
    const { pipelines, questionSpec, playbooks, outOfScopeRules } = datasets;

    if (!stageComplete(questionSpec, answers, "stage1")) {
      return null;
    }

    const pipelinesById = new Map(pipelines.map((pipeline) => [pipeline.id, pipeline]));
    const outOfScopeRule = resolveOutOfScopeCase(answers, outOfScopeRules);
    const exactCandidates = pipelines.filter((pipeline) => passesHardFilters(pipeline, answers, questionSpec));
    const candidatePool = exactCandidates.length > 0 ? exactCandidates : pipelines;
    const ranked = candidatePool
      .map((pipeline) => ({
        pipeline,
        ...scorePipeline(pipeline, answers, questionSpec)
      }))
      .sort((left, right) => {
        if (right.score !== left.score) {
          return right.score - left.score;
        }
        return left.pipeline.title.localeCompare(right.pipeline.title);
      });

    let primary = ranked[0]?.pipeline || pipelines[0];
    let track = chooseTrack(primary, answers, questionSpec);
    let status = "closest_supported";
    const stage1Specific = allSpecificStage1Answers(questionSpec, answers);

    if (outOfScopeRule) {
      primary = pipelinesById.get(outOfScopeRule.primary_nearest_pipeline) || primary;
      track = chooseTrack(primary, answers, questionSpec);
      status = "unsupported";
    } else if (exactCandidates.length > 0 && stage1Specific && exactCandidates.length === 1) {
      status = track ? "track_exact" : "exact";
    }

    const playbook = resolvePlaybook(playbooks, primary.id, track?.id || null);
    const preprocessing = derivePreprocessing(primary, track, playbook);
    const warnings = buildCompatibilityWarnings(primary, track, status, answers, questionSpec, outOfScopeRule);
    const confidence = chooseConfidence(status, ranked, warnings);
    const scoreGap = ranked.length > 1 ? ranked[0].score - ranked[1].score : ranked[0]?.score || 0;

    return {
      status,
      statusLabel: statusLabel(status),
      confidence,
      confidenceLabel: `${confidence.charAt(0).toUpperCase()}${confidence.slice(1)} confidence`,
      fitSummary: confidenceSummary(status, confidence, exactCandidates.length, scoreGap),
      explanation: explainRecommendation(status, primary, track),
      primary: {
        pipeline: primary,
        track,
        playbook,
        preprocessing,
        entryActions: filterConditionalItems(playbook?.entry_actions, answers),
        curatedCommands: filterConditionalItems(playbook?.curated_commands, answers)
      },
      alternatives: buildAlternatives(primary, ranked, exactCandidates, pipelinesById, outOfScopeRule),
      decision_trace: {
        exactCandidateCount: exactCandidates.length,
        scoreGap,
        stage1Specific,
        reasons: (ranked[0]?.reasons || []).slice(0, 6)
      },
      warnings,
      ontNotes: buildOntNotes(answers),
      outOfScopeRule
    };
  }

  return {
    allQuestions,
    stageQuestions,
    stageComplete,
    questionById,
    questionByField,
    optionFor,
    isNeutral,
    passesHardFilters,
    scorePipeline,
    chooseTrack,
    classifyRecommendation: chooseConfidence,
    resolveOutOfScopeCase,
    computeRecommendation
  };
});
