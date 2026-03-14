(function initSelectorEngine(globalScope, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
    return;
  }

  globalScope.SelectorEngine = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function createSelectorEngine() {
  const WIZARD_ORDER = [
    "sample",
    "material",
    "target",
    "example",
    "setup",
    "kit",
    "flowcell",
    "basecalling",
    "analysis",
    "conditions",
    "results"
  ];

  const BARCODED_LIBRARY_MODES = new Set(["rbk114_24", "nbd114_24", "barcoded_metagenome"]);
  const AMPLICON_LIBRARY_MODES = new Set(["amplicon_workflow", "rapid_pcr_amplicon"]);
  const ROUTE_PAGE_IDS = new Set(["sample", "material", "target", "example"]);

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

  function uniqueLinks(links) {
    const seen = new Set();
    return (links || []).filter((link) => {
      if (!link?.url || seen.has(link.url)) {
        return false;
      }
      seen.add(link.url);
      return true;
    });
  }

  function findById(items, id) {
    return (items || []).find((item) => item.id === id) || null;
  }

  function preferredOrderIndex(id, orderedIds) {
    const index = (orderedIds || []).indexOf(id);
    return index === -1 ? Number.MAX_SAFE_INTEGER : index;
  }

  function matchesWhen(when, answers) {
    if (!when) {
      return true;
    }

    return Object.entries(when).every(([questionId, acceptedValues]) => {
      if (!Array.isArray(acceptedValues) || acceptedValues.length === 0) {
        return false;
      }
      return acceptedValues.includes(answers[questionId]);
    });
  }

  function isQuestionVisible(questionSpec, question, answers) {
    return matchesWhen(question?.visible_when, answers);
  }

  function visibleOptionsForQuestion(questionSpec, question, answers) {
    return (question?.options || []).filter((option) => matchesWhen(option.visible_when, answers));
  }

  function isNeutralAnswer(questionSpec, questionId, value) {
    const question = typeof questionId === "string" ? questionById(questionSpec, questionId) : questionId;
    return Boolean(optionFor(question, value)?.neutral);
  }

  function hasAnswer(questionSpec, questionId, answers) {
    const question = questionById(questionSpec, questionId);
    if (!question) {
      return false;
    }

    if (!isQuestionVisible(questionSpec, question, answers)) {
      return true;
    }

    const value = answers[questionId];
    if (!value) {
      return false;
    }

    if (question.dynamic_options_from === "examples") {
      return true;
    }

    return visibleOptionsForQuestion(questionSpec, question, answers).some((option) => option.value === value);
  }

  function hasConcreteRouteAnswer(questionSpec, questionId, answers) {
    if (!hasAnswer(questionSpec, questionId, answers)) {
      return false;
    }

    return !isNeutralAnswer(questionSpec, questionId, answers[questionId]);
  }

  function routeBaseComplete(questionSpec, answers) {
    return ["sample_context", "material_class", "target_goal"].every((questionId) =>
      hasConcreteRouteAnswer(questionSpec, questionId, answers)
    );
  }

  function getEligibleExamples(answers, datasets) {
    if (!routeBaseComplete(datasets.questionSpec, answers)) {
      return [];
    }

    return (datasets.examples || []).filter((example) =>
      example.sample_contexts.includes(answers.sample_context) &&
      example.material_classes.includes(answers.material_class) &&
      example.target_goals.includes(answers.target_goal)
    );
  }

  function needsExampleSelection(answers, datasets) {
    const examples = getEligibleExamples(answers, datasets);
    if (examples.length === 0) {
      return false;
    }

    return examples.length !== 1 || examples[0].status_class !== "exact";
  }

  function resolveSelectedExample(answers, datasets) {
    const examples = getEligibleExamples(answers, datasets);
    if (examples.length === 0) {
      return null;
    }

    if (!needsExampleSelection(answers, datasets)) {
      return examples[0];
    }

    return examples.find((example) => example.id === answers.example_context) || null;
  }

  function routeComplete(questionSpec, answers, datasets) {
    if (!routeBaseComplete(questionSpec, answers)) {
      return false;
    }

    if (getEligibleExamples(answers, datasets).length === 0) {
      return false;
    }

    if (!needsExampleSelection(answers, datasets)) {
      return true;
    }

    return hasConcreteRouteAnswer(questionSpec, "example_context", answers);
  }

  function pageQuestions(questionSpec, pageId, answers) {
    const page = pageById(questionSpec, pageId);
    return (page?.questions || []).filter((question) => isQuestionVisible(questionSpec, question, answers));
  }

  function pageComplete(questionSpec, answers, pageId, datasets) {
    const page = pageById(questionSpec, pageId);
    if (!page) {
      return false;
    }

    if (pageId === "results") {
      return Boolean(computeRecommendation(answers, datasets));
    }

    if (page.page_type === "info" || pageId === "setup") {
      return routeComplete(questionSpec, answers, datasets);
    }

    if (page.page_type === "conditions") {
      return routeComplete(questionSpec, answers, datasets);
    }

    const questions = pageQuestions(questionSpec, pageId, answers);
    if (questions.length === 0) {
      return true;
    }

    return questions.every((question) => {
      const value = answers[question.id];
      if (!value) {
        return false;
      }

      let valid = false;
      if (question.dynamic_options_from === "examples") {
        valid = getEligibleExamples(answers, datasets).some((example) => example.id === value);
      } else {
        valid = visibleOptionsForQuestion(questionSpec, question, answers).some((option) => option.value === value);
      }

      if (!valid) {
        return false;
      }

      if (ROUTE_PAGE_IDS.has(pageId)) {
        return !isNeutralAnswer(questionSpec, question, value);
      }

      return true;
    });
  }

  function getWizardPageSequence(questionSpec, answers, datasets) {
    const sequence = ["sample", "material", "target"];

    if (!routeBaseComplete(questionSpec, answers)) {
      return sequence;
    }

    if (needsExampleSelection(answers, datasets)) {
      sequence.push("example");
    }

    if (!routeComplete(questionSpec, answers, datasets)) {
      return sequence;
    }

    sequence.push("setup", "kit", "flowcell", "basecalling", "analysis", "conditions", "results");
    return sequence;
  }

  function canReachPage(pageId, answers, datasets) {
    const sequence = getWizardPageSequence(datasets.questionSpec, answers, datasets);
    const index = sequence.indexOf(pageId);
    if (index === -1) {
      return false;
    }

    return sequence.slice(0, index).every((priorPageId) =>
      pageComplete(datasets.questionSpec, answers, priorPageId, datasets)
    );
  }

  function firstReachablePage(questionSpec, answers, datasets) {
    const sequence = getWizardPageSequence(questionSpec, answers, datasets);
    for (const pageId of sequence) {
      if (canReachPage(pageId, answers, datasets) && !pageComplete(questionSpec, answers, pageId, datasets)) {
        return pageId;
      }
    }
    return sequence[sequence.length - 1] || "sample";
  }

  function resolveMatrixProfile(answers, datasets, example) {
    if (!example) {
      return null;
    }

    if (example.matrix_profile_id) {
      return findById(datasets.matrixProfiles, example.matrix_profile_id);
    }

    return null;
  }

  function findMatchingRouteDefault(answers, datasets) {
    return (datasets.nanoporeProfiles?.route_defaults || []).find((profile) =>
      profile.sample_contexts.includes(answers.sample_context) &&
      profile.material_classes.includes(answers.material_class) &&
      profile.target_goals.includes(answers.target_goal)
    ) || null;
  }

  function effectiveValue(answers, questionId, fallback) {
    const value = answers[questionId];
    if (!value || value === "unsure") {
      return fallback || null;
    }
    return value;
  }

  function resolveNanoporeProfile(answers, datasets, example) {
    const routeDefault = findMatchingRouteDefault(answers, datasets);
    const defaultAnalysis = example?.status_class === "unsupported_nearest"
      ? "hybrid_reference"
      : routeDefault?.defaults?.analysis_environment || "group_repo_backend";

    const effective = {
      library_mode: effectiveValue(answers, "library_mode", routeDefault?.defaults?.library_mode),
      flowcell_family: effectiveValue(answers, "flowcell_family", routeDefault?.defaults?.flowcell_family),
      basecalling_goal: effectiveValue(answers, "basecalling_goal", routeDefault?.defaults?.basecalling_goal),
      analysis_environment: effectiveValue(answers, "analysis_environment", defaultAnalysis)
    };

    return {
      defaults: routeDefault?.defaults || {},
      route_default_note: routeDefault?.result_note || "",
      effective,
      kit: findById(datasets.nanoporeProfiles?.kits, effective.library_mode),
      flowcell: findById(datasets.nanoporeProfiles?.flow_cells, effective.flowcell_family),
      basecalling: findById(datasets.nanoporeProfiles?.basecalling_profiles, effective.basecalling_goal)
    };
  }

  function resolveExternalFallbacks(answers, datasets, status, analysisEnvironment, matrixProfile) {
    const compatibility = status === "unsupported" ? "unsupported" : "exact";
    const preferredSource = analysisEnvironment === "cz_id"
      ? "cloud"
      : analysisEnvironment === "epi2me_labs"
        ? "ont_curated"
        : null;
    const explicitWorkflowOrder = matrixProfile?.fallback_workflow_ids || [];
    const matrixProfileId = matrixProfile?.id || null;

    return (datasets.externalWorkflows || [])
      .filter((workflow) =>
        workflow.route_compatibility.includes(compatibility) &&
        workflow.supported_material_classes.includes(answers.material_class) &&
        workflow.supported_target_goals.includes(answers.target_goal)
      )
      .sort((left, right) => {
        const explicitLeft = preferredOrderIndex(left.id, explicitWorkflowOrder);
        const explicitRight = preferredOrderIndex(right.id, explicitWorkflowOrder);
        const leftMatrixMatch = matrixProfileId && (left.preferred_matrix_profile_ids || []).includes(matrixProfileId) ? 1 : 0;
        const rightMatrixMatch = matrixProfileId && (right.preferred_matrix_profile_ids || []).includes(matrixProfileId) ? 1 : 0;
        const leftPreferred = preferredSource && left.source_type === preferredSource ? 1 : 0;
        const rightPreferred = preferredSource && right.source_type === preferredSource ? 1 : 0;

        return explicitLeft - explicitRight ||
          rightMatrixMatch - leftMatrixMatch ||
          rightPreferred - leftPreferred ||
          left.label.localeCompare(right.label);
      })
      .map((workflow) => ({
        ...workflow,
        emphasis: status === "unsupported" ? "fallback" : "alternative"
      }));
  }

  function findPipelineTrack(pipeline, trackId) {
    return pipeline?.track_notes?.find((track) => track.id === trackId) || null;
  }

  function resolveBackendFromExample(example, datasets) {
    const pipelineId = example.status_class === "exact" ? example.pipeline_id : example.nearest_pipeline_id;
    const trackId = example.status_class === "exact" ? example.track_id : example.nearest_track_id;
    const pipeline = findById(datasets.pipelines, pipelineId);
    const track = trackId ? findPipelineTrack(pipeline, trackId) : null;
    const playbook = (datasets.playbooks || []).find((entry) =>
      entry.pipeline_id === pipelineId && entry.track_id === (trackId || null)
    ) || (datasets.playbooks || []).find((entry) => entry.pipeline_id === pipelineId && entry.track_id === null) || null;

    return { pipeline, track, playbook };
  }

  function mergePreprocessing(backend) {
    return {
      ...(backend.pipeline?.default_preprocessing || {}),
      ...(backend.track?.preprocessing_override || {}),
      ...(backend.playbook?.preprocessing_defaults || {})
    };
  }

  function evaluateExpertRules(answers, datasets, example, nanoporeProfile) {
    const evaluationAnswers = { ...answers, ...nanoporeProfile.effective };

    return (datasets.expertRules || [])
      .filter((rule) => rule.applies_to_example_ids.includes(example.id) && matchesWhen(rule.when, evaluationAnswers))
      .sort((left, right) => (right.priority || 0) - (left.priority || 0));
  }

  function applySetupHeuristics(answers, datasets, example, nanoporeProfile, backend, matrixProfile) {
    const expertEffects = [];
    const warnings = [];
    const insertedActions = [];
    const setupNotes = [];
    const guideLinks = uniqueLinks([
      {
        label: "Nanopore guide",
        url: "nanopore-guide.html"
      },
      matrixProfile?.guide_section_id
        ? {
            label: `${matrixProfile.label} matrix notes`,
            url: `nanopore-guide.html#${matrixProfile.guide_section_id}`
          }
        : null
    ].filter(Boolean)).map((link) => ({
      title: link.label,
      url: link.url
    }));
    let preferredTool = null;

    if (nanoporeProfile.basecalling && nanoporeProfile.effective.basecalling_goal !== "already_basecalled") {
      expertEffects.push({
        title: `Basecalling with ${nanoporeProfile.basecalling.label}`,
        summary: nanoporeProfile.basecalling.summary,
        effect_type: "step_insert"
      });
      insertedActions.push({
        id: "setup-basecalling",
        title: `Basecall with ${nanoporeProfile.basecalling.label}`,
        summary: nanoporeProfile.basecalling.summary,
        entry_file: "docs/nanopore-guide.html#basecalling-tiers",
        doc_url: "nanopore-guide.html#basecalling-tiers"
      });
    } else if (nanoporeProfile.effective.basecalling_goal === "already_basecalled") {
      expertEffects.push({
        title: "Skip upstream basecalling",
        summary: "The selected setup starts from basecalled reads rather than raw signal.",
        effect_type: "step_skip"
      });
    }

    if (BARCODED_LIBRARY_MODES.has(nanoporeProfile.effective.library_mode)) {
      expertEffects.push({
        title: "Add demultiplexing and barcode trimming",
        summary: "The selected kit implies barcode-aware separation before the backend steps start.",
        effect_type: "step_insert"
      });
      insertedActions.push({
        id: "setup-demultiplexing",
        title: "Demultiplex and trim barcodes first",
        summary: "This setup expects per-barcode separation and barcode-aware trimming before downstream analysis.",
        entry_file: "docs/nanopore-guide.html#library-prep-kits",
        doc_url: "nanopore-guide.html#library-prep-kits"
      });
    }

    if (AMPLICON_LIBRARY_MODES.has(nanoporeProfile.effective.library_mode) && answers.barcoded_amplicon_pool === "yes") {
      expertEffects.push({
        title: "Keep amplicon pools barcode-aware",
        summary: "Pooled amplicon data still need barcode-aware separation and primer-aware cleanup.",
        effect_type: "step_insert"
      });
    }

    if (nanoporeProfile.flowcell?.id === "promethion_r10_4_1") {
      warnings.push({
        title: "PromethION depth framing",
        text: "This setup fits deeper metagenomics or larger cohorts and may exceed the throughput assumptions of the published example."
      });
    }

    if (nanoporeProfile.effective.library_mode === "direct_rna" && nanoporeProfile.effective.flowcell_family !== "rna_flow_cell") {
      warnings.push({
        title: "Direct RNA mismatch",
        text: "Direct RNA usually expects an RNA-specific flow cell family, so confirm the wet-lab setup before proceeding."
      });
    }

    if (nanoporeProfile.effective.analysis_environment === "epi2me_labs") {
      setupNotes.push("The result should foreground ONT-curated EPI2ME Labs workflows alongside the internal backend.");
    } else if (nanoporeProfile.effective.analysis_environment === "cz_id") {
      setupNotes.push("The result should foreground CZ ID as the main cloud analysis environment while still keeping the nearest internal example visible.");
    } else if (nanoporeProfile.effective.analysis_environment === "hybrid_reference") {
      setupNotes.push("The result should combine the nearest internal example with external workflow references.");
    } else {
      setupNotes.push("The result remains anchored in the internal published backend first.");
    }

    const matchingRules = evaluateExpertRules(answers, datasets, example, nanoporeProfile);
    for (const rule of matchingRules) {
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

      if (rule.tool_override?.to) {
        preferredTool = {
          from: rule.tool_override.from,
          to: rule.tool_override.to
        };
      }
    }

    if (preferredTool) {
      setupNotes.push(`Preferred assembler heuristic: ${preferredTool.to} instead of ${preferredTool.from}.`);
    }

    const entryActions = [...insertedActions, ...(backend.playbook?.entry_actions || [])];
    return {
      expertEffects,
      warnings,
      entryActions,
      setupNotes,
      preferredTool,
      guideLinks
    };
  }

  function buildStatus(example) {
    if (example.status_class === "unsupported_nearest") {
      const hasComposed = Array.isArray(example.recommended_steps) && example.recommended_steps.length > 0;
      return {
        value: "unsupported",
        label: hasComposed
          ? "Recommended approach (composed from published workflows)"
          : "Unsupported / nearest published example"
      };
    }

    if (example.track_id) {
      return {
        value: "track_exact",
        label: "Published example + branch"
      };
    }

    return {
      value: "exact",
      label: "Published example match"
    };
  }

  function labelForValue(questionSpec, questionId, value) {
    const question = questionById(questionSpec, questionId);
    return optionFor(question, value)?.label || value || "";
  }

  function buildMatrixNotes(matrixProfile) {
    if (!matrixProfile) {
      return null;
    }

    return {
      id: matrixProfile.id,
      label: matrixProfile.label,
      summary: matrixProfile.selector_summary,
      warnings: matrixProfile.selector_warnings || [],
      setup_biases: matrixProfile.setup_biases || {},
      what_this_changes: matrixProfile.what_this_changes,
      guide_section_id: matrixProfile.guide_section_id
    };
  }

  function computeRecommendation(answers, datasets) {
    if (!routeComplete(datasets.questionSpec, answers, datasets)) {
      return null;
    }

    const example = resolveSelectedExample(answers, datasets);
    if (!example) {
      return null;
    }

    const backend = resolveBackendFromExample(example, datasets);
    if (!backend.pipeline || !backend.playbook) {
      return null;
    }

    const status = buildStatus(example);
    const matrixProfile = resolveMatrixProfile(answers, datasets, example);
    const nanoporeProfile = resolveNanoporeProfile(answers, datasets, example);
    const setupEffects = applySetupHeuristics(answers, datasets, example, nanoporeProfile, backend, matrixProfile);
    const externalFallbacks = resolveExternalFallbacks(
      answers,
      datasets,
      status.value,
      nanoporeProfile.effective.analysis_environment,
      matrixProfile
    );
    const preprocessing = mergePreprocessing(backend);
    const docs = {
      primary: uniqueLinks([...(backend.pipeline.primary_docs || []), ...(backend.playbook.evidence_links || [])]),
      setup: uniqueLinks([...(backend.pipeline.setup_docs || [])]),
      evidence: uniqueLinks(backend.playbook.evidence_links || [])
    };

    const analysisEnvironmentLabel = labelForValue(
      datasets.questionSpec,
      "analysis_environment",
      nanoporeProfile.effective.analysis_environment
    );

    const kitLabel = nanoporeProfile.kit?.label || nanoporeProfile.effective.library_mode || "Route default";
    const flowcellLabel = nanoporeProfile.flowcell?.label || nanoporeProfile.effective.flowcell_family || "Route default";
    const basecallingLabel = nanoporeProfile.basecalling?.label || nanoporeProfile.effective.basecalling_goal || "Route default";

    const setupRecommendation = [kitLabel, flowcellLabel, basecallingLabel].filter(Boolean).join(" + ");
    const exampleReason = example.selection_help || example.route_summary;
    const fallbackReason = example.unsupported_reason
      ? `${example.unsupported_reason} The nearest internal example is still shown as the starting point.`
      : exampleReason;
    const explanation = status.value === "unsupported"
      ? fallbackReason
      : backend.track
        ? "This route matches a published backend and an internal documented branch."
        : "This route matches a published backend in the repository.";

    const routeSummary = [
      labelForValue(datasets.questionSpec, "sample_context", answers.sample_context),
      labelForValue(datasets.questionSpec, "material_class", answers.material_class),
      labelForValue(datasets.questionSpec, "target_goal", answers.target_goal)
    ].filter(Boolean).join(" -> ");

    return {
      route: {
        summary: example.route_summary || routeSummary,
        label: routeSummary
      },
      example,
      backend,
      composed_steps: example.recommended_steps || null,
      pipeline_diagram: example.pipeline_diagram || backend.playbook.pipeline_diagram || null,
      status: status.value,
      status_label: status.label,
      explanation,
      matrix_profile: matrixProfile,
      matrix_notes: buildMatrixNotes(matrixProfile),
      literature_links: uniqueLinks(matrixProfile?.citations || []),
      nanopore_profile: nanoporeProfile,
      setup_summary: {
        recommendation: setupRecommendation,
        result_note: nanoporeProfile.route_default_note,
        notes: setupEffects.setupNotes,
        analysis_environment_label: analysisEnvironmentLabel
      },
      external_fallbacks: externalFallbacks,
      analysis_environment: {
        id: nanoporeProfile.effective.analysis_environment,
        label: analysisEnvironmentLabel
      },
      guide_links: setupEffects.guideLinks,
      expert_effects: setupEffects.expertEffects,
      entry_actions: setupEffects.entryActions,
      curated_commands: backend.playbook.curated_commands || [],
      preprocessing,
      warnings: setupEffects.warnings,
      docs,
      preferred_tool_override: setupEffects.preferredTool,
      kit_consequences: nanoporeProfile.kit?.consequences
        ? {
            demultiplexing: nanoporeProfile.kit.consequences.demultiplexing,
            barcode_trimming: nanoporeProfile.kit.consequences.barcode_trimming,
            route_shape: nanoporeProfile.kit.consequences.route_implication,
            first_changes: nanoporeProfile.kit.summary
          }
        : null
    };
  }

  return {
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
  };
});
