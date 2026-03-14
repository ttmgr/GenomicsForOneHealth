(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
    return;
  }

  root.SelectorEngine = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const WIZARD_ORDER = ["sample", "material", "target", "example", "expert", "results"];
  const ROUTE_PAGE_IDS = ["sample", "material", "target"];
  const ROUTE_QUESTION_IDS = ["sample_context", "material_class", "target_goal"];
  const GENERIC_OPTION_DOC_LABEL = "Selected backend documentation";

  function allQuestions(questionSpec) {
    return (questionSpec?.pages || []).flatMap((page) => page.questions || []);
  }

  function pageById(questionSpec, pageId) {
    return (questionSpec?.pages || []).find((page) => page.id === pageId) || null;
  }

  function questionById(questionSpec, questionId) {
    return allQuestions(questionSpec).find((question) => question.id === questionId) || null;
  }

  function optionFor(question, value) {
    return (question?.options || []).find((option) => option.value === value) || null;
  }

  function isNeutral(question, value) {
    return Boolean(optionFor(question, value)?.neutral);
  }

  function matchesVisibleWhen(questionSpec, answers, visibleWhen) {
    if (!visibleWhen) {
      return true;
    }

    return Object.entries(visibleWhen).every(([questionId, acceptedValues]) => {
      const dependencyValue = answers[questionId];
      if (!dependencyValue) {
        return false;
      }
      return acceptedValues.includes(dependencyValue);
    });
  }

  function isQuestionVisible(questionSpec, question, answers) {
    return matchesVisibleWhen(questionSpec, answers, question?.visible_when || null);
  }

  function visibleOptionsForQuestion(questionSpec, question, answers) {
    if (question?.dynamic_options_from) {
      return [];
    }

    const options = question?.options || [];
    if (!options.some((option) => option.visible_when)) {
      return options;
    }

    return options.filter((option) => matchesVisibleWhen(questionSpec, answers, option.visible_when || null));
  }

  function hasConcreteAnswer(questionSpec, answers, questionId) {
    const question = questionById(questionSpec, questionId);
    const value = answers[questionId];
    if (!value) {
      return false;
    }
    return !isNeutral(question, value);
  }

  function routeComplete(questionSpec, answers) {
    return ROUTE_QUESTION_IDS.every((questionId) => hasConcreteAnswer(questionSpec, answers, questionId));
  }

  function exampleMatches(example, answers) {
    const mappings = [
      ["sample_context", "sample_contexts"],
      ["material_class", "material_classes"],
      ["target_goal", "target_goals"]
    ];

    return mappings.every(([questionId, field]) => {
      const value = answers[questionId];
      return Boolean(value) && (example[field] || []).includes(value);
    });
  }

  function getEligibleExamples(answers, datasets) {
    if (!routeComplete(datasets.questionSpec, answers)) {
      return [];
    }

    return (datasets.examples || []).filter((example) => exampleMatches(example, answers));
  }

  function needsExampleSelection(answers, datasets) {
    return getEligibleExamples(answers, datasets).length > 1;
  }

  function resolveSelectedExample(answers, datasets) {
    const eligibleExamples = getEligibleExamples(answers, datasets);
    if (eligibleExamples.length === 0) {
      return null;
    }

    if (eligibleExamples.length === 1) {
      return eligibleExamples[0];
    }

    const exampleId = answers.example_context;
    if (!exampleId) {
      return null;
    }

    return eligibleExamples.find((example) => example.id === exampleId) || null;
  }

  function resolveBackend(selectedExample, datasets) {
    if (!selectedExample) {
      return null;
    }

    const pipelinesById = new Map((datasets.pipelines || []).map((pipeline) => [pipeline.id, pipeline]));
    const pipelineId = selectedExample.status_class === "exact" ? selectedExample.pipeline_id : selectedExample.nearest_pipeline_id;
    const trackId = selectedExample.status_class === "exact" ? selectedExample.track_id : selectedExample.nearest_track_id;
    const pipeline = pipelinesById.get(pipelineId) || null;
    const track = pipeline?.track_notes?.find((entry) => entry.id === trackId) || null;

    return { pipeline, track };
  }

  function resolvePlaybook(playbooks, pipelineId, trackId) {
    return (
      (playbooks || []).find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === trackId) ||
      (playbooks || []).find((playbook) => playbook.pipeline_id === pipelineId && playbook.track_id === null) ||
      null
    );
  }

  function derivePreprocessing(pipeline, track, playbook) {
    if (playbook?.preprocessing_defaults) {
      return { ...playbook.preprocessing_defaults };
    }

    return {
      ...(pipeline?.default_preprocessing || {}),
      ...(track?.preprocessing_override || {})
    };
  }

  function fallbackDoc(pipeline, playbook) {
    return playbook?.evidence_links?.[0] || pipeline?.setup_docs?.[0] || pipeline?.primary_docs?.[0] || null;
  }

  function ruleMatchesAnswers(answers, when) {
    if (!when) {
      return true;
    }

    return Object.entries(when).every(([questionId, acceptedValues]) => {
      const answer = answers[questionId];
      return Boolean(answer) && acceptedValues.includes(answer);
    });
  }

  function matchingRules(selectedExample, answers, expertRules) {
    if (!selectedExample) {
      return [];
    }

    return (expertRules || [])
      .filter((rule) => (rule.applies_to_example_ids || []).includes(selectedExample.id))
      .filter((rule) => ruleMatchesAnswers(answers, rule.when))
      .sort((left, right) => (right.priority || 0) - (left.priority || 0));
  }

  function genericCleaningAction(answers, pipeline, playbook) {
    const state = answers.preprocessing_state;
    const doc = fallbackDoc(pipeline, playbook);
    const base = {
      id: "generic_read_cleaning",
      priority: 60,
      doc_url: doc?.url || "",
      entry_file: doc?.label || GENERIC_OPTION_DOC_LABEL
    };

    if (state === "need_trim_and_filter") {
      return {
        ...base,
        title: "Trim adapters and filter reads",
        summary: "Run the route-appropriate adapter cleanup and read-length or quality filtering before downstream workflow entry."
      };
    }

    if (state === "need_trim_only") {
      return {
        ...base,
        title: "Trim adapters before downstream analysis",
        summary: "Adapter or primer cleanup is still needed before entering the documented backend."
      };
    }

    if (state === "need_filter_only") {
      return {
        ...base,
        title: "Filter reads before downstream analysis",
        summary: "Apply the route-appropriate quality or length filtering before continuing."
      };
    }

    return null;
  }

  function dedupeById(items) {
    return items.filter((item, index, collection) => collection.findIndex((candidate) => candidate.id === item.id) === index);
  }

  function applyExpertRules(answers, selectedExample, pipeline, track, playbook, datasets) {
    const rules = matchingRules(selectedExample, answers, datasets.expertRules);
    const genericCleaning = genericCleaningAction(answers, pipeline, playbook);
    const insertedActions = genericCleaning ? [genericCleaning] : [];
    const skippedIds = new Set();
    const warnings = [];
    const expertEffects = [];
    const preprocessingOverrides = {};
    const toolOverrides = [];
    const doc = fallbackDoc(pipeline, playbook);

    for (const rule of rules) {
      expertEffects.push({
        title: rule.title,
        summary: rule.summary,
        effect_type: rule.effect_type
      });

      if (rule.warning) {
        warnings.push({
          title: rule.title,
          text: rule.warning
        });
      }

      if (rule.effect_type === "tool_swap" && rule.tool_override) {
        toolOverrides.push(`${rule.tool_override.from} -> ${rule.tool_override.to}`);
      }

      if (rule.effect_type === "preprocessing_override" && rule.preprocessing_override) {
        Object.assign(preprocessingOverrides, rule.preprocessing_override);
      }

      if (rule.effect_type === "step_insert" && rule.step_insertion) {
        insertedActions.push({
          id: rule.step_insertion.id,
          title: rule.step_insertion.title,
          summary: rule.step_insertion.summary,
          priority: rule.priority || 0,
          doc_url: doc?.url || "",
          entry_file: doc?.label || GENERIC_OPTION_DOC_LABEL
        });
      }

      if (rule.effect_type === "step_skip") {
        for (const stepId of rule.target_step_ids || []) {
          skippedIds.add(stepId);
        }
      }
    }

    if (toolOverrides.length > 0) {
      const current = preprocessingOverrides.additional_preprocessing || playbook?.preprocessing_defaults?.additional_preprocessing || pipeline?.default_preprocessing?.additional_preprocessing || "";
      preprocessingOverrides.additional_preprocessing = [
        `Expert heuristic overrides: ${toolOverrides.join("; ")}.`,
        current
      ].filter(Boolean).join(" ");
    }

    return {
      expertEffects,
      warnings,
      insertedActions: dedupeById(
        insertedActions
          .filter((action) => !skippedIds.has(action.id))
          .sort((left, right) => (right.priority || 0) - (left.priority || 0))
      ),
      preprocessingOverrides
    };
  }

  function filterCommands(commands, answers) {
    return (commands || []).filter((command) => ruleMatchesAnswers(answers, command.when));
  }

  function buildKitConsequences(answers) {
    const map = {
      lsk114: {
        title: "LSK114 consequences",
        demultiplexing: "Not expected by default.",
        barcode_trimming: "Not expected unless barcodes were introduced upstream.",
        route_shape: "Single-sample or isolate-oriented handling.",
        first_changes: "Start from basecalling or adapter trimming, then continue into the selected backend."
      },
      rbk114_24: {
        title: "RBK114.24 consequences",
        demultiplexing: "Usually required when reads are still pooled.",
        barcode_trimming: "Expected as part of early preprocessing.",
        route_shape: "Barcoded, multiplexed handling.",
        first_changes: "Basecall if needed, then demultiplex, trim barcodes or adapters, and continue."
      },
      nbd114_24: {
        title: "NBD114.24 consequences",
        demultiplexing: "Usually required when reads are still pooled.",
        barcode_trimming: "Expected as part of early preprocessing.",
        route_shape: "Barcoded, multiplexed handling with ligation-based prep.",
        first_changes: "Basecall if needed, then demultiplex, trim barcodes or adapters, and continue."
      },
      amplicon_workflow: {
        title: "Amplicon workflow consequences",
        demultiplexing: "Depends on how the pool was prepared.",
        barcode_trimming: "Primer or adapter cleanup is usually still relevant.",
        route_shape: "Amplicon-focused entry rather than shotgun processing.",
        first_changes: "Use amplicon-aware cleanup and keep branch-specific interpretation in mind."
      },
      barcoded_metagenome: {
        title: "Barcoded metagenome consequences",
        demultiplexing: "Expected if pooled clinical metagenomes are not yet split.",
        barcode_trimming: "Expected before host-association analysis.",
        route_shape: "Multiplexed metagenomic handling.",
        first_changes: "Separate pooled reads before downstream host-association interpretation."
      },
      adaptive_sampling: {
        title: "Adaptive-sampling consequences",
        demultiplexing: "Only needed if barcodes were added upstream.",
        barcode_trimming: "Depends on whether barcodes are present.",
        route_shape: "Real-time enrichment or depletion framing.",
        first_changes: "Preserve target-enrichment context and keep matched controls aligned when available."
      },
      standard_control: {
        title: "Standard-control consequences",
        demultiplexing: "Only needed if barcodes were added upstream.",
        barcode_trimming: "Depends on whether barcodes are present.",
        route_shape: "Matched non-adaptive comparison framing.",
        first_changes: "Keep the control comparable to the adaptive-sampling branch when interpreting outputs."
      }
    };

    return map[answers.library_mode] || null;
  }

  function buildOntNotes(answers) {
    const notes = [];

    if (answers.library_mode === "rbk114_24") {
      notes.push({
        title: "Rapid Barcoding Kit 24 V14",
        description: "Oxford Nanopore rapid barcoding workflow for multiplexed DNA sequencing.",
        url: "https://store.nanoporetech.com/rapid-barcoding-sequencing-kit-24-v14.html",
        urlLabel: "Official kit page"
      });
    }

    if (answers.library_mode === "nbd114_24") {
      notes.push({
        title: "Native Barcoding Kit 24 V14",
        description: "Oxford Nanopore ligation-based barcoding workflow for multiplexed DNA sequencing.",
        url: "https://store.nanoporetech.com/native-barcoding-kit-24-v14.html",
        urlLabel: "Official kit page"
      });
    }

    if (answers.basecalling_state === "raw_signal_not_basecalled") {
      notes.push({
        title: "Dorado simplex basecalling",
        description: "Use Dorado basecalling before demultiplexing, trimming, or downstream analysis when starting from POD5 or FAST5.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/basecaller/simplex/",
        urlLabel: "Simplex basecalling docs"
      });
    }

    const modelGuideStates = ["prefer_fast", "prefer_hac", "prefer_sup"];
    if (modelGuideStates.includes(answers.basecalling_state)) {
      notes.push({
        title: `Dorado ${answers.basecalling_state.replace("prefer_", "").toUpperCase()} model guidance`,
        description: "Use the official Dorado model guide to match accuracy tier to chemistry and compute budget.",
        url: "https://software-docs.nanoporetech.com/dorado/latest/models/models/",
        urlLabel: "Dorado model guide"
      });
    }

    return notes;
  }

  function buildCompatibilityWarnings(answers, selectedExample, pipeline, expertWarnings) {
    const warnings = [...expertWarnings];

    if (selectedExample?.status_class === "unsupported_nearest") {
      warnings.unshift({
        title: "Unsupported route",
        text: selectedExample.unsupported_reason
      });
    }

    if (
      answers.input_format &&
      answers.input_format !== "unsure" &&
      Array.isArray(pipeline?.input_formats) &&
      pipeline.input_formats.length > 0 &&
      !pipeline.input_formats.includes(answers.input_format)
    ) {
      warnings.push({
        title: "Input-format adaptation required",
        text: `The selected backend is documented primarily for ${pipeline.input_formats.join(", ")} input rather than ${answers.input_format}.`
      });
    }

    return dedupeById(
      warnings.map((warning, index) => ({
        id: `warning_${index}_${warning.title}`,
        ...warning
      }))
    ).map(({ id, ...warning }) => warning);
  }

  function statusLabel(selectedExample, backend) {
    if (!selectedExample || !backend?.pipeline) {
      return "";
    }
    if (selectedExample.status_class === "unsupported_nearest") {
      return "Unsupported / nearest published example";
    }
    if (backend.track) {
      return "Published example + branch";
    }
    return "Published example match";
  }

  function explanationText(selectedExample, backend) {
    if (!selectedExample || !backend?.pipeline) {
      return "";
    }
    if (selectedExample.status_class === "unsupported_nearest") {
      return `${selectedExample.label} is not a published exact backend in this repository, so the wizard is using ${backend.pipeline.title}${backend.track ? ` (${backend.track.title})` : ""} as the nearest documented starting point.`;
    }
    return `${backend.pipeline.title}${backend.track ? ` (${backend.track.title})` : ""} is the published example backend selected for this route.`;
  }

  function computeRecommendation(answers, datasets) {
    if (!routeComplete(datasets.questionSpec, answers)) {
      return null;
    }

    const selectedExample = resolveSelectedExample(answers, datasets);
    if (!selectedExample) {
      return null;
    }

    const backend = resolveBackend(selectedExample, datasets);
    if (!backend?.pipeline) {
      return null;
    }

    const playbook = resolvePlaybook(datasets.playbooks || [], backend.pipeline.id, backend.track?.id || null);
    const preprocessing = derivePreprocessing(backend.pipeline, backend.track, playbook);
    const expert = applyExpertRules(answers, selectedExample, backend.pipeline, backend.track, playbook, datasets);
    const entryActions = dedupeById([
      ...expert.insertedActions,
      ...(playbook?.entry_actions || [])
    ]);
    const finalPreprocessing = {
      ...preprocessing,
      ...expert.preprocessingOverrides
    };

    return {
      route: {
        sample_context: answers.sample_context,
        material_class: answers.material_class,
        target_goal: answers.target_goal,
        summary: selectedExample.route_summary || ROUTE_QUESTION_IDS.map((questionId) => answers[questionId]).join(" -> ")
      },
      example: selectedExample,
      backend: {
        pipeline: backend.pipeline,
        track: backend.track,
        playbook
      },
      status: selectedExample.status_class === "unsupported_nearest" ? "unsupported" : backend.track ? "track_exact" : "exact",
      status_label: statusLabel(selectedExample, backend),
      explanation: explanationText(selectedExample, backend),
      expert_effects: expert.expertEffects,
      entry_actions: entryActions,
      curated_commands: filterCommands(playbook?.curated_commands || [], answers),
      preprocessing: finalPreprocessing,
      warnings: buildCompatibilityWarnings(answers, selectedExample, backend.pipeline, expert.warnings),
      docs: {
        primary: backend.pipeline.primary_docs || [],
        setup: backend.pipeline.setup_docs || [],
        evidence: playbook?.evidence_links || []
      },
      ont_notes: buildOntNotes(answers),
      kit_consequences: buildKitConsequences(answers)
    };
  }

  function questionComplete(questionSpec, answers, questionId) {
    return hasConcreteAnswer(questionSpec, answers, questionId);
  }

  function pageComplete(questionSpec, answers, pageId, datasets) {
    const page = pageById(questionSpec, pageId);
    if (!page) {
      return false;
    }

    if (pageId === "example") {
      if (!needsExampleSelection(answers, datasets)) {
        return true;
      }
      return Boolean(resolveSelectedExample(answers, datasets));
    }

    if (pageId === "expert") {
      return Boolean(resolveSelectedExample(answers, datasets) || (!needsExampleSelection(answers, datasets) && getEligibleExamples(answers, datasets).length === 1));
    }

    if (pageId === "results") {
      return Boolean(computeRecommendation(answers, datasets));
    }

    return (page.questions || [])
      .filter((question) => isQuestionVisible(questionSpec, question, answers))
      .every((question) => questionComplete(questionSpec, answers, question.id));
  }

  function canReachPage(pageId, answers, datasets) {
    const questionSpec = datasets.questionSpec;

    if (pageId === "sample") {
      return true;
    }

    if (pageId === "material") {
      return pageComplete(questionSpec, answers, "sample", datasets);
    }

    if (pageId === "target") {
      return pageComplete(questionSpec, answers, "sample", datasets) && pageComplete(questionSpec, answers, "material", datasets);
    }

    if (pageId === "example") {
      return routeComplete(questionSpec, answers) && needsExampleSelection(answers, datasets);
    }

    if (pageId === "expert") {
      if (!routeComplete(questionSpec, answers)) {
        return false;
      }
      if (needsExampleSelection(answers, datasets)) {
        return pageComplete(questionSpec, answers, "example", datasets);
      }
      return getEligibleExamples(answers, datasets).length === 1;
    }

    if (pageId === "results") {
      return Boolean(computeRecommendation(answers, datasets));
    }

    return false;
  }

  function getWizardPageSequence(questionSpec, answers, datasets) {
    const sequence = ["sample"];

    if (canReachPage("material", answers, datasets)) {
      sequence.push("material");
    }
    if (canReachPage("target", answers, datasets)) {
      sequence.push("target");
    }
    if (canReachPage("example", answers, datasets)) {
      sequence.push("example");
    }
    if (canReachPage("expert", answers, datasets)) {
      sequence.push("expert");
    }
    if (canReachPage("results", answers, datasets)) {
      sequence.push("results");
    }

    return sequence.filter((pageId, index, collection) => collection.indexOf(pageId) === index && pageById(questionSpec, pageId));
  }

  function firstReachablePage(questionSpec, answers, datasets) {
    if (!pageComplete(questionSpec, answers, "sample", datasets)) {
      return "sample";
    }
    if (!pageComplete(questionSpec, answers, "material", datasets)) {
      return "material";
    }
    if (!pageComplete(questionSpec, answers, "target", datasets)) {
      return "target";
    }
    if (needsExampleSelection(answers, datasets) && !pageComplete(questionSpec, answers, "example", datasets)) {
      return "example";
    }
    if (canReachPage("expert", answers, datasets) && !canReachPage("results", answers, datasets)) {
      return "expert";
    }
    return "results";
  }

  return {
    ROUTE_PAGE_IDS,
    WIZARD_ORDER,
    allQuestions,
    pageById,
    questionById,
    optionFor,
    isNeutral,
    matchesVisibleWhen,
    isQuestionVisible,
    visibleOptionsForQuestion,
    routeComplete,
    questionComplete,
    pageComplete,
    getEligibleExamples,
    needsExampleSelection,
    resolveSelectedExample,
    getWizardPageSequence,
    canReachPage,
    firstReachablePage,
    computeRecommendation
  };
});
