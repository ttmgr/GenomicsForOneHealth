(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
    return;
  }

  root.SelectorEngine = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const WEIGHTS = {
    category: 60,
    sample_types: 42,
    molecule_types: 34,
    analysis_goals: 44,
    input_formats: 24,
    library_modes: 18,
    supports_multiplexing: 6
  };

  function allQuestions(questionSpec) {
    return questionSpec.stages.flatMap((stage) => stage.questions);
  }

  function questionById(questionSpec, questionId) {
    return allQuestions(questionSpec).find((question) => question.id === questionId);
  }

  function questionByField(questionSpec, field) {
    return allQuestions(questionSpec).find((question) => question.field === field);
  }

  function optionFor(question, value) {
    return question.options.find((option) => option.value === value);
  }

  function isNeutral(question, value) {
    if (!question || !value) {
      return false;
    }

    const option = optionFor(question, value);
    return Boolean(option && option.neutral);
  }

  function stageQuestions(questionSpec, stageId) {
    return questionSpec.stages.find((stage) => stage.id === stageId)?.questions || [];
  }

  function stageComplete(questionSpec, answers, stageId) {
    return stageQuestions(questionSpec, stageId).every((question) => Boolean(answers[question.id]));
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

  function passesHardFilters(pipeline, answers, questionSpec) {
    for (const stage of questionSpec.stages) {
      for (const question of stage.questions) {
        if (question.stage !== "stage1") {
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

  function scorePipeline(pipeline, answers, questionSpec) {
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
          score += WEIGHTS[question.field] || 0;
          reasons.push(`${question.label}: ${optionFor(question, value).label}`);
        }
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
      const when = track.when || {};
      let score = 0;

      for (const [field, acceptedValues] of Object.entries(when)) {
        const question = questionByField(questionSpec, field);
        const value = question ? answers[question.id] : null;

        if (!value || isNeutral(question, value)) {
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

  function labelForValue(questionSpec, questionId, value) {
    const question = questionById(questionSpec, questionId);
    if (!question) {
      return value;
    }

    return optionFor(question, value)?.label || value;
  }

  function formatFieldValues(questionSpec, field, values) {
    const question = questionByField(questionSpec, field);
    return values.map((value) => (question ? optionFor(question, value)?.label || value : value)).join(", ");
  }

  function matchesAnswerRule(answers, conditions) {
    if (!conditions) {
      return true;
    }

    return Object.entries(conditions).every(([questionId, acceptedValues]) => {
      const value = answers[questionId];
      if (!value) {
        return false;
      }

      return acceptedValues.includes(value);
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

  function derivePreprocessing(pipeline, track, playbook) {
    if (playbook?.preprocessing_defaults) {
      return playbook.preprocessing_defaults;
    }

    return {
      ...pipeline.default_preprocessing,
      ...(track?.preprocessing_override || {})
    };
  }

  function resolvePlaybook(playbooks, pipelineId, trackId) {
    const directMatch = playbooks.find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === trackId);
    if (directMatch) {
      return directMatch;
    }

    return playbooks.find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === null) || null;
  }

  function filterConditionalItems(items, answers) {
    return (items || []).filter((item) => !item.when || matchesAnswerRule(answers, item.when));
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
        title: "No exact current pipeline",
        text: "The current collection does not contain a workflow that exactly matches all Stage 1 answers. This recommendation is the nearest documented starting point in the existing repository."
      });
    }

    const inputQuestion = questionById(questionSpec, "input_format");
    const inputValue = answers.input_format;
    if (inputValue && inputQuestion && !isNeutral(inputQuestion, inputValue) && !matchesFieldValue(pipeline, "input_formats", inputValue)) {
      warnings.push({
        title: "Input-format adaptation required",
        text: `Your current input format is ${labelForValue(questionSpec, "input_format", inputValue)}. The documented workflow is written primarily for ${formatFieldValues(questionSpec, "input_formats", pipeline.input_formats)}. Some adaptation may be required before you can run it exactly as published.`
      });
    }

    const libraryQuestion = questionById(questionSpec, "library_mode");
    const libraryValue = answers.library_mode;
    if (libraryValue && libraryQuestion && !isNeutral(libraryQuestion, libraryValue) && pipeline.library_modes.length > 0 && !matchesFieldValue(pipeline, "library_modes", libraryValue)) {
      warnings.push({
        title: "Library-mode mismatch",
        text: `You selected ${labelForValue(questionSpec, "library_mode", libraryValue)}, but this workflow is documented mainly for ${formatFieldValues(questionSpec, "library_modes", pipeline.library_modes)}. Treat the recommendation as a starting point rather than an exact protocol match.`
      });
    }

    if (answers.demultiplexing === "needed" && !pipeline.supports_multiplexing) {
      warnings.push({
        title: "Demultiplexing not central to this workflow",
        text: "You indicated that demultiplexing is still needed, but multiplexing is not a central documented mode for this workflow. Confirm whether your data should be separated upstream before using this pipeline."
      });
    }

    if (answers.basecalling_state === "already_basecalled") {
      warnings.push({
        title: "Basecalling can likely be skipped",
        text: "You indicated that reads are already basecalled. Start at the read-level preprocessing stage and verify that the current files and thresholds match the documented workflow."
      });
    } else if (answers.basecalling_state === "raw_signal_not_basecalled") {
      warnings.push({
        title: "Raw-data entry point",
        text: `This recommendation assumes a raw-data entry point compatible with ${formatFieldValues(questionSpec, "input_formats", pipeline.input_formats)}. Use the documented basecalling branch before downstream preprocessing.`
      });
    } else if (answers.basecalling_state === "prefer_fast") {
      warnings.push({
        title: "FAST tier selected",
        text: "FAST is the speed-first Dorado tier. Use it when turnaround time matters most, but expect lower accuracy than HAC or SUP."
      });
    } else if (answers.basecalling_state === "prefer_sup") {
      warnings.push({
        title: "SUP tier selected",
        text: "SUP is the accuracy-first Dorado tier. It is often sensible for assembly-sensitive work, but it carries the highest computational cost."
      });
    }

    if (answers.preprocessing_state === "already_trimmed_and_filtered") {
      warnings.push({
        title: "Read preprocessing may already be complete",
        text: "You indicated that adapter trimming and read filtering are already done. Verify that the published thresholds still match your processed reads before skipping those steps."
      });
    }

    if (track?.notes?.length) {
      for (const note of track.notes) {
        warnings.push({
          title: track.title,
          text: note
        });
      }
    }

    return warnings;
  }

  function buildOntNotes(answers) {
    const libraryReference = {
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
        description: "RNA002 is an older native-RNA branch and should be treated as a legacy chemistry condition.",
        url: "https://nanoporetech.com/document/direct-rna-sequencing-sqk-rna002",
        urlLabel: "Legacy protocol"
      },
      direct_rna004: {
        title: "Direct RNA Sequencing Kit (SQK-RNA004)",
        description: "Oxford Nanopore positions SQK-RNA004 for sequencing native RNA directly, without cDNA conversion or PCR.",
        url: "https://store.nanoporetech.com/us/direct-rna-sequencing-kit-004.html",
        urlLabel: "Official kit page"
      },
      cdna_rbk: {
        title: "PCR-cDNA Sequencing V14 - Barcoding",
        description: "This branch is distinct from native direct RNA and uses reverse transcription, cDNA amplification, and barcode primers before loading.",
        url: "https://nanoporetech.com/document/pcr-cdna-sequencing-v14-barcoding-sqk-pcb114-24",
        urlLabel: "Official protocol"
      }
    };

    const doradoReference = {
      raw_signal_not_basecalled: {
        title: "Dorado simplex basecalling",
        description: "If you are entering from POD5 or FAST5, use Dorado's simplex basecalling documentation to select the latest compatible model for your chemistry and pore type.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/basecaller/simplex/",
        urlLabel: "Simplex basecalling docs"
      },
      prefer_fast: {
        title: "Dorado FAST",
        description: "FAST is the quickest Dorado tier and the least computationally expensive, but also the least accurate of the standard simplex options.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Model selection guide"
      },
      prefer_hac: {
        title: "Dorado HAC",
        description: "Oxford Nanopore recommends HAC for most users because it balances accuracy and compute cost.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Model selection guide"
      },
      prefer_sup: {
        title: "Dorado SUP",
        description: "SUP is the most accurate standard simplex tier and is useful when assembly quality or difficult calls are the priority.",
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

  function chooseConfidence(status, ranked, warnings) {
    const scoreGap = ranked.length > 1 ? ranked[0].score - ranked[1].score : ranked[0]?.score || 0;

    if (status === "unsupported") {
      return "low";
    }

    if (status === "closest_supported") {
      if (warnings.length >= 3 || scoreGap < 18) {
        return "low";
      }
      return "moderate";
    }

    if (warnings.length === 0 && scoreGap >= 18) {
      return "high";
    }

    return "moderate";
  }

  function confidenceSummary(status, confidence, candidateCount, scoreGap) {
    if (status === "unsupported") {
      return "This case falls outside the currently published collection. The selector is showing the nearest documented starting point without claiming full support.";
    }

    if (status === "closest_supported") {
      if (confidence === "low") {
        return "This is a partial fit with multiple adaptations likely required. Use the listed docs as a starting point rather than a validated protocol match.";
      }
      return "This is the nearest supported route in the current repository. Some workflow adaptation is still likely required.";
    }

    if (candidateCount > 1 && scoreGap < 18) {
      return "More than one published workflow remains plausible. The selector is choosing the strongest current fit, but nearby alternatives are also worth reviewing.";
    }

    if (status === "track_exact") {
      return "The umbrella workflow is an exact current fit, and the selector identified a specific internal branch that best matches your study intent.";
    }

    return "The selected workflow is a strong current fit for the stated biological context and documented analytical objective.";
  }

  function statusLabel(status) {
    if (status === "exact") {
      return "Exact current match";
    }
    if (status === "track_exact") {
      return "Exact workflow + track";
    }
    if (status === "closest_supported") {
      return "Nearest current starting point";
    }
    return "Unsupported / nearest start";
  }

  function explainRecommendation(status, pipeline, track) {
    if (status === "unsupported") {
      return `${pipeline.title} is the nearest documented starting point in the collection, but the answers you provided fall outside the workflows that are currently published here.`;
    }

    if (status === "closest_supported") {
      return `${pipeline.title} is the nearest documented starting point in the current collection, but at least one of your Stage 1 answers falls outside the workflows that are presently published in this repository.`;
    }

    if (track) {
      return `${pipeline.title} is the strongest current fit for your use case within the published collection. The selected internal branch is ${track.title}.`;
    }

    return `${pipeline.title} is the strongest current fit for your biological use case, sample type, and analytical objective within the published collection.`;
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

    const fallbackIds = (primary.closest_alternatives || [])
      .map((pipelineId) => pipelinesById.get(pipelineId))
      .filter(Boolean);

    return [...rankedAlternatives, ...fallbackIds]
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
    const pool = exactCandidates.length > 0 ? exactCandidates : pipelines;
    const ranked = pool
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

    let primary = ranked[0].pipeline;
    let track = chooseTrack(primary, answers, questionSpec);
    let status = exactCandidates.length > 0 ? (track ? "track_exact" : "exact") : "closest_supported";

    if (outOfScopeRule) {
      primary = pipelinesById.get(outOfScopeRule.primary_nearest_pipeline) || primary;
      track = chooseTrack(primary, answers, questionSpec);
      status = "unsupported";
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
      confidenceLabel: confidence.charAt(0).toUpperCase() + confidence.slice(1),
      fitSummary: confidenceSummary(status, confidence, exactCandidates.length, scoreGap),
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
        reasons: ranked[0].reasons.slice(0, 6)
      },
      warnings,
      ontNotes: buildOntNotes(answers),
      explanation: explainRecommendation(status, primary, track),
      outOfScopeRule
    };
  }

  return {
    stageQuestions,
    stageComplete,
    allQuestions,
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
