# OncoSentinel — Master Project Roadmap, Architecture & Faculty Review Guide

**Document type:** Master implementation directive and project-status reference  
**Project:** OncoSentinel — Unified Hybrid Multi-Model Cancer Research and Decision-Support Prototype  
**Selected architecture:** Hybrid shared network  
**Selected training strategy:** Train all eight task configurations one after another through a unified training manager  
**Intended audience:** Project team, supervisor/faculty, evaluators, and future contributors  
**Status baseline:** Based on the previously reviewed `RAG Major Project` archive and related project documents; re-verify against the current working copy before formal submission.

> **Important scope boundary:** OncoSentinel is a research and decision-support prototype. It must not be represented as a clinically validated diagnostic product, nor as a substitute for professional medical judgement. Architecture, software scaffolding, or successful training alone does not establish clinical validity.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Vision and Working Principles](#2-project-vision-and-working-principles)
3. [What the Archive Review Established](#3-what-the-archive-review-established)
4. [Current Status and Completion Estimate](#4-current-status-and-completion-estimate)
5. [Selected Architecture: Hybrid Shared Network](#5-selected-architecture-hybrid-shared-network)
6. [The Eight-Task Model Portfolio](#6-the-eight-task-model-portfolio)
7. [Repository and Configuration Plan](#7-repository-and-configuration-plan)
8. [Unified Training Engine and Sequential Queue](#8-unified-training-engine-and-sequential-queue)
9. [Dataset Selection, Preparation, and Leakage Prevention](#9-dataset-selection-preparation-and-leakage-prevention)
10. [Model Evaluation, Checkpoints, and Experiment Records](#10-model-evaluation-checkpoints-and-experiment-records)
11. [Inference Routing and Safe Failure Behavior](#11-inference-routing-and-safe-failure-behavior)
12. [RAG, Explainability, Uncertainty, Fairness, Longitudinal Analysis, and Outcomes](#12-rag-explainability-uncertainty-fairness-longitudinal-analysis-and-outcomes)
13. [Testing, Environment, Deployment, and Security](#13-testing-environment-deployment-and-security)
14. [Phased Roadmap and Exit Criteria](#14-phased-roadmap-and-exit-criteria)
15. [Project Dashboard and Evidence-Based Tracking](#15-project-dashboard-and-evidence-based-tracking)
16. [Faculty Presentation and Demonstration Plan](#16-faculty-presentation-and-demonstration-plan)
17. [Risk Register](#17-risk-register)
18. [Immediate Prioritized Checklist](#18-immediate-prioritized-checklist)
19. [Definition of Done](#19-definition-of-done)
20. [Suggested Repository Commands](#20-suggested-repository-commands)
21. [Decision Log Template](#21-decision-log-template)
22. [Run Record and Model Card Templates](#22-run-record-and-model-card-templates)
23. [Final Recommendations](#23-final-recommendations)

---

## 1. Executive Summary

OncoSentinel should be developed as **one coordinated software platform**, not eight separate applications. The platform will have a shared model registry, data-loading interfaces, configuration system, training/evaluation engine, checkpoint lifecycle, inference router, audit trail, and dashboard.

The selected design is a **hybrid shared network**:

- Shared software infrastructure and reusable training/evaluation logic.
- Modality-aware branches and encoders where input characteristics differ.
- Task-specific output heads, class mappings, checkpoints, metrics, and model cards.
- Empirical testing before sharing learned weights between tasks.
- A sequential training queue that trains each enabled task one after another and records its actual state.
- One UI that shows all eight tasks independently, without implying that a configured task is already trained.

The most important development priority is **not to implement more features immediately**. It is to establish one complete, repeatable path from a verified dataset to a trained checkpoint, evaluation report, reloaded inference, and working application integration. After that vertical slice is reproducible, generalize the workflow and run the other tasks sequentially.

The previous archive review indicated a substantial architecture and service scaffold, but did **not** establish real trained models, a complete training loop, or a passing full test suite. This document therefore distinguishes among:
- **Observed:** found in the reviewed archive or described in the project documents.
- **Estimated:** a provisional engineering-readiness assessment.
- **Planned:** work recommended but not verified as implemented.
- **Experimentally demonstrated:** a claim that should only be used after a reproducible run and supporting evidence exist.

---

## 2. Project Vision and Working Principles

### 2.1 Vision

OncoSentinel is intended to be a modular, multi-task cancer-imaging research platform that accepts supported inputs, selects a compatible task, produces a task-specific result, and exposes useful supporting context such as model version, evaluation evidence, explanations, uncertainty information, and system limitations.

The platform is designed to support research and responsible decision support. It should not autonomously diagnose cancer or recommend treatment as if it were a clinically validated system.

### 2.2 Core principles

1. **One platform, not eight duplicated codebases.** Reuse the engineering pipeline wherever appropriate.
2. **Task-specific scientific handling.** Reuse infrastructure without pretending every modality, dataset, label scheme, and prediction objective is identical.
3. **Evidence before claims.** Never present planned work, placeholder values, or architecture diagrams as experimentally completed work.
4. **Reproducibility.** Each result must be tied to a specific dataset version, split, configuration, checkpoint, and evaluation run.
5. **Safe failure is a valid result.** Unsupported inputs, unknown tasks, invalid files, or missing checkpoints must be rejected or routed to clarification rather than generating a fabricated or arbitrary prediction.
6. **Expand incrementally.** Prove one full path; generalize; add validated configurations; then run the sequential queue.
7. **Use measured performance to make architecture decisions.** Sharing components is a hypothesis to test, not a performance guarantee.
8. **Keep clinical claims proportionate to evidence.** A research prototype, a trained model, and a clinically validated diagnostic system are different maturity levels.

---

## 3. What the Archive Review Established

The following points were observed in the previously reviewed `RAG Major Project` archive. Re-run the checks on the current working copy before treating these statements as current status.

### 3.1 Existing software foundation

The repository contains a broad project structure, including areas for:

- Gateway/API.
- Ingestion, storage, validation, and OCR-related logic.
- ML backbone, heads, registry, orchestration, checkpoint handling, and validation.
- RAG retriever, vector-store wrapper, verification, and LLM reasoning.
- Routing.
- Explainability.
- Uncertainty.
- Fairness.
- Longitudinal analysis.
- Outcomes.
- Audit.
- FHIR/interoperability.
- Federated learning.
- Frontend and monitoring configurations.
- A collection of test modules.
- Project requirements, architecture, PRD/SRS, research-gap analysis, and development history.

Relevant reviewed paths included `configs/taxonomy.yaml`, `services/ml/registry.py`, `services/ml/orchestrator.py`, `services/ml/checkpoints.py`, `services/ml/validation.py`, `services/rag/`, `services/ingestion/`, `services/router/`, `services/gateway/`, and `tests/`.

### 3.2 Checks that were performed

- Python compilation using `python -m compileall -q services tests` succeeded in the reviewed environment.
- The full test run did **not** complete. Pytest collection stopped because `structlog` was missing.
- The reviewed archive did not include the datasets or genuine trained model checkpoints required to prove completed model training.
- No complete training loop was found in the reviewed Python source.

**Interpretation:** successful compilation is a useful syntax check, not proof that the full application works. A failed test collection is not a pass or a failure result for every test; it means the suite outcome remains unknown until it runs successfully.

### 3.3 Important technical findings to address

#### A. Checkpoint metrics must not be misleading

The reviewed checkpoint helper had default/example validation metrics (including values around 0.94 accuracy/AUC-style fields and low ECE-like values in the helper defaults or baseline-creation path). Those values can make untrained or randomly initialized weights appear evaluated.

Required action:
- Remove numeric example defaults from functions that save or register genuine experiment results.
- Use `null`/unmeasured when a value has not been measured.
- Explicitly mark synthetic/test checkpoints as synthetic.
- Never register random initialization as a trained, evaluated, or approved checkpoint.
- Link every metric to a real evaluation run and split.

#### B. A complete training pipeline remains to be established

The reviewed source did not show a complete reproducible training loop. Model construction, registry, inference orchestration, and checkpoint utilities do not replace data splitting, training, validation-based selection, final testing, and run-record generation.

#### C. RAG should not be described as a validated embedding-retrieval system yet

The reviewed RAG implementation appeared to have seeded evidence and lexical/token-overlap retrieval. A persistent, production-like embedding index and a measured retrieval evaluation were not established by the archive review. Local LLM calls also had a deterministic fallback path.

Required action:
- Describe the current work precisely as seeded/lexical retrieval scaffolding until persistent embedding retrieval, citations, and evaluation have been demonstrated.
- Do not imply the deterministic fallback is a locally generated LLM answer.
- Evaluate source traceability, citation correctness, grounding, and abstention.

#### D. Scope conflict across project materials

The main `RAG Major Project` archive uses an eight-category taxonomy, with Breast and Kidney described as Phase 1 and the other categories staged for Phase 2. A separate scaffold archive proposed a different four-head launch scope.

For this roadmap, the selected baseline is the **eight-category taxonomy in the main project**. Keep that choice consistent across configurations, UI, reports, and faculty slides unless the project owner makes an explicit documented scope change. Do not silently merge the alternative four-head proposal into the eight-category project.

#### E. Dataset/task mismatches must be resolved before training

- The commonly used BUSI breast ultrasound dataset includes normal, benign, and malignant examples. The taxonomy's binary benign/malignant mapping must be reconciled with the actual dataset. Choose a documented binary or three-class task.
- KiTS23 is primarily associated with kidney tumor segmentation. Do not assume it automatically supports a four-class normal/tumor/cyst/stone classifier. Verify the intended task and the labels provided by the actual dataset or choose a compatible dataset.

#### F. Service configuration does not prove deployment

Having Docker Compose, database/cache/object-store/vector-store configuration, health-check settings, or frontend files is not the same as a verified running deployment. Runtime service health and an end-to-end request must be demonstrated.

---

## 4. Current Status and Completion Estimate

### 4.1 Provisional executive estimate

Based on the prior archive review, the project was assessed at roughly **40% engineering readiness**, with an indicative range of **30–50%**.

This number is a qualitative engineering estimate, **not** a calculated percentage, scientific performance result, model accuracy, or clinical-readiness score. It should be refreshed after a fresh audit. The dimensions below should not simply be averaged because documentation, training, testing, and deployment measure different kinds of progress.

### 4.2 Provisional workstream view

| Workstream | Earlier qualitative assessment | What the assessment means |
|---|---:|---|
| Architecture and documentation | ~85% | Strong planning/documentation foundation; implementation still needs evidence |
| Configuration and taxonomy | ~80% | Eight-category configuration exists; dataset labels and task definitions require verification |
| Ingestion | ~55% | Service scaffolding exists; real-input integration and edge-case tests remain |
| Routing | ~65% | Routing components exist; compatibility and end-to-end behaviour need tests |
| ML architecture/inference | ~50% | Model and checkpoint scaffolding exists; trained-weight path is not demonstrated |
| Real model training | 0–5% | No complete loop or genuine trained checkpoints were confirmed in the reviewed archive |
| RAG | ~25% | Seeded/lexical prototype logic; persistent retrieval and evidence evaluation pending |
| Local LLM reasoning | ~30% | Call/fallback scaffolding; grounded behaviour and failure cases need testing |
| XAI and uncertainty | ~45% | Modules/methods exist; fidelity, stability, calibration, and task-level evaluation pending |
| Database, audit, and security | ~45% | Structural pieces exist; integration, privacy, and access-path validation pending |
| Frontend | ~50% | UI scaffolding exists; working end-to-end application flow not established |
| Testing and reproducibility | ~25% | Tests exist, but the complete suite did not run in the earlier review |
| Deployment and monitoring | ~30% | Configurations exist; deployment and health checks are not verified |

### 4.3 Phase-level planning estimates

These approximate phase labels from the prior discussion should be treated as planning aids, not audit-grade measurements:

| Phase / area | Earlier estimate | Most important missing evidence |
|---|---:|---|
| Core architecture and scope | ~85% | Verified behaviour and implementation-to-documentation alignment |
| Data and model pipeline | ~40% | Verified data, full training loop, checkpoints, real task integration |
| Real training and evaluation | 0–5% | A reproducible run and final evaluation on held-out data |
| Research intelligence (RAG/XAI/uncertainty) | ~25–30% | Real pipeline validation, source/citation tests, explanation/calibration studies |
| Application and integration | ~30–35% | End-to-end route from real input through a verified checkpoint to displayed output |
| Productization/release readiness | ~10–15% | Reproducibility, environment, deployment, security, validation and release records |

**Dashboard rule:** display the date of the latest audit, the evidence used, and whether a figure is estimated or verified. Prefer evidence states over overly precise completion percentages.

### 4.4 Recommended project status vocabulary

Use a consistent status vocabulary across source control, the dashboard, reports, and slides:

- `PLANNED` — a design/task exists but implementation has not started.
- `DESIGNED` — the design and interfaces are documented.
- `SCAFFOLDED` — initial code/configuration exists.
- `IMPLEMENTED` — implementation exists and can be exercised.
- `TESTED` — the relevant automated/manual tests completed and evidence was recorded.
- `TRAINED` — a real training run completed from identified data.
- `EVALUATED` — the specified evaluation protocol completed on the documented split.
- `RESEARCH_DEMO_READY` — required prototype/research-demo checklist passed.
- `BLOCKED_DATA`, `BLOCKED_ENVIRONMENT`, `FAILED`, `NEEDS_REVIEW` — explicit non-success states.

Do not skip straight from `SCAFFOLDED` to `EVALUATED`.

---

## 5. Selected Architecture: Hybrid Shared Network

### 5.1 The decision

The selected design is:

- **Hybrid shared network**
- **All eight task configurations trained sequentially**
- **One shared codebase and common training infrastructure**
- **Modality-aware branches and task-specific heads/checkpoints**
- **Controlled experiments before deciding which learned components should be shared**

The term “one network” should be understood as one coordinated architecture/platform. It does not require every task to use the exact same neural weights. Ultrasound, CT, MRI, histology, blood microscopy, and cytology may need different preprocessing and encoders.

### 5.2 Conceptual architecture

```text
                              ONCOSENTINEL
                                   |
                         Input / Task Router
                                   |
                    Task Registry + Compatibility Check
                                   |
                     Dataset / Input Adapter Layer
                                   |
                          Modality Dispatcher
                 ________________|________________
                |                |                |
          Ultrasound           CT / MRI       Microscopy /
            branch             branch         Histology /
                                                  Cytology
                |                |                |
                +----------------+----------------+
                                 |
                  Shared components where justified
                (e.g., compatible pretraining/features)
                                 |
                      Task-specific output head
                                 |
                    Training / Evaluation Engine
                                 |
                  Checkpoint + Run Record + Model Card
                                 |
                     Validated Inference Orchestrator
                                 |
          Explanation / Uncertainty / Audit / Evidence Layer
                                 |
                   Unified OncoSentinel Dashboard
```

This is the **target architecture**, not a statement that all pieces are already connected or complete.

### 5.3 Why use a hybrid approach?

It avoids two extremes:

- **Eight duplicated applications:** wasteful to maintain and test.
- **One identical model for all image types:** scientifically unproven and may introduce negative transfer or incompatible input/label assumptions.

The engineering pipeline can be shared even if the neural-network weights are not. Sharing should be an experimental choice justified by evidence.

### 5.4 Define a task precisely

A task should be defined by **disease/category + modality + prediction objective + label mapping**, not by cancer name alone.

Examples:

| Task ID (example) | Input | Prediction objective |
|---|---|---|
| `breast_ultrasound` | Ultrasound image | Classification |
| `breast_histology` | Histology image | Classification |
| `kidney_ct` | CT image/volume | Classification or segmentation, explicitly selected |
| `brain_mri` | MRI image/volume | Task-specific classification or segmentation |
| `leukemia_microscopy` | Blood-cell microscopy | Classification |
| `cervical_cytology` | Cytology image/slide | Task-specific classification |

These IDs are examples. The final task registry must follow the actual selected dataset and label definitions. A taxonomy category may contain more than one task if it spans modalities or prediction objectives.

### 5.5 Recommended development strategy

1. Build one shared training/evaluation engine.
2. Start with task-specific encoder/head configurations and independent baselines.
3. Prove the full pipeline with a single verified task.
4. Add the sequential training manager.
5. Configure the remaining tasks after their data and labels are verified.
6. Group compatible modalities and compare independent models with shared-encoder experiments.
7. Retain sharing only when it is reproducible and does not cause unacceptable per-task degradation.

---

## 6. The Eight-Task Model Portfolio

The main project's `configs/taxonomy.yaml` defined these eight categories. Treat each row as a task slot to validate, not as a trained model.

| Slot | Category | Current taxonomy modality | Stage in main project | Required next decision |
|---|---|---|---|---|
| 01 | Breast cancer | Ultrasound and histology | Phase 1 | Decide whether ultrasound and histology are separate tasks; resolve BUSI's actual label scheme |
| 02 | Kidney | CT | Phase 1 | Confirm classification vs segmentation and select compatible labels/data |
| 03 | ALL / leukemia | Blood microscopy | Phase 2 | Verify dataset, labels, patient grouping, and use permissions |
| 04 | Oral cancer | Oral images | Phase 2 | Define actual image type, task, label mapping, and data source |
| 05 | Lung and colon | Histology | Phase 2 | Define separate or combined task structure and exact class semantics |
| 06 | Lymphoma | Histology | Phase 2 | Verify dataset provenance, label mapping, patient/slide-level splitting |
| 07 | Brain tumor | MRI | Phase 2 | Define MRI sequence assumptions, labels, and prediction objective |
| 08 | Cervical cancer | Cytology | Phase 2 | Define labels and whether the unit is an image, slide, or patient sample |

### 6.1 Dataset acceptance checklist

Before a dataset is used:

- [ ] Official source, dataset version, and publication/source are recorded.
- [ ] License, terms of use, and permitted research use are confirmed.
- [ ] Raw-data storage path and download method are documented.
- [ ] Exact class names and class-index mappings are verified.
- [ ] Image/volume shape, channels, format, and metadata are understood.
- [ ] Patient/study/slide grouping information is identified, where available.
- [ ] Duplicate/corrupt/excluded sample rules are documented.
- [ ] Class counts are produced.
- [ ] A train/validation/test manifest is created and saved.
- [ ] The manifest contains no unintended patient/study/slide leakage.
- [ ] Preprocessing and augmentation are appropriate for the modality.
- [ ] Dataset version or checksum is recorded.
- [ ] No credentials or private access tokens are committed to source control.

Do not fabricate a substitute dataset or mark a task ready merely because a configuration file exists.

---

## 7. Repository and Configuration Plan

### 7.1 Inspect before restructuring

Preserve useful current modules. Before adding duplicate systems, document the public interfaces of existing modules and their tests.

Review at least:

- `configs/taxonomy.yaml`
- `configs/thresholds.yaml`
- `configs/fairness_strata.yaml`
- `services/ml/registry.py`
- `services/ml/orchestrator.py`
- `services/ml/checkpoints.py`
- `services/ml/validation.py`
- `services/ingestion/`
- `services/router/`
- `services/gateway/`
- `services/rag/`
- `services/xai/`
- `services/uncertainty/`
- `tests/`

### 7.2 Proposed additions

Adapt names to the existing conventions; do not create duplicate registries or checkpoint managers unnecessarily.

```text
configs/
  taxonomy.yaml
  model_registry.yaml
  training/
    breast_ultrasound.yaml
    kidney_ct.yaml
    leukemia_microscopy.yaml
    oral_cancer.yaml
    lung_colon_histology.yaml
    lymphoma_histology.yaml
    brain_mri.yaml
    cervical_cytology.yaml

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
  manifests/
  checkpoints/
    breast_ultrasound/
    kidney_ct/
    leukemia_microscopy/
    oral_cancer/
    lung_colon_histology/
    lymphoma_histology/
    brain_mri/
    cervical_cytology/
  metrics/
  model_cards/
  logs/
```

Keep large raw datasets and generated checkpoints outside version control unless a documented repository policy explicitly says otherwise.

### 7.3 Example configuration contract

This is a schematic example only. It must be aligned with the actual dataset and current configuration parser before use.

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

Configuration notes:

- `class_names` must exactly reflect the verified task. The BUSI example above must not be used if the final design is binary or its actual labels differ.
- `patient_id` is a placeholder field and must not be assumed to exist. If no patient identifier is available, document the data limitation and the chosen split strategy.
- Segmentation, multi-label classification, and multi-class classification require task-appropriate data handling and metrics.
- Keep tasks disabled until the configuration, input data, and labels have passed verification.
- Save an immutable configuration snapshot with each run.

---

## 8. Unified Training Engine and Sequential Queue

### 8.1 Target command

The eventual interface should be simple, for example:

```powershell
python -m training.train_all --registry configs/model_registry.yaml
```

This is a **target command**; it is not guaranteed to exist in the current repository. Implement it only after agreeing on the package structure and configuration contract.

### 8.2 Common training engine responsibilities

Write the reusable mechanics once:

1. Validate the task configuration and dataset path.
2. Load the matching dataset adapter.
3. Check labels, sample integrity, class distribution, and split manifests.
4. Apply task-specific preprocessing.
5. Instantiate the appropriate modality branch and task-specific head.
6. Train using configurable loss, optimizer, scheduler, early stopping, and seed.
7. Evaluate on validation data for model selection.
8. Restore the selected checkpoint.
9. Evaluate once on the locked test split after choices are finalized.
10. Save weights, relevant optimizer/scheduler state, configuration, logs, metrics, and model card.
11. Register the task's real status.
12. Release memory/resources and proceed to the next enabled task.

### 8.3 Required queue behavior

- Deterministic task order.
- Resume a previously interrupted run only when task, model, dataset version, split, label mapping, and configuration are compatible.
- Retry an individual failed task without corrupting another model's checkpoint.
- Skip only a verified compatible checkpoint/run that meets the configured policy.
- Continue or stop on failure according to an explicit setting.
- Produce a full queue summary, including blocked and failed tasks.
- Never report an existing file as proof of successful training or evaluation.
- Record run IDs and timestamps.

### 8.4 Suggested run states

`NOT_CONFIGURED → READY → TRAINING → TRAINED → EVALUATED → RESEARCH_DEMO_READY`

Possible blocked/failure states:

- `BLOCKED_DATA`
- `BLOCKED_ENVIRONMENT`
- `FAILED_TRAINING`
- `FAILED_EVALUATION`
- `CHECKPOINT_INVALID`
- `NEEDS_REVIEW`

A checkpoint is not research-demo-ready merely because training finished. Required evaluation and review criteria must also pass.

### 8.5 Example queue summary

```text
01 breast_ultrasound      EVALUATED
02 kidney_ct              BLOCKED_DATA
03 leukemia_microscopy    NOT_CONFIGURED
04 oral_cancer            NOT_CONFIGURED
05 lung_colon_histology   NOT_CONFIGURED
06 lymphoma_histology     NOT_CONFIGURED
07 brain_mri              NOT_CONFIGURED
08 cervical_cytology      NOT_CONFIGURED
```

The actual summary must come from the manager's run records. This example is illustrative, not current execution output.

---

## 9. Dataset Selection, Preparation, and Leakage Prevention

### 9.1 Splitting policy

- Prefer patient-level, study-level, or slide-level splitting when multiple samples may come from the same source entity.
- Avoid placing crops/tiles of the same original slide in both train and test.
- Keep a final test split locked until model and threshold decisions have been made.
- Fit data-driven preprocessing statistics on the training split only.
- Record and check duplicates/near-duplicates where feasible.
- Track class counts for every split and investigate material imbalance.
- If a patient-level identifier is unavailable, document that limitation and evaluate the resulting risk of leakage.

### 9.2 Augmentation

- Use transformations suitable for the target and modality.
- Do not assume that every rotation, reflection, crop, colour adjustment, or intensity transformation preserves the label.
- Use deterministic validation/test preprocessing.
- Save the exact transform configuration for every run.

### 9.3 Optimization

Any example values for epochs, batch size, learning rate, early-stopping patience, or optimizer are starting hypotheses, not universal settings. Tune on validation data and available compute. Different tasks may need different data shapes, batch sizes, loss functions, training durations, and evaluation metrics.

### 9.4 Required run artifacts

For each task/run, produce:

- Training configuration snapshot.
- Dataset identity/version and split-manifest reference.
- Training/validation curves.
- Per-class sample support and metrics.
- Confusion matrix where appropriate.
- Classification report or task-appropriate equivalent.
- ROC-AUC only when the task's label format and sample support make it valid.
- Calibration information such as Brier score or expected calibration error, when appropriate.
- Checkpoint and cryptographic hash.
- Random seed, dependency versions, and runtime environment.
- Error/failure examples and known limitations.
- Model card and intended/prohibited use.

For segmentation tasks, report task-appropriate measures such as Dice and IoU instead of forcing classification-only metrics onto the task.

---

## 10. Model Evaluation, Checkpoints, and Experiment Records

### 10.1 Metrics

For classification tasks, consider:

- Accuracy.
- Precision.
- Sensitivity/recall.
- Specificity.
- Macro F1 and per-class results.
- ROC-AUC when statistically and technically appropriate.
- Confusion matrix.
- Calibration measures where applicable.
- Confidence intervals or suitable uncertainty estimates when feasible.

Medical imaging datasets can be imbalanced, so accuracy alone is insufficient. Choose a primary metric before training; explain why it suits the task. Do not claim that a single metric establishes clinical usefulness.

### 10.2 Checkpoint metadata

Each checkpoint should carry or reference:

- Stable task ID.
- Model architecture/configuration version.
- Dataset version and split-manifest ID.
- Class names and label mapping.
- Training run ID.
- Weight file hash.
- Training date and software version.
- Actual evaluation run ID and measured results, if available.
- Status such as `synthetic_test`, `trained`, `evaluated`, or `research_demo_ready`.

### 10.3 Essential correction for existing checkpoint code

Before using the current checkpoint machinery for real experiments:

- Remove example/default numeric performance metrics from production save/register paths.
- Mark absent values as unmeasured.
- Prevent randomly initialized weights from being registered as trained.
- Require a training manifest for genuine trained checkpoints.
- Verify that checkpoint loading succeeds in a fresh process.
- Validate architecture compatibility, output shape, class mapping, and metadata.
- Separate checkpoint creation, training completion, validation, final testing, and research-demo approval.

Synthetic checkpoints may be used for tests but must be labelled clearly and excluded from real inference and project performance reporting.

### 10.4 Experiment ledger

Every experiment must have a unique run ID and an immutable record containing:

- Hypothesis / objective.
- Task and modality.
- Dataset and split versions.
- Model/configuration version.
- Hyperparameters and seed.
- Start/end time and exit state.
- Training logs and selected epoch.
- Validation results and final test results, kept distinct.
- Artifact/checkpoint hashes.
- Known limitations and follow-up decision.

The experiment ledger is a high-value addition because it converts training work into traceable research evidence.

---

## 11. Inference Routing and Safe Failure Behavior

The system must not choose a model merely because the input is an image.

For each incoming input:

1. Validate type, size, integrity, and supported format.
2. Identify or request the modality and intended task.
3. Check the task registry and modality compatibility.
4. Verify that a compatible checkpoint exists and its status satisfies the inference policy.
5. Apply the exact preprocessing linked to that checkpoint.
6. Validate the model output shape, class mapping, and numerical values.
7. Return the result with task identity, model version, relevant limitations, and appropriate explanation.
8. Write an audit record while minimizing exposure of sensitive patient information.
9. Reject the input, abstain, or request clarification if the modality/task is unknown, unsupported, corrupt, or lacks a valid model.

The initial product should perform one explicitly selected and compatible task per request. Do not claim that it can diagnose all eight cancer categories from a single arbitrary image unless a dedicated, validated multi-task workflow actually exists.

### The “cannot reliably assess” outcome

Implement visible failure/abstention states for:

- Unsupported input type.
- Uncertain modality/task routing.
- Corrupt or invalid input.
- Missing checkpoint.
- Incompatible checkpoint/task ID.
- Unknown or mismatched label mapping.
- Out-of-scope task.
- Runtime/model failure.

This is a safety-oriented product behaviour, not proof that the model is clinically safe. Later uncertainty/calibration studies may inform a more evidence-based abstention policy.

---

## 12. RAG, Explainability, Uncertainty, Fairness, Longitudinal Analysis, and Outcomes

These workstreams complement a trained model but do not replace the need to train and evaluate it.

### 12.1 RAG

Current reviewed implementation appeared to include seeded evidence and lexical retrieval. A validated persistent embedding index was not established in the review.

Recommended next steps:

1. Curate a permitted source corpus and record source provenance/version.
2. Parse documents while preserving source title, version, page, section, and publication details.
3. Chunk and embed content; persist the index.
4. Consider hybrid lexical+dense retrieval and a reranking stage if justified.
5. Assemble an evaluation set of answerable and deliberately unanswerable questions.
6. Measure retrieval recall/relevance, citation correctness, answer faithfulness, and abstention behaviour.
7. Keep RAG knowledge retrieval separate from the image model's prediction path.
8. Never allow retrieved text to fabricate a model result or make unsupported clinical claims.

Do not fine-tune a local LLM before basic source-grounded retrieval works. Distinguish live LLM responses from deterministic fallback responses in logs and UI.

### 12.2 Explainability (XAI)

- Use methods appropriate to the model and modality.
- Validate explanation stability/fidelity and localization where feasible.
- Ensure an explanation belongs to the exact checkpoint and input being shown.
- Do not treat a heatmap or feature ranking as proof that a prediction is correct.
- Show known limitations and avoid unsupported causal language.

### 12.3 Uncertainty and calibration

- Measure calibration on appropriate held-out data.
- Do not label raw softmax scores as calibrated probabilities by default.
- Define abstention policy with validation evidence and document the trade-offs.
- Report uncertainty limitations and sample support.

### 12.4 Fairness

- Define relevant demographic/acquisition subgroups only where data legitimately support their evaluation.
- Report subgroup sample sizes and uncertainty.
- Avoid strong fairness claims when subgroup support is small or unavailable.
- Respect licensing, privacy, and data governance.

### 12.5 Longitudinal patient modelling

Before implementation, define the time unit, permitted data fields, outcome, data leakage controls, and evaluation protocol. Keep claims disabled until longitudinal data and an appropriate validation study exist.

### 12.6 Clinical outcomes

Define outcomes before analysis and separate proxy metrics from clinically meaningful endpoints. Do not imply improved patient outcomes without a design and evidence that support such a conclusion.

### 12.7 Federated learning and FHIR/interoperability

These are potentially valuable extensions but should remain later-stage until the one-task training/inference path and data governance are solid. Do not prioritize complex multi-institution or interoperability claims merely because service folders/configurations exist.

---

## 13. Testing, Environment, Deployment, and Security

### 13.1 Re-establish a reliable environment

The earlier test command did not complete because `structlog` was missing. Re-run in a clean environment with the project's declared Python and dependency requirements. Do not treat a partial collection result as the final test outcome.

### 13.2 Testing gates

**Gate A — Environment**
- Create a clean virtual environment.
- Install declared dependencies.
- Run compile checks.
- Run the complete test suite to completion.
- Fix dependency/build failures and record versions and output.

**Gate B — One-task vertical slice**
- Verified dataset.
- Deterministic split manifest.
- Real training run.
- Saved and reloaded checkpoint.
- Final test report.
- Inference through the actual API/orchestrator path.
- Audit/log output.
- Tests for malformed input, missing checkpoint, mismatched labels, and invalid configuration.

**Gate C — Training manager**
- Config validation tests.
- Deterministic task order.
- Resume and retry tests.
- Task isolation and checkpoint compatibility tests.
- Failure isolation and full queue summary.
- Small synthetic dataset integration test.

**Gate D — Eight-task configuration**
- Data source/license/labels verified per enabled task.
- Each task has a valid configuration and split manifest.
- Tasks without valid data remain blocked.
- Sequential queue produces an auditable result.

**Gate E — Research demo**
- Per-task evaluation artifacts available.
- Model versions and inputs traceable.
- RAG citations/abstention tested separately.
- XAI and uncertainty claims proportional to validation.
- Documented limitations and non-clinical status.

### 13.3 Deployment

- Review `.env.example` and keep secrets out of source control.
- Do not use production credentials for demos.
- Verify each configured service's actual health.
- Exercise an end-to-end request after deployment.
- Record what ran locally and what ran through Docker.
- Avoid exposing identifiable patient data in logs or dashboard exports.
- Document authentication, access control, retention, and data deletion policy appropriate to the prototype.

---

## 14. Phased Roadmap and Exit Criteria

These are execution phases for the unified architecture. They are not promises that each phase is already complete.

### Phase 0 — Freeze, inspect, and stabilize the baseline

**Work**
1. Create a branch/backup.
2. Inspect the current working tree, dependency configuration, and project documents.
3. Run compilation and full tests in a clean environment.
4. Document existing module contracts and current blockers.
5. Remove misleading checkpoint metric defaults.
6. Confirm the authoritative eight-category taxonomy and resolve documentation drift.

**Exit criteria**
- Current repository baseline is repeatable.
- Full test status is known.
- No synthetic/default score can be mistaken for an actual experiment.
- Task scope and current gaps are documented.

### Phase 1 — Complete one real task end to end

**Work**
1. Select a dataset based on accessibility, permitted use, labels, and suitability.
2. Verify task definition and modality.
3. Implement an adapter and leakage-resistant split.
4. Train a baseline model.
5. Save actual weights, configuration, logs, and run metadata.
6. Reload the checkpoint in a fresh process.
7. Evaluate on a locked test split.
8. Integrate inference into the real router/API/UI path.
9. Produce a model card and experiment report.

**Exit criteria**
- One verified task can be trained, evaluated, reloaded, and served using real data.
- Results are traceable and reproducible.
- Failure states and missing-checkpoint states work.

### Phase 2 — Build and test the reusable hybrid engine

**Work**
1. Establish a stable task/configuration contract.
2. Add or finalize dataset adapters, model factory, task-specific heads, generic training/evaluation, and checkpoint lifecycle.
3. Implement the queue with run states, resume, retry, and a consolidated report.
4. Add integration tests using a tiny synthetic dataset.
5. Verify that task labels/checkpoints cannot be silently mixed.

**Exit criteria**
- A second task can be added through a verified adapter/configuration and necessary model implementation without duplicating the entire codebase.
- The trainer and queue behave reproducibly.

### Phase 3 — Configure and train all eight task slots

**Work**
1. Verify each dataset and its data-use permissions.
2. Resolve labels, modality, input shape, and prediction objective.
3. Create and test all eight configurations.
4. Run enabled tasks sequentially.
5. Preserve per-task reports and model cards.
6. Keep tasks with unresolved data/task definitions marked blocked.

**Exit criteria**
- Every enabled task has a genuine reproducible training/evaluation record.
- Unavailable or unverified tasks are transparently incomplete rather than silently simulated.

### Phase 4 — Evaluate parameter sharing

**Work**
1. Group compatible modalities based on data properties.
2. Establish independent baselines.
3. Compare independent models, shared encoder/task-specific head, and shared pretraining followed by task-specific fine-tuning as feasible.
4. Evaluate each task separately, not only aggregate scores.
5. Track negative transfer and subgroup degradation.
6. Document why each shared component is retained or rejected.

**Exit criteria**
- The final hybrid design is informed by reproducible comparative experiments.

### Phase 5 — Research extensions and product hardening

**Work**
- Build and evaluate persistent RAG retrieval/citations.
- Validate XAI and uncertainty.
- Run fairness analysis where valid data support it.
- Add longitudinal/outcome studies only with appropriate data and methodology.
- Verify access controls, audit behaviour, service health, monitoring, and release documentation.

**Exit criteria**
- Each extended claim has evidence and known limitations.
- No unverified clinical-readiness claim is made.

---

## 15. Project Dashboard and Evidence-Based Tracking

A professional dashboard should be a project-control instrument, not only a decorative progress chart.

### 15.1 Recommended dashboard sections

1. **Executive overview**
   - Latest audit date.
   - Overall engineering readiness estimate (clearly labelled estimated).
   - Number of tasks configured, datasets verified, models trained, models evaluated, and test suites passed.
   - Blockers needing decisions.

2. **Phase readiness**
   - Design, scaffold, implementation, testing, training, evaluation, integration, and release states.
   - Current evidence and next milestone.
   - Clear distinction between estimated readiness and verified outcomes.

3. **Eight-task portfolio**
   - Task ID, modality, objective, dataset verification, label mapping, split status, training status, checkpoint status, test status, and owner/next action.
   - Each task must be tracked independently.

4. **Experiment results**
   - Actual train/validation curves.
   - Confusion matrix and per-class recall/macro F1.
   - ROC-AUC and calibration metrics when appropriate.
   - Dataset split sizes and checkpoint version.
   - “Not yet measured” instead of invented scores.

5. **Workstream status**
   - ML/training, ingestion/routing, RAG, XAI, uncertainty, fairness, longitudinal/outcomes, API/frontend, testing, deployment, security.

6. **Risk register**
   - Risk, impact, mitigation, owner, status, and decision needed.

7. **Decision log**
   - Date, decision, reason/evidence, alternatives considered, consequence, and follow-up.

8. **Faculty view/export**
   - Concise status, demonstrated capabilities, unresolved work, next milestone, and limitations.
   - Print/export without exposing sensitive patient information or secrets.

### 15.2 Evidence-based tracker states

Prefer a progression such as:

`PLANNED → DESIGNED → SCAFFOLDED → IMPLEMENTED → TESTED → EXPERIMENTALLY EVALUATED`

For ML tasks, also track:

`DATA_VERIFIED`, `TRAINED`, `CHECKPOINT_VERIFIED`, `INFERENCE_INTEGRATED`, and `RESEARCH_DEMO_READY`.

Every state change should have:
- Evidence or artifact.
- Last verified date.
- Responsible person (if this is a team project).
- Next action or blocker.

### 15.3 Dashboard improvements worth doing now

- Replace unqualified percentages with evidence-based status.
- Add the experiment-results page, even if it initially says “Not yet measured”.
- Add the decision log and latest verification dates.
- Link to test reports, model cards, logs, and checkpoints where accessible.
- Keep the current dashboard estimates labelled as provisional until updated against the live repository.

A dashboard with honest incomplete states is more credible than one displaying polished but unsupported progress numbers.

---

## 16. Faculty Presentation and Demonstration Plan

### 16.1 Claims that are supportable from the earlier archive review

Subject to a fresh check, the following wording is appropriate:

- “OncoSentinel is designed as a modular research and decision-support platform for multiple cancer-imaging tasks.”
- “The project defines an eight-category taxonomy and contains scaffolding for ingestion, routing, ML orchestration, RAG, explainability, uncertainty, audit, and related services.”
- “The current engineering priority is a reusable hybrid training engine, a sequential training queue, and a real end-to-end validated task.”
- “We are tracking architecture completion separately from experimentally verified model performance.”

### 16.2 Claims to avoid until evidence exists

- “All eight cancer models are trained.”
- “The model achieves a particular accuracy” unless it comes from a documented real evaluation.
- “The system diagnoses cancer reliably” or “is clinically ready.”
- “The RAG system uses validated vector search” before persistent retrieval and evaluation are demonstrated.
- “The test suite passes” before the complete test command finishes successfully.
- “The shared network performs better” before controlled baseline comparisons exist.
- “The platform improves clinical outcomes” without an appropriate outcomes study.

### 16.3 Recommended live demonstration

Prepare one permitted sample dataset and a repeatable demo:

1. Show the dataset source, task definition, class distribution, and split plan.
2. Demonstrate preprocessing and task routing.
3. Run inference using a known trained checkpoint.
4. Show measured evaluation results from the correct split.
5. Show one model explanation and clearly state its limitations.
6. Demonstrate a safe rejection for unsupported input or missing model.
7. Open the run record to show config, model version, checkpoint hash, and limitations.
8. Show the eight-task roadmap with the actual states of all remaining tasks.

### 16.4 Suggested presentation narrative

> “The project is being built as one unified hybrid platform rather than eight duplicated applications. A common training and evaluation engine will process each verified task sequentially, while modality-specific branches and task-specific heads preserve the differences between imaging types and label definitions. We are separating design and scaffold milestones from measured model results. The next milestone is a fully reproducible end-to-end task; only after that will we scale the same process across the remaining task slots and evaluate whether shared representations help.”

This narrative describes the design direction and plan. Update the wording as implementation evidence accumulates.

---

## 17. Risk Register

| ID | Risk | Why it matters | Mitigation / response |
|---|---|---|---|
| R1 | Default/example checkpoint metrics look real | Can lead to false research claims | Remove defaults; require evaluation-run provenance |
| R2 | Dataset label/task mismatch | Model may learn an invalid target | Verify every class and target before implementing the loader |
| R3 | Data leakage | Metrics can be misleadingly high | Split at patient/study/slide level where possible; lock test set |
| R4 | Over-sharing model weights | Negative transfer or modality mismatch | Compare independent baselines with controlled sharing experiments |
| R5 | Missing dependencies prevent tests | Code behaviour remains unverified | Reproducible environment and full test run |
| R6 | RAG appears stronger than it is | Seeded lexical retrieval may be confused with validated RAG | Build persistent retrieval and measure evidence/citation quality |
| R7 | Explanation visualisations are overinterpreted | Heatmaps can be misleading | Validate explanation methods and communicate limits |
| R8 | UI reports every configured task as available | Could route to random, incompatible, or missing weights | Registry compatibility gate and explicit state machine |
| R9 | Scope drifts between eight-task and four-head documents | Confuses implementation and faculty expectations | Keep eight-category main taxonomy authoritative; document any change |
| R10 | Deployment configs are mistaken for a running system | Operational readiness is overstated | Health checks, end-to-end tests, release checklist |
| R11 | Data/privacy issues in logs or exports | Could expose sensitive information | Data minimization, access control, safe logs, no secrets in repo |
| R12 | Too many advanced features before baseline works | Creates broad scaffolding without a demonstrable result | Prioritize one complete vertical slice and then generalize |

---

## 18. Immediate Prioritized Checklist

Complete these in order before a full eight-task training run.

### Priority 1 — Baseline credibility

- [ ] Confirm the main eight-category taxonomy is the authoritative scope.
- [ ] Check current branch and working tree; create a safe backup/version-control checkpoint.
- [ ] Create a clean environment consistent with the project's dependency pins.
- [ ] Resolve missing dependency/build problems and run the full test suite.
- [ ] Record exactly which tests passed, failed, or did not run.
- [ ] Remove default/example checkpoint metrics.
- [ ] Audit model registration so random weights cannot appear as trained.

### Priority 2 — First complete task

- [ ] Select a viable, permitted dataset.
- [ ] Verify labels and modality.
- [ ] Create split manifest with leakage controls.
- [ ] Implement/reuse a dataset adapter.
- [ ] Train a real baseline.
- [ ] Save config, logs, weights, metrics, and metadata.
- [ ] Reload the checkpoint in a fresh process.
- [ ] Evaluate on the locked test split.
- [ ] Integrate inference into the actual application/API path.
- [ ] Build a concise result/model card.
- [ ] Record all limitations.

### Priority 3 — Unified engine

- [ ] Finalize the task registry and configuration contract.
- [ ] Implement the model factory and modality-aware branches.
- [ ] Implement reusable training and task-appropriate evaluation.
- [ ] Implement checkpoint validation and run metadata.
- [ ] Implement deterministic sequential queue.
- [ ] Add resume, retry, failure isolation, and queue summary.
- [ ] Test with a tiny synthetic dataset before expensive runs.

### Priority 4 — Expand to the remaining tasks

- [ ] Verify every dataset/source/license.
- [ ] Resolve all labels and objectives.
- [ ] Add and test configurations one at a time.
- [ ] Train all enabled tasks sequentially.
- [ ] Keep blocked tasks explicitly blocked.
- [ ] Publish per-task model cards and results.

### Priority 5 — Research-quality improvements

- [ ] Establish individual baselines before sharing weights.
- [ ] Evaluate shared encoders by compatible modality group.
- [ ] Validate explanations and uncertainty.
- [ ] Implement persistent RAG retrieval and citation evaluation.
- [ ] Perform fairness analyses only where data support them.
- [ ] Add longitudinal/outcomes research only when valid data and methods exist.
- [ ] Update the dashboard from genuine evidence and verification dates.

---

## 19. Definition of Done

### 19.1 One-task vertical slice is done when

- A verified dataset is identified and permitted for the intended research use.
- The task and label definitions are explicit.
- A valid split manifest exists.
- A real training run completes.
- The checkpoint and full run metadata are saved.
- The checkpoint reloads in a fresh process.
- The final test report is generated and kept separate from validation results.
- The real API/orchestrator can use the checkpoint.
- Failure and unsupported-input cases are tested.
- A model card and known-limitations note exist.

### 19.2 Unified training engine is done when

- The authoritative registry defines all eight task slots.
- Enabled tasks run sequentially through one command.
- Shared infrastructure handles data validation, training, evaluation, checkpointing, and reporting.
- Modality-specific branches and task-specific heads are explicitly configured.
- Resume verifies dataset/configuration/model compatibility.
- Failures do not corrupt another task's checkpoint.
- The queue summary lists successes, failures, and blocked tasks.
- All displayed metrics link to real evaluation runs.

### 19.3 Research demo readiness is reached when

- Every active inference model has a verified compatible checkpoint.
- Inputs are checked for task/modality compatibility.
- Unsupported inputs are rejected or routed to clarification.
- Results are traceable to task/model version.
- Explainability and uncertainty outputs are not overclaimed.
- The test suite's actual status is known.
- Known limitations and non-clinical status are visible.
- The dashboard accurately distinguishes configured, trained, evaluated, and demo-ready tasks.

This is a research-demo bar, not a clinical-validation standard.

---

## 20. Suggested Repository Commands

The following are starting commands for a Windows PowerShell workflow. Confirm the current repository path, Python requirement, and dependency configuration before running them.

```powershell
# Move to the repository directory (adjust path if needed)
cd "RAG Major Project"

# Create and activate a project environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Update pip and install the declared project dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# Syntax/bytecode compilation check
python -m compileall -q services tests

# Run the complete test suite
python -m pytest -q
```

If installation fails, resolve the declared dependency/build problem instead of silently bypassing the environment requirements. If pytest does not complete, record the blocker and do not claim the suite passed.

The earlier review suggested that Python 3.11 may be a sensible environment for the project's pinned dependencies, but this must be confirmed against the current `pyproject.toml` and package compatibility.

### Baseline audit evidence to save

```text
audit/
  environment.txt
  dependency_install.log
  compileall.log
  pytest.log
  repository_tree.txt
  open_blockers.md
```

These are suggested artifacts, not files already confirmed to exist.

---

## 21. Decision Log Template

Maintain a concise decision log in the repository, for example `project-docs/DECISIONS.md`.

```markdown
## Decision: <short title>
- Date:
- Status: Proposed / Accepted / Rejected / Superseded
- Context/problem:
- Options considered:
- Decision:
- Evidence/reason:
- Impact on architecture/data/training:
- Risks/limitations:
- Follow-up action:
- Related run/issue/commit:
```

Record decisions such as:
- Why a dataset and label mapping were chosen.
- Why a task is classification or segmentation.
- Which encoders are shared and why.
- Whether a shared encoder was retained after comparison.
- Why a task remains blocked.
- Changes to the official eight-category scope.

---

## 22. Run Record and Model Card Templates

### 22.1 Experiment run record

```yaml
run_id: "<unique-run-id>"
task_id: "<stable-task-id>"
status: "TRAINED"  # update only from real run status
dataset_id: "<dataset-name-and-version>"
split_manifest: "<path-or-id>"
config_snapshot: "<path-or-id>"
seed: 42
model_architecture: "<architecture-and-version>"
checkpoint_path: "<path>"
checkpoint_sha256: "<hash>"
started_at: "<timestamp>"
finished_at: "<timestamp>"
metrics:
  validation: null
  test: null
notes: []
limitations: []
```

This is a schema example. `null` must remain `null` until a metric is genuinely measured. Do not mark the example run as trained or use example values as actual project evidence.

### 22.2 Model card minimum fields

```markdown
# Model Card — <Task ID>

## Intended use
## Out-of-scope / prohibited use
## Input modality and expected format
## Prediction objective and class mapping
## Dataset source, version, license, and population
## Train/validation/test split method
## Model architecture and checkpoint version
## Training procedure and configuration
## Evaluation protocol and measured results
## Per-class performance and sample support
## Calibration / uncertainty evaluation, if applicable
## Explainability method and limitations
## Known failure modes and limitations
## Fairness/subgroup evaluation, if supported
## Reproducibility instructions
## Date and reviewer
```

---

## 23. Final Recommendations

### What is most worth doing

1. **Establish credibility first.** Make the complete test suite run and remove misleading metrics.
2. **Finish one end-to-end task.** This is the most important near-term technical milestone.
3. **Build the common engine, not eight duplicate pipelines.** Reuse adapters/interfaces, training, evaluation, logging, checkpointing, and reporting.
4. **Keep model science task-aware.** Do not force incompatible modalities and objectives through one unchanged network.
5. **Train sequentially with explicit statuses.** Resume/retry safely and show every task's real state.
6. **Use evidence-based tracking.** Store real metrics, run records, decision history, and model cards.
7. **Test weight sharing after baselines exist.** Treat sharing as a research question and evaluate negative transfer.
8. **Defer costly extras.** Federated learning, broad multimodal fusion, local-LLM fine-tuning, and clinical-readiness claims are not the best first use of time.
9. **Keep the dashboard honest.** Use “Not yet measured”, “Blocked”, or “Not verified” when that is the truth.
10. **Prepare a repeatable faculty demo.** Show one real result, its provenance, an explanation with limitations, and safe rejection behaviour.

### The core strategy in one sentence

**Build the reusable hybrid training and evaluation infrastructure, prove it on one verified task, then expand sequentially to all eight while preserving independent checkpoints, honest per-task evaluation, and a clear evidence trail.**

That strategy gives OncoSentinel a realistic path from a broad scaffold to a credible, professional research prototype without confusing design progress with scientific validation.
