# OncoSentinel — Unified Hybrid Multi-Model Network
## Implementation Directive, Priorities, and Step-by-Step Development Plan

**Document purpose:** This file is the working implementation brief for evolving the existing OncoSentinel project into one unified platform with a **hybrid shared network** and **eight cancer-task models trained sequentially**.

**Chosen direction**
- **Architecture:** Hybrid shared network — share compatible components, use modality-specific branches where needed, and maintain task-specific output heads and checkpoints.
- **Training schedule:** Train all eight tasks one after another through a single training manager.
- **Platform goal:** One codebase, one model registry, one training engine, one evaluation framework, one inference router, and one dashboard.
- **Safety boundary:** Research and decision-support prototype only. Do not present predictions as autonomous diagnosis or treatment advice.

---

## 1. Executive Decision

OncoSentinel should not become eight separately engineered applications. Build a common platform that can configure, train, evaluate, register, and serve eight task-specific models through a reusable pipeline.

The intended design is:

1. A central registry describes each task, its modality, dataset, labels, preprocessing, architecture, and training settings.
2. A dataset adapter loads the correct dataset and produces a consistent sample format.
3. A modality-specific encoder processes the input.
4. Compatible encoders may share selected parameters; incompatible modalities use separate branches.
5. A task-specific head produces the output for that task.
6. One generic trainer runs the configured task, evaluates it, and saves its checkpoint.
7. A sequential training manager proceeds to the next eligible task.
8. A single inference router selects only a compatible, successfully trained, validated model.
9. A unified dashboard displays the real status and measured metrics of each task independently.

**Important distinction:** “One unified network” means one coordinated system. It does not require one identical set of neural-network weights for every modality. Forcing ultrasound, CT, MRI, histology, blood microscopy, and cytology through one unchanged backbone would be an untested assumption and could reduce performance.

---

## 2. What the Existing Project Review Established

The following points were observed in the reviewed `RAG Major Project` archive and its documentation:

- The project already has a broad software structure for the gateway/API, ingestion, ML orchestration, model registry, checkpoint handling, RAG, XAI, uncertainty, fairness, longitudinal analysis, outcomes, audit, and frontend.
- `configs/taxonomy.yaml` describes eight categories and identifies Breast and Kidney as Phase 1, with the other six staged for Phase 2.
- The codebase compiled with Python's `compileall` during the review.
- The test suite did **not** complete: test collection stopped because `structlog` was missing in the environment. This is not evidence that the full test suite passes.
- The reviewed archive did not contain the datasets or genuine trained model checkpoints required to demonstrate completed model training.
- No complete training loop was found in the reviewed Python source.
- The checkpoint helper had default/example validation values. Those values must not be represented as measured experimental results.
- The RAG implementation appeared to contain seeded evidence and lexical retrieval logic; a real, evaluated embedding index was not established by the archive review.
- The main archive uses an eight-category taxonomy, while a separate scaffold archive proposes a different four-head launch scope. This plan follows the requested **eight-category taxonomy in the main project**. Do not silently merge or replace the two scopes.

These are review findings, not claims that no future work has been done outside the reviewed archive. Re-run the checks against the current working copy before changing code.

---

## 3. The Eight-Task Scope

Use the main project's `configs/taxonomy.yaml` as the starting point. Verify every dataset, license, label definition, and task before training.

| Slot | Task/category | Input family in current taxonomy | Initial implementation rule |
|---|---|---|---|
| 01 | Breast | Ultrasound and/or histology | Decide whether these are one or two tasks. Do not combine incompatible modalities without an explicit design and evaluation plan. |
| 02 | Kidney | CT | Confirm whether the chosen dataset supports classification, segmentation, or both. |
| 03 | ALL / leukemia | Blood microscopy | Verify image format, patient identifiers, class definitions, and dataset license. |
| 04 | Oral cancer | Oral images | Specify the exact target label and intended image type. |
| 05 | Lung and colon | Histology | Define whether this is one multi-class task or separate tasks and document label mapping. |
| 06 | Lymphoma | Histology | Verify dataset provenance, patient-level grouping, and class balance. |
| 07 | Brain tumor | MRI | Define classes, MRI sequence assumptions, and patient-level splitting. |
| 08 | Cervical | Cytology | Define the target labels and determine whether images or slides/patient samples are the units of analysis. |

### Dataset decisions that must be resolved before training

**Breast / BUSI:** The commonly used BUSI dataset includes a normal class as well as benign and malignant classes. Decide explicitly between a binary task (with a documented rule for excluding or handling normal samples) and a three-class task. Do not silently map labels.

**Kidney / KiTS23:** KiTS23 is principally associated with segmentation challenges and should not automatically be treated as a four-class normal/tumor/cyst/stone classification dataset. Verify the actual labels and task definition. If the selected data do not support the planned task, change the task definition or choose a compatible dataset before writing the loader.

For every dataset, record:
- Official source and version.
- License and permitted use.
- Download instructions (do not commit private credentials or large datasets to Git).
- Class names and exact mapping.
- Patient/study/slide grouping identifiers, where available.
- Image dimensions, channels, format, and preprocessing.
- Exclusion criteria and missing/corrupt sample handling.
- Train/validation/test split manifest.
- Dataset checksum or version identifier.
- Whether external validation is available.

Do not start all eight training runs until at least one task has passed the complete data-to-checkpoint-to-evaluation workflow.

---

## 4. Target Architecture

```text
                         ONCOSENTINEL
                              |
                      Task / Input Router
                              |
                  Registry + Compatibility Check
                              |
               Dataset Adapter / Input Normalizer
                              |
                     Modality Dispatcher
               _____________|______________
              |             |              |
         Ultrasound       CT / MRI      Microscopy /
          encoder         encoder       Histology /
              |             |           Cytology encoder
              |             |              |
              +-------------+--------------+
                            |
              Shared components where justified
             (e.g. compatible pretraining/embeddings)
                            |
                 Task-specific output head
                            |
              Training / Evaluation / Checkpoint
                            |
                Model Registry + Model Card
                            |
             Validated Inference + Explanations
                            |
               Dashboard, Audit, and Monitoring
```

This diagram is a conceptual target, not a statement that the existing project already contains these connected components.

### Architecture rules

1. **Share the framework first.** Reuse configuration parsing, training loops, metric calculation, checkpoint format, logging, and evaluation.
2. **Share parameters only when justified.** Modality compatibility and empirical validation determine whether an encoder or representation can be shared.
3. **Use explicit modality branches.** Image dimensions, intensity distributions, stain patterns, MRI sequences, and label semantics differ.
4. **Keep task heads independent.** Each task has its own output dimension, class mapping, loss configuration, metrics, threshold policy, and checkpoint.
5. **Avoid accidental cross-task label mixing.** Class index `1` in one dataset must not acquire another task's meaning.
6. **Do not treat model output as calibrated confidence by default.** Calibration must be measured on suitable held-out data.
7. **Use a compatibility gate.** If the uploaded input modality or task cannot be identified confidently, request clarification or abstain instead of selecting an arbitrary model.

### First implementation strategy

Start with a **shared training engine and modality-specific encoders/task heads**. Initially train and evaluate each task independently through that engine. Only introduce joint multi-task weight sharing after the independent baselines are reproducible. This gives a reliable baseline for determining whether shared training helps or harms each task.

---

## 5. Repository Work: What to Inspect and Change

Preserve existing project modules where they are usable. Do not rewrite the entire repository before running the current tests and understanding module contracts.

### Existing areas to audit

- `configs/taxonomy.yaml` — source of task definitions.
- `services/ml/registry.py` — model registration and lookup.
- `services/ml/orchestrator.py` — inference/model orchestration.
- `services/ml/checkpoints.py` — checkpoint saving/loading.
- `services/ml/validation.py` — validation rules.
- `services/ingestion/` — file validation and modality-aware ingestion.
- `services/router/` — input/task routing.
- `services/gateway/` — API endpoints.
- `services/xai/` — explanation methods.
- `services/uncertainty/` — uncertainty estimation.
- `tests/` — current regression tests.

Before implementation, document each module's public functions, expected inputs/outputs, and existing tests. Avoid replacing a module based only on its filename.

### Proposed additions (adapt names to current conventions)

```text
configs/
  taxonomy.yaml
  model_registry.yaml             # or extend the existing taxonomy/registry cleanly
  training/
    breast.yaml
    kidney.yaml
    leukemia.yaml
    oral_cancer.yaml
    lung_colon.yaml
    lymphoma.yaml
    brain_tumor.yaml
    cervical.yaml

training/
  __init__.py
  dataset_adapters.py
  transforms.py
  split_manifest.py
  model_factory.py
  shared_components.py
  train_one.py
  train_all.py
  evaluate.py
  checkpoint_io.py
  run_state.py
  tests/

artifacts/
  manifests/                      # dataset and split manifests; no raw data by default
  checkpoints/
    breast/
    kidney/
    leukemia/
    oral_cancer/
    lung_colon/
    lymphoma/
    brain_tumor/
    cervical/
  metrics/
  model_cards/
  logs/
```

This is a proposed structure. Integrate with existing directories instead of creating duplicate registries, duplicate checkpoint managers, or competing orchestrators. Store large datasets and generated checkpoints outside source control unless the repository's data policy explicitly permits them.

---

## 6. The Configuration Contract

Each task must be represented declaratively. Example only; replace dataset paths, labels, and model choices after inspecting the real data.

```yaml
task_id: breast_ultrasound
display_name: Breast ultrasound classification
enabled: false

data:
  dataset_id: BUSI
  root: ${ONCOSENTINEL_DATA_ROOT}/BUSI
  input_type: image
  modality: ultrasound
  target_column: label
  class_names:
    - normal
    - benign
    - malignant
  grouping_column: patient_id
  split_manifest: artifacts/manifests/breast_ultrasound.json

model:
  family: image_classifier
  encoder: resnet18
  pretrained: true
  output_head: task_specific

training:
  seed: 42
  batch_size: 16
  epochs: 20
  optimizer: AdamW
  learning_rate: 0.0001
  early_stopping_patience: 5

evaluation:
  primary_metric: macro_f1
  metrics:
    - accuracy
    - macro_f1
    - sensitivity
    - specificity
    - roc_auc
    - brier_score

checkpoint:
  directory: artifacts/checkpoints/breast_ultrasound
  save_optimizer_state: true
```

Configuration requirements:

- The actual class mapping must match the verified dataset.
- Do not assume `patient_id` exists; if it does not, determine a valid grouping strategy and document the limitation.
- Do not use the same generic metric implementation blindly for classification, segmentation, or multi-label tasks.
- Use a stable task ID. Display names may change without breaking stored artifacts.
- `enabled: false` is the safe default until data, labels, and configuration have been verified.
- Store configuration snapshots alongside every training run.
- Validate the configuration before starting any expensive training.

---

## 7. Sequential Training Manager

The desired operator command is conceptually:

```powershell
python -m training.train_all --registry configs/model_registry.yaml
```

This command is a **target interface**, not a claim that the current repository already implements it.

### Required behavior

1. Load and validate the registry.
2. Select enabled tasks in a deterministic order.
3. Check dataset paths, license/approval metadata, class mapping, and split manifests.
4. Skip a task only when a compatible checkpoint and matching run metadata are present and verified.
5. Run data-integrity checks.
6. Initialize the task's model and optimizer.
7. Train for the configured number of epochs with early stopping based on validation data.
8. Evaluate on validation data for model selection.
9. Evaluate the final locked model once on the test split.
10. Save checkpoint, optimizer state (for resume), metrics, logs, configuration, and model card.
11. Mark the task as complete only if all required checks pass.
12. Continue to the next task according to the failure policy.
13. Write a machine-readable summary of the full queue.

### Run states

Use explicit states, for example:

`NOT_CONFIGURED → READY → TRAINING → TRAINED → EVALUATED → APPROVED_FOR_RESEARCH_DEMO`

Other states:

- `BLOCKED_DATA`
- `FAILED_TRAINING`
- `FAILED_EVALUATION`
- `CHECKPOINT_INVALID`
- `NEEDS_REVIEW`

A trained checkpoint is not automatically approved for a clinical workflow. `APPROVED_FOR_RESEARCH_DEMO` should require documented evaluation and a reviewer-defined checklist.

### Resume and retry rules

- Store a unique `run_id` for each attempt.
- Save epoch-level state at a configurable frequency.
- On resume, verify that task ID, model definition, dataset version, class mapping, and configuration match.
- Never reuse a checkpoint silently after the dataset or label mapping changes.
- A failure in one task should be logged and isolated; the manager may continue to the next task if configured to do so.
- The final summary must show every task, including blocked and failed tasks.

### Queue summary example

```text
01 breast_ultrasound  EVALUATED
02 kidney_ct          BLOCKED_DATA
03 leukemia_microscopy NOT_CONFIGURED
...
08 cervical_cytology  NOT_CONFIGURED
```

Do not mark a task as evaluated just because a checkpoint file exists.

---

## 8. Training and Data-Leakage Rules

These rules are mandatory for all eight tasks.

### Data splits

- Prefer patient-level, study-level, or slide-level splitting when multiple images can come from the same patient/study/slide.
- Keep the test set locked until final evaluation.
- Use training data to fit weights; use validation data for early stopping, model selection, and threshold selection.
- Never tune repeatedly on the test set.
- Document duplicate and near-duplicate checks where feasible.
- Fit normalization statistics and data-driven preprocessing on the training set only.
- Avoid splitting tiles or crops from the same original slide across train and test.
- Record class counts for each split and investigate severe imbalance.

### Augmentation

- Use only transformations appropriate to the modality and target. Do not assume that every rotation, flip, crop, or intensity transformation preserves clinically meaningful labels.
- Keep validation and test transformations deterministic.
- Save the exact transform configuration with each run.

### Optimization

Use the values in the task configuration as starting hypotheses, not universal best settings. Tune using validation data and available compute. Do not assume that the same batch size, learning rate, image size, loss, or epoch count will suit all tasks.

### Required outputs for each run

- `run_config.yaml`
- Dataset/version and split manifest references
- Training and validation curves
- Per-class support and metrics
- Confusion matrix where applicable
- Classification report or task-appropriate equivalent
- ROC-AUC only when the target format and class support make it valid
- Calibration metrics, such as Brier score or expected calibration error, where applicable
- Checkpoint and cryptographic hash
- Software/hardware environment and random seed
- Limitations and failure examples
- Model card with intended use and prohibited uses

For segmentation tasks, report suitable segmentation measures such as Dice and IoU instead of forcing classification-only metrics onto them.

---

## 9. Hybrid Sharing Strategy: How to Prove It Helps

Do not begin by jointly training all eight tasks and assume that shared learning is better.

### Stage A — Reproducible task baselines

Train one task at a time with the common engine. For the initial Breast task, verify the exact dataset and label scheme first. A compact pretrained image encoder may be a reasonable prototype baseline, subject to licensing and hardware constraints.

### Stage B — Group compatible modalities

Create candidate groups based on data properties and evidence, not cancer names alone. Histology tasks may be candidates for shared image representations; ultrasound, CT, MRI, microscopy, and cytology should be assessed separately. Some modalities may still share lower-level components after compatible preprocessing, but this must be tested.

### Stage C — Compare sharing experiments

For each proposed shared group, compare:

1. Independently trained baseline.
2. Shared encoder with task-specific heads.
3. Shared pretraining followed by task-specific fine-tuning.

Keep data splits, evaluation protocol, and reporting consistent. Report per-task results, not only a single aggregate score. Track whether sharing harms any task, class, or subgroup. If negative transfer occurs, reduce sharing or separate the relevant branch.

### Stage D — Expand carefully

Only promote shared components when results are reproducible and each affected task remains acceptable against its predeclared evaluation criteria. Eight tasks can use the same trainer even if some use different encoder families.

---

## 10. Inference Routing and Input Compatibility

The runtime system must not pick a model merely because an uploaded file is an image.

For each incoming item:

1. Validate file type, file size, integrity, and allowed format.
2. Determine or request the modality and intended task.
3. Check that a compatible task is enabled.
4. Confirm that a valid checkpoint is registered for that exact task and version.
5. Apply that task's preprocessing.
6. Run inference and validate output shape/range.
7. Return the task-specific result, limitations, and appropriate explanation.
8. Record an audit event without unnecessarily exposing patient information.
9. Abstain or request clarification when modality/task compatibility is uncertain or the model is unavailable.

Do not automatically diagnose all eight cancers from one image. The initial product should support one explicitly selected and compatible task per inference request unless a separately validated multi-task workflow is implemented.

---

## 11. Critical Checkpoint and Metric Corrections

The reviewed checkpoint helper used default/example validation metrics. Before building the training manager:

- Remove default numeric validation scores from checkpoint-saving APIs.
- Represent missing metrics as `null`/unmeasured, not as example numbers.
- Record the metric's dataset split, task, timestamp, and evaluation run.
- Never create a “trained” checkpoint from randomly initialized weights.
- Require a matching training manifest and actual weights before a model is registered as trained.
- Verify checkpoint loading with a test that checks architecture, output shape, and stored metadata.
- Distinguish model initialization, training completion, validation, and test evaluation.
- Do not allow example/demo outputs to be confused with model predictions.

A placeholder checkpoint may be useful for a unit test, but it must be explicitly marked as synthetic and prohibited from production inference.

---

## 12. RAG, Explainability, Uncertainty, Fairness, and Outcomes

These are complementary workstreams, not substitutes for a trained and evaluated image model.

### RAG

- First curate an approved source corpus with provenance and version metadata.
- Build PDF/text extraction that preserves source title, version, page, section, and publication details.
- Chunk and index content using an embedding model; persist the index.
- Consider hybrid lexical+dense retrieval and reranking.
- Test answerable and unanswerable questions.
- Measure retrieval recall/relevance, citation correctness, answer faithfulness, and abstention.
- Keep RAG guidance separate from the image classifier's learned output. RAG retrieval must not manufacture evidence for a model prediction.

### Explainability

- Add explanation methods suitable for the selected architecture and modality.
- Validate explanation stability and, where feasible, localization/fidelity.
- Do not treat a heatmap as proof that a prediction is correct.
- Display limitations and ensure explanations correspond to the exact checkpoint used.

### Uncertainty and abstention

- Establish a simple, documented baseline first.
- Evaluate calibration on held-out data.
- Define an abstention policy based on validation evidence and the intended research workflow.
- Do not label raw softmax values as calibrated probabilities.

### Fairness

- Identify relevant demographic and acquisition strata where data legitimately support analysis.
- Report sample sizes and uncertainty for subgroup metrics.
- Avoid strong fairness claims for tiny or missing subgroups.
- Respect privacy and data-use permissions.

### Longitudinal analysis and outcomes

- Define the temporal unit, permitted data, leakage controls, and intended outcome before implementation.
- Keep longitudinal and outcome claims disabled until valid temporal data and evaluation methods exist.

---

## 13. Testing and Release Gates

The existing test suite could not be fully collected during the earlier review because `structlog` was missing. Re-establish a reproducible environment before interpreting test results.

### Gate 1 — Environment and baseline

- Use a supported Python version consistent with the project's dependency pins.
- Create a clean virtual environment.
- Install the declared dependencies.
- Run compilation and all tests.
- Fix dependency/build issues and record the results.
- Never claim all tests pass unless the full test command completes successfully.

### Gate 2 — One-task vertical slice

- One verified dataset.
- One deterministic split manifest.
- One real training run.
- One saved checkpoint.
- One fresh-process checkpoint reload.
- One final test evaluation.
- One inference request through the project's real orchestration/API path.
- One audit/log record.
- Tests for malformed input, missing checkpoint, label mismatch, and invalid configuration.

### Gate 3 — Training manager

- Unit tests for configuration validation and task ordering.
- Integration test with a tiny synthetic dataset.
- Resume/retry and failure isolation tests.
- Checkpoint metadata compatibility tests.
- A queue summary that correctly reports incomplete tasks.

### Gate 4 — Eight task configurations

- Each task's data source, license, labels, modality, and loader are verified.
- Each task has a working configuration and split manifest.
- Tasks without validated data remain blocked rather than being trained on substitute or invented data.
- The full queue can run sequentially and produce an auditable summary.

### Gate 5 — Research demo

- Per-task evaluation reports are available.
- No placeholder metrics are displayed as experimental results.
- Input routing and model-version tracking work.
- RAG citations and abstention behavior are tested separately.
- Known limitations and non-clinical status are visible.

---

## 14. Recommended Execution Order

Do the work in this order to minimize rework.

### Phase 0 — Freeze and inspect the baseline

1. Make a version-controlled branch or backup.
2. Inspect the current working tree and dependencies.
3. Run compilation and tests in a clean environment.
4. Document current module contracts and existing functionality.
5. Fix the checkpoint-metric defaults before using the checkpoint manager for real experiments.
6. Decide which taxonomy file is authoritative and keep the eight-category scope consistent.

**Exit condition:** The repository's current behavior and blockers are documented, and test results are reproducible.

### Phase 1 — Build one complete task

1. Choose the first task based on accessible, licensed, well-documented data; Breast ultrasound is a possible starting candidate, not an automatic decision.
2. Verify the actual classes and dataset format.
3. Implement the dataset adapter and leakage-resistant split.
4. Train a baseline using the generic training engine.
5. Save real weights and run metadata.
6. Reload the checkpoint in a new process.
7. Evaluate and generate the report.
8. Integrate the result into the inference route and dashboard.

**Exit condition:** One task can be trained, evaluated, reloaded, and served end to end with real data and traceable results.

### Phase 2 — Generalize the engine

1. Move task-specific values into configuration.
2. Add the model factory and task-specific output heads.
3. Implement the sequential queue, run states, resume, retry, and reporting.
4. Add synthetic integration tests.
5. Verify that each task's class mapping and checkpoint remain isolated.

**Exit condition:** A second compatible or different-modality task can be added primarily through a verified adapter/configuration and necessary model implementation, not by duplicating the entire pipeline.

### Phase 3 — Configure and train all eight tasks

1. Verify each dataset and its permissions.
2. Add and test each task configuration.
3. Run tasks sequentially in the agreed order.
4. Keep blocked tasks in the queue report.
5. Compare performance against task-specific evaluation criteria.
6. Save per-task reports and model cards.

**Exit condition:** Every enabled task has a genuine, reproducible training/evaluation record; tasks without data remain explicitly incomplete.

### Phase 4 — Introduce and validate sharing

1. Group compatible modalities.
2. Establish independent baselines.
3. Run controlled shared-encoder experiments.
4. Compare per-task metrics and negative transfer.
5. Keep or revert shared components based on evidence.
6. Document the final hybrid design.

**Exit condition:** Parameter sharing is supported by measured results, not merely architectural preference.

### Phase 5 — Product hardening

1. Validate routing, audit, security, and data handling.
2. Finish RAG retrieval and citation evaluation.
3. Validate XAI and uncertainty.
4. Conduct subgroup/fairness analysis where data permit.
5. Verify deployment and monitoring with actual health checks.
6. Document research limitations and the non-clinical intended use.

**Exit condition:** The prototype has reproducible test evidence, transparent limitations, and a traceable release package.

---

## 15. Immediate Checklist

Complete these items before starting a full eight-task training run.

- [ ] Confirm the main eight-category taxonomy is the authoritative scope.
- [ ] Inspect current branch, dependencies, and test status.
- [ ] Remove misleading default checkpoint metrics.
- [ ] Confirm the first dataset's license, labels, and actual files.
- [ ] Define patient/study/slide-level split rules.
- [ ] Implement one reusable dataset interface.
- [ ] Implement one reusable training loop.
- [ ] Implement a model factory and task-specific heads.
- [ ] Implement checkpoint metadata and safe reload.
- [ ] Implement evaluation with task-appropriate metrics.
- [ ] Demonstrate one end-to-end task.
- [ ] Add sequential queue, resume/retry, and status reporting.
- [ ] Add the remaining six task configurations only after their data/task definitions are verified.
- [ ] Run all enabled tasks sequentially and report blocked tasks honestly.
- [ ] Test shared encoders only after independent baselines exist.

---

## 16. Definition of Done

OncoSentinel's unified hybrid training system is ready for a research prototype when:

- All eight tasks are represented in one authoritative registry.
- A single command can process enabled tasks sequentially.
- The same reusable engine handles data validation, training, evaluation, checkpointing, and reporting.
- Modality-specific branches and task-specific heads are selected explicitly.
- Failed tasks do not corrupt successful checkpoints or prevent useful queue reporting.
- Resume behavior verifies configuration and dataset compatibility.
- Every displayed metric is linked to a real evaluation run and split.
- Every active inference model has a verified checkpoint and a known task/class mapping.
- Inputs that do not match a supported task are rejected or routed to clarification.
- The project can reproduce the first end-to-end result from documented steps.
- Any shared weights have been justified by controlled experiments.
- The system is clearly presented as a research/decision-support prototype and not as an independently validated clinical diagnostic product.

**Final instruction:** Build the reusable training and evaluation infrastructure first, prove it on one verified task, and then expand sequentially to all eight. Do not spend time hand-building eight duplicate networks, but do not pretend that a shared pipeline eliminates the need for separate datasets, task definitions, checkpoints, and per-task validation.
