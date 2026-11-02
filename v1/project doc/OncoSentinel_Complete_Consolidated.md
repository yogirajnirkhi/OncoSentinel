# ONCOSENTINEL — COMPLETE CONSOLIDATED DOCUMENTATION

**Contents of this file (all four uploaded PDFs, in full):**

| Part | Source PDF | Document |
|---|---|---|
| A | `OncoSentinel_SRS_v2_0_docx.pdf` | Software Requirements Specification (SRS) v2.0 — Research-gap aligned |
| B | `OncoSentinel_Architecture_v2_0_docx.pdf` | Updated System Architecture v2.0 — Research-gap aligned |
| C | `OncoSentinel_PRD_v2_0_docx.pdf` | Product Requirements Document (PRD) v2.0 — Research-gap aligned |
| D | `Research_Gap_Analysis_docx__1_.pdf` | Research Gap Analysis: AI, ML, Federated Learning, LLMs, and Explainable AI in Cancer and Rare-Disease Diagnosis |

All four OncoSentinel documents: Version 2.0 | Research-gap aligned baseline | Body text 10 pt.

---
---

# PART A — ONCOSENTINEL: SOFTWARE REQUIREMENTS SPECIFICATION (SRS v2.0)

**SRS v2.0 — Research-gap aligned**
Version 2.0 | Research-gap aligned baseline | Body text 10 pt

## Document Control

| Field | Value |
|---|---|
| Document version | 2.0 |
| Status | Research-gap aligned baseline |
| Base body text | 10 pt |
| Product | OncoSentinel |
| Primary scope | Multimodal cancer AI + clinical decision support + research evaluation |
| Taxonomy | Authoritative eight-category Multi Cancer taxonomy |
| Safety position | AI-assisted decision support; not autonomous diagnosis or treatment authority |

## 1. Introduction

### 1.1 Purpose

This SRS defines the functional, non-functional, AI/ML, data, security, RAG, explainability, uncertainty, longitudinal modeling, fairness, clinical evaluation, integration, deployment, and governance requirements for OncoSentinel v2.0.

### 1.2 Research basis

The update is grounded in the supplied literature.

- **Kourou et al.** identify small datasets, inadequate validation, heterogeneous data, and limited clinical translation.
- **Pati et al.** demonstrate the value of federated multi-site training and explicit out-of-sample testing.
- **Zhang et al.** emphasize data normalization, interoperability, scale, and translation barriers.
- **Sangwan** demonstrates the need for quantitative explanation evaluation while identifying the limitations of pixel-level explanations.
- **Shyr et al.** demonstrate end-to-end rare-disease workflow modeling and identify the need for prospective evaluation, broader representation, and clinically meaningful deployment.

### 1.3 Scope

OncoSentinel shall:

- accept text, images, PDFs and multimodal combinations;
- validate and normalize inputs;
- route supported cancer-analysis requests to appropriate ML models;
- route evidence questions to RAG;
- use a local LLM only under explicit grounding controls;
- support approved external fallback;
- provide uncertainty and safe abstention;
- create concept-based explanations;
- maintain longitudinal case timelines;
- support federated research;
- evaluate fairness;
- collect clinical outcomes; and
- preserve provenance/auditability.

### 1.4 Intended Users

- CLINICIAN
- RESEARCHER
- ADMIN
- ANALYST
- AUDITOR
- AUTHORIZED DATA CURATOR
- CLINICAL STUDY REVIEWER

## 2. Product Scope and Taxonomy

The initial ML scope remains the authoritative eight categories:

1. Breast
2. Kidney
3. ALL/Leukemia
4. Oral Cancer
5. Lung & Colon
6. Lymphoma
7. Brain
8. Cervical

Category-specific class mappings, modalities, datasets, calibration policies, uncertainty policies, explanation types, fairness strata, and clinical study status shall be versioned through registry/configuration.

## 3. System Architecture

```
USER -> INPUT GATEWAY -> CONTENT UNDERSTANDING -> INTENT/RELEVANCE/SAFETY ROUTER
-> ML ORCHESTRATOR -> SHARED BACKBONE -> CATEGORY HEAD -> UNCERTAINTY/OOD
-> LONGITUDINAL CONTEXT -> CLINICAL XAI -> SAFETY/EVIDENCE/Fairness gates
-> HUMAN REVIEW -> REPORT / OUTCOME CAPTURE
OR
-> RAG ORCHESTRATOR -> VECTOR DB/KG -> EVIDENCE CHECK -> LOCAL LLM
-> XAI/PROVENANCE/SAFETY -> HUMAN REVIEW -> REPORT / OUTCOME CAPTURE
OR
-> APPROVED EXTERNAL WEB/API -> SOURCE VALIDATION -> LOCAL LLM -> VERIFIER
ALL ROUTES -> AUDIT + MODEL/DATA PROVENANCE + METRICS + CLINICAL OUTCOME LAYER
MLOps/Federated loop -> DRIFT -> RETRAIN -> CALIBRATE -> FAIRNESS -> APPROVE -> DEPLOY
```

## 4. Functional Requirements

| ID | Requirement | Statement |
|---|---|---|
| FR-01 | Input ingestion | Accept text, image, PDF and multimodal requests and create a common RequestContext. |
| FR-02 | Input validation | Validate type, integrity, security, image quality, page extraction, OCR and content safety. |
| FR-03 | Intent/relevance routing | Determine user intent, modality, cancer relevance, category, supported capability and phase status. |
| FR-04 | ML gate | Permit ML inference only when modality/category/model/quality/phase constraints are satisfied. |
| FR-05 | ML inference | Return prediction, model/version, class probabilities where supported, confidence, uncertainty and artifacts. |
| FR-06 | Calibration | Maintain category/modality-specific calibration artifacts and versioned thresholds. |
| FR-07 | OOD detection | Detect inputs outside expected data distribution and trigger review or abstention policies. |
| FR-08 | Safe abstention | Return ABSTAIN/REVIEW or NO_GROUNDED_ANSWER when evidence or model certainty is insufficient. |
| FR-09 | RAG retrieval | Support metadata filtering, hybrid retrieval, reranking, evidence scoring and citation identity. |
| FR-10 | Local LLM | Structure and summarize supplied evidence; it shall not fabricate missing clinical evidence. |
| FR-11 | External fallback | Use approved sources/APIs only when internal evidence is insufficient and external lookup is permitted. |
| FR-12 | Answer verification | Verify relevance, grounding, provenance, contradiction, safety and citation integrity. |
| FR-13 | Clinical XAI | Produce concept-based explanations linked to clinical findings and supporting/counter evidence. |
| FR-14 | Technical XAI | Provide SHAP/Grad-CAM/attribution artifacts when supported by the model type. |
| FR-15 | Explanation evaluation | Store fidelity, robustness, localization and clinician-utility evaluation results. |
| FR-16 | Longitudinal timeline | Store time-stamped diagnosis, imaging, pathology, laboratory, treatment, response and outcome events. |
| FR-17 | Temporal context | Use authorized longitudinal context in prediction/reasoning and expose which timepoints influenced output. |
| FR-18 | Fairness evaluation | Compute subgroup performance, calibration, error and abstention metrics under approved governance. |
| FR-19 | Fairness reporting | Produce machine-readable and human-readable fairness reports and flag unacceptable disparities. |
| FR-20 | Human-in-loop | Allow clinician accept/edit/reject/request-evidence/abstain actions and record feedback. |
| FR-21 | Clinical outcome capture | Capture study-specific workflow and patient-relevant outcome variables under approved governance. |
| FR-22 | External validation | Support unseen-site, temporal and subgroup evaluation datasets without training leakage. |
| FR-23 | Federated training | Support local site training and secure aggregation without raw patient-data movement. |
| FR-24 | Continuous learning | Support staged retraining, validation, fairness, calibration and rollback gates. |
| FR-25 | Drift monitoring | Detect data, performance, calibration and subgroup drift. |
| FR-26 | Model registry | Store model ID, version, category, modalities, datasets, metrics, calibration, uncertainty, XAI and deployment state. |
| FR-27 | Dataset registry | Store dataset version, population, taxonomy, modalities, preprocessing, annotation policy, subgroup metadata and splits. |
| FR-28 | Case/report management | Create cases, attach inputs/results/evidence, generate reports and retrieve history by permission. |
| FR-29 | Auditability | Retain route, model, evidence, source, explanation, uncertainty, fairness, clinician action and outcome provenance. |
| FR-30 | Terminal safety states | Support explicit unsupported, abstain, review-required and no-grounded-answer states. |

## 5. Non-Functional Requirements

| ID | Area | Requirement |
|---|---|---|
| NFR-01 | Reliability | Critical services shall fail safely; uncertain or unsupported medical claims shall not be silently emitted. |
| NFR-02 | Performance | Latency budgets shall be benchmark-derived for ingestion, routing, inference, retrieval, XAI, LLM and external lookup. |
| NFR-03 | Scalability | ML, RAG, longitudinal, outcome and reporting services shall scale independently. |
| NFR-04 | Security | Use secure auth, RBAC, encryption in transit/at rest, secrets management, validation, rate limiting and vulnerability scanning. |
| NFR-05 | Privacy | Minimize sensitive data, enforce access control, support de-identification and local data retention for federated workflows. |
| NFR-06 | Explainability | Clinical explanations must be understandable, evidence-linked and accompanied by method/version metadata. |
| NFR-07 | Calibration | Probability outputs used for decisions shall be evaluated for calibration and monitored after deployment. |
| NFR-08 | Fairness | Supported models must have defined subgroup evaluation plans before clinical deployment. |
| NFR-09 | Longitudinal integrity | Patient timelines must preserve immutability of historical facts, timestamps and provenance. |
| NFR-10 | Outcome integrity | Clinical outcome measurements must be linked to study protocol versions and avoid inappropriate leakage into model training. |
| NFR-11 | Observability | Collect logs, metrics, traces, drift, calibration, fairness, outcome and audit signals without unnecessary PHI exposure. |
| NFR-12 | Reproducibility | Dataset, model, policy, calibration, explanation and evaluation versions must be reproducible. |
| NFR-13 | Interoperability | Support a standards-oriented integration path for hospital/EHR/PACS/RIS/LIS/FHIR/HL7 workflows where deployed. |
| NFR-14 | Portability | Local, hybrid and cloud deployments shall be supported through containerized services and provider abstraction. |

## 6. AI/ML Research Requirements

- All category heads must follow the authoritative taxonomy and documented task definition.
- Internal and external validation must be separated and leakage-controlled.
- Performance must be reported by overall cohort and approved subgroups.
- Calibration, uncertainty and OOD behavior must be reported alongside discrimination metrics.
- Model cards must include intended use, exclusions, limitations, data lineage, fairness results, uncertainty characteristics and explanation support.
- Continuous-learning updates must not enter production without repeat validation, fairness assessment, calibration check and rollback artifact.
- Research experiments must record random seeds, software versions, dataset versions, configuration, hyperparameters and evaluation scripts.

## 7. Clinical XAI Requirements

- Clinical explanations shall identify salient concepts, not only raw pixels/features.
- Each explanation shall expose source evidence and, when available, counter-evidence.
- Technical attribution maps shall be retained for audit but shall not be presented as inherently clinically valid.
- Explanation quality shall be evaluated with quantitative fidelity/robustness measures and clinician-centered usefulness studies.
- Explanation text shall distinguish model evidence from retrieved guideline/literature evidence and generated synthesis.

## 8. Longitudinal Requirements

| Requirement | Specification |
|---|---|
| Timeline | Append-only time-stamped event model with diagnosis, imaging, pathology, labs, treatment, response, outcomes. |
| Temporal leakage control | Training/validation splits must respect time when the study question is prospective/forecasting. |
| Trajectory features | Support trends, changes, intervals, treatment exposure and recurrence/progression markers. |
| Context visibility | UI/report must disclose which historical events were used by the model or reasoning layer. |
| Missingness | Missing events must be represented explicitly rather than treated as absence. |

## 9. Fairness Requirements

- Define evaluation strata before study execution.
- Report subgroup sensitivity, specificity, F1/AUC, calibration error, false-negative rate, false-positive rate, abstention rate and explanation-utility results where sample size permits.
- Investigate whether model routing or data-quality gates disproportionately reject specific groups.
- Fairness reports must be versioned and attached to the model release record.
- Mitigation actions may include data collection, reweighting, subgroup-specific calibration, threshold adjustment or model redesign; mitigation must be justified and revalidated.

## 10. Clinical Outcome Requirements

| Outcome level | Required measurements |
|---|---|
| Technical | AUC, sensitivity, specificity, F1, calibration, segmentation metrics as applicable, OOD/abstention performance |
| Workflow | time-to-diagnosis, time-to-review, clinician workload, decision time, override rate |
| Decision quality | appropriate escalation, unsafe misses, clinician-AI agreement, evidence use |
| Patient-level | study-specific downstream care/outcome variables approved by ethics/governance |
| Safety | critical-error rate, grounding failures, incorrect citation rate, unsafe automation rate |

## 11. Data Model Additions

| Object | New/updated fields |
|---|---|
| Prediction | calibration_set_version, confidence, uncertainty_vector, ood_score, abstention_decision |
| Explanation | explanation_id, concept_list, evidence_ids, counter_evidence_ids, method, fidelity_metrics |
| PatientTimelineEvent | event_time, event_type, source, provenance, confidence, missingness_state |
| FairnessEvaluation | model_version, subgroup_definition, metric_set, results, threshold_policy, status |
| ClinicalOutcome | study_id, endpoint, measurement_time, value, source, adjudication_state |
| ModelVersion | calibration_policy, uncertainty_policy, fairness_report_id, explanation_policy, drift_baseline |

## 12. API Requirements

```
POST /api/v2/analyze
POST /api/v2/ingest
POST /api/v2/predictions/{id}/review
GET  /api/v2/predictions/{id}/uncertainty
GET  /api/v2/predictions/{id}/explanation
GET  /api/v2/cases/{id}/timeline
POST /api/v2/cases/{id}/timeline-events
GET  /api/v2/models/{id}/fairness
GET  /api/v2/models/{id}/calibration
GET  /api/v2/models/{id}/drift
POST /api/v2/outcomes
GET  /api/v2/studies/{id}/outcomes
POST /api/v2/federated/rounds
GET  /api/v2/audit
```

## 13. Testing and Acceptance

- Unit, integration, API, security, routing, model smoke, RAG, XAI, longitudinal, fairness, calibration and drift tests.
- Synthetic and retrospective tests must include known ambiguous/unsupported inputs and required safe-failure states.
- External validation datasets must be held out from all model selection and threshold tuning.
- Clinical validation must have a predefined analysis plan and endpoint definitions.
- Phase promotion requires all relevant technical, uncertainty, fairness, safety and documentation gates to pass.

## 14. Phase Plan v2.0

| Phase | Scope | Exit gate |
|---|---|---|
| Phase 1 | Breast + Kidney; multimodal ingestion, routing, ML, uncertainty skeleton | Validated end-to-end pipeline + calibrated baseline |
| Phase 2 | All eight categories; authoritative taxonomy and category heads | All categories routable + external validation protocol operational |
| Phase 3 | RAG, KG, local LLM, concept-XAI, evidence verifier, longitudinal timeline | Grounded workflow + explainability evaluation + timeline integrity |
| Phase 4 | Federated learning, fairness engine, drift monitoring, continual-learning controls | Multi-site simulation + fairness/uncertainty gates + rollback |
| Phase 5 | Clinical pilot, outcome capture, comparative evaluation, hospital integration | Prospective evidence package + production-oriented baseline |

## 15. Safety and Regulatory Position

OncoSentinel is an AI-assisted research and clinical decision-support platform. It must clearly distinguish model predictions, retrieved evidence, generated synthesis, and external information. It shall provide safe abstention and shall not autonomously prescribe treatment. Production clinical use requires institution-specific governance, validation, legal review, and regulatory assessment appropriate to the deployment jurisdiction and intended use.

## 16. Literature References

- Kourou, K., Exarchos, T. P., Exarchos, K. P., Karamouzis, M. V., & Fotiadis, D. I. (2015). Machine learning applications in cancer prognosis and prediction. *Computational and Structural Biotechnology Journal*, 13, 8-17.
- Pati, S., et al. (2022). Federated Learning Enables Big Data for Rare Cancer Boundary Detection. arXiv:2204.10836v2.
- Zhang, B., Shi, H., & Wang, H. (2023). Machine Learning and AI in Cancer Prognosis, Prediction, and Treatment Selection: A Critical Approach. *Journal of Multidisciplinary Healthcare*, 16, 1779-1791.
- Sangwan, H. (2024). Quantifying Explainable AI Methods in Medical Diagnosis: A Study in Skin Cancer. medRxiv preprint 2024.12.08.24318158.
- Shyr, C., Hu, Y., Tinker, R. J., et al. (2026). An artificial intelligence framework for end-to-end rare disease phenotyping from clinical notes using large language models. arXiv:2602.20324v1.

---
---

# PART B — ONCOSENTINEL: UPDATED SYSTEM ARCHITECTURE (v2.0)

**Research-gap aligned Architecture v2.0**
Version 2.0 | Research-gap aligned baseline | Body text 10 pt

## 1. Architecture Intent

OncoSentinel is a multimodal cancer intelligence and clinical decision-support platform. Version 2.0 retains the established intelligent-routing, eight-category taxonomy, shared-backbone, category-specific model, RAG, local-LLM, federated-learning, provenance, and safe-failure principles, while adding five research-critical capabilities:

1. uncertainty quantification,
2. clinically grounded concept-based explainability,
3. longitudinal patient modeling,
4. fairness evaluation, and
5. clinical outcome measurement.

The architecture is intentionally research-oriented. It distinguishes technical capability from evidence of clinical benefit: a subsystem can be implemented before it is considered clinically validated. This distinction follows the reviewed literature, where high predictive performance, federated generalizability, explainability metrics, and end-to-end phenotyping still require prospective evidence of clinical utility [Kourou et al., 2015; Pati et al., 2022; Zhang et al., 2023; Sangwan, 2024; Shyr et al., 2026].

## 2. Canonical Architecture

```
                 USER / CLINICIAN / RESEARCHER
                              |
                              v
                  +-----------------------+
                  | Secure API / UI Layer |
                  +-----------------------+
                              |
                              v
                +----------------------------+
                |        Input Gateway       |
                |   PDF / Image / Text / Mix |
                +----------------------------+
                              |
                              v
                +----------------------------+
                |    Content Understanding   |
                |  OCR | Page/Image parsing  |
                |  Modality + Quality checks |
                +----------------------------+
                              |
                              v
        +-----------------------------------------+
        |  Intent / Relevance / Safety Router     |
        |  Cancer relevance | modality | phase    |
        |  category | quality | capability fit    |
        +-----------------------------------------+
                              |
        +---------------------+----------------------+
        |                     |                      |
        v                     v                      v
+----------------+  +--------------------+  +---------------------+
| ML Orchestrator|  | RAG / Knowledge    |  | Longitudinal Engine |
+----------------+  +--------------------+  +---------------------+
        |                     |                      |
        v                     v                      v
+----------------+  +--------------------+  +---------------------+
| Shared Backbone|  | Vector DB / KG     |  | Patient Timeline    |
| + 8 Category   |  | evidence retrieval |  | trends / events     |
| Heads          |  | reranking          |  | treatment/response  |
+----------------+  +--------------------+  +---------------------+
        |                     |                      |
        +----------+----------+----------------------+
                   |
                   v
+------------------------------------------------------+
|        TRUST / RESEARCH SAFETY FABRIC                |
|  Uncertainty + OOD | Fairness | Provenance | Audit   |
|  Concept-based XAI | contradiction | versioning      |
+------------------------------------------------------+
                   |
                   v
+------------------------------------------------------+
| LOCAL LLM / GROUNDED REASONING / REPORT GENERATION   |
+------------------------------------------------------+
                   |
                   v
+------------------------------------------------------+
|        HUMAN-IN-THE-LOOP CLINICAL REVIEW             |
|  accept | reject | edit | request evidence | abstain  |
+------------------------------------------------------+
                   |
                   v
+------------------------------------------------------+
| CLINICAL OUTCOME / QI / RESEARCH EVALUATION LAYER    |
| diagnostic accuracy | time-to-diagnosis | workload   |
| treatment agreement | safety events | subgroup gaps  |
+------------------------------------------------------+
                   |
                   v
+------------------------------------------------------+
|   MLOps / Federated Coordinator / Monitoring         |
|   drift | retraining | model registry | rollback     |
+------------------------------------------------------+
```

## 3. New v2.0 Research Layers

| Capability | Purpose | Primary outputs | Research gap addressed |
|---|---|---|---|
| Uncertainty Quantification | Estimate predictive and evidence uncertainty and trigger safe abstention/escalation. | confidence, calibrated probability, uncertainty type, OOD score, abstain decision | Methodological + theoretical + safety |
| Clinically Grounded Concept-based Explainability | Translate model evidence into clinically meaningful concepts and supporting evidence. | concepts, regions/features, supporting evidence, counter-evidence, explanation fidelity | Theoretical + practical |
| Longitudinal Patient Modeling | Represent disease and treatment trajectories over time. | patient timeline, trend features, response trajectory, recurrence/progression indicators | Theoretical + empirical |
| Fairness & Bias Evaluation | Measure subgroup performance and detect harmful disparities. | subgroup metrics, calibration gaps, equalized error indicators, bias reports | Empirical + practical |
| Clinical Outcome Measurement | Measure whether AI assistance improves real clinical work and outcomes. | diagnostic accuracy, time-to-diagnosis, workload, decision agreement, safety events | Practical/clinical translation |

## 4. Uncertainty Quantification Architecture

Uncertainty is a first-class decision layer, not a cosmetic confidence number. The system should distinguish at least **predictive uncertainty, data/input uncertainty, evidence uncertainty, and out-of-distribution (OOD) uncertainty**.

```
Prediction -> Calibration -> Uncertainty Aggregator -> OOD Detector
                                                          |
                                           +--------------+-------------+
                                           |              |             |
                                         PASS          REVIEW        ABSTAIN
                                           |              |             |
                                           v              v             v
                                        Result        Clinician     No-grounded /
                                                       review      evidence request
```

- Calibration methods should be benchmarked per category and modality rather than assuming global calibration.
- The uncertainty record must be stored with the model version, threshold policy, calibration dataset version, and decision route.
- High uncertainty must be able to force human review or a safe refusal even when the top-1 prediction is available.
- Uncertainty thresholds must be configurable and versioned rather than hard-coded.

## 5. Clinically Grounded Concept-based Explainability

The explainability layer is expanded from generic post-hoc attribution to a concept-based evidence narrative. Pixel/feature attribution remains available for technical auditing, but clinical explanations must map evidence to domain concepts that clinicians recognize.

```
Model output
   |
   +--> Attribution / localization
   +--> Concept extraction / mapping
   +--> Guideline / evidence linking
   +--> Counter-evidence identification
   +--> Clinical explanation generator
   +--> Fidelity + robustness + usefulness evaluation
```

**Output:** What -> Where -> Why -> Supporting evidence -> Contradicting evidence -> Confidence

## 6. Longitudinal Patient Modeling

Cancer is a time-dependent process. The platform therefore maintains a versioned patient timeline that can connect historical diagnoses, imaging, pathology, laboratory values, treatments, adverse events, response assessments, recurrence/progression events, and follow-up data. The system should never overwrite historical facts; it appends time-stamped events with source provenance.

| Timeline domain | Example data | Modeling use |
|---|---|---|
| Diagnosis | disease, subtype, stage, date | baseline state |
| Imaging | serial scans, lesion measurements, radiomics | response/progression |
| Pathology | histology, grade, biomarkers | disease characterization |
| Labs | serial biomarkers, blood counts | trend/context features |
| Treatment | surgery, radiation, drugs, dates | treatment-response relationship |
| Outcomes | response, recurrence, survival/follow-up | prognostic and clinical evaluation |

## 7. Fairness and Bias Architecture

```
Protected / operational subgroups
        |
        v
Performance evaluator
   -> sensitivity / specificity / F1 / AUC
   -> calibration
   -> false-negative / false-positive rates
   -> referral / abstention rates
   -> uncertainty distribution
        |
        v
Fairness report + mitigation recommendation
        |
        +--> retraining / reweighting / threshold policy / data collection
```

Fairness evaluation must be performed by disease category and modality and should report both overall and subgroup metrics. Demographic or protected attributes must be handled under the applicable governance policy; where they cannot legally or ethically be used for inference, they may still be held in secure evaluation workflows for bias auditing when permitted.

## 8. Clinical Outcome Measurement Layer

| Outcome domain | Core metrics | Study phase |
|---|---|---|
| Model validity | AUC, sensitivity, specificity, F1, calibration, Dice where applicable | Retrospective |
| Generalization | unseen-site, temporal, cross-population performance | External validation |
| Clinical workflow | time-to-diagnosis, time-to-decision, workload, override rate | Prospective pilot |
| Decision quality | clinician-AI agreement, appropriate escalation, unsafe miss rate | Prospective comparative |
| Patient-relevant outcomes | downstream care metrics appropriate to study design | Controlled/clinical study |
| Safety | critical error rate, hallucination/grounding failures, abstention failures | All phases |

## 9. Federated Learning and Continuous Learning

Federated learning remains the privacy-preserving training backbone. Version 2.0 adds a controlled continuous-learning loop:

**site updates -> secure aggregation -> validation gates -> subgroup/fairness checks -> uncertainty/calibration checks -> approval -> model registry -> staged deployment -> drift monitoring -> rollback if required.**

Pati et al. show the value of geographically distributed data and explicit unseen-site validation for generalizability [Pati et al., 2022].

## 10. Canonical Data Domains

- **Patient/case domain:** identity surrogate, consent, longitudinal events, clinical context.
- **Imaging domain:** DICOM/NIfTI-derived assets, acquisition metadata, quality metrics, model-ready representations.
- **Text/document domain:** PDF pages, extracted text, tables, figures, clinical notes, provenance.
- **Pathology/omics domain:** pathology reports, histology features, molecular/omics metadata where supported.
- **Knowledge domain:** guideline sources, literature, ontology mappings, evidence chunks, citations.
- **AI domain:** datasets, model versions, calibration artifacts, uncertainty policies, explanation artifacts, evaluation runs.
- **Outcome domain:** clinical workflow outcomes, safety events, subgroup performance, prospective study data.

## 11. Updated End-to-End Workflow

1. Ingest -> validate -> normalize -> secure
2. Understand modality + intent + cancer relevance
3. Route to ML / RAG / local LLM / external verified source
4. If ML: shared backbone -> category head -> prediction
5. Compute calibration + uncertainty + OOD status
6. Generate concept-based clinical explanation + technical attribution
7. Pull longitudinal context when authorized
8. Run contradiction / evidence / safety checks
9. Apply fairness-sensitive monitoring and route policy
10. Present structured result + evidence + uncertainty + explanation
11. Clinician reviews / accepts / edits / rejects / requests evidence
12. Store provenance, outcome, feedback and audit trail
13. Aggregate research metrics and monitor drift
14. Retrain only through approved federated/MLOps gates

## 12. Architecture Principles

- Evidence before generation.
- Routing before execution.
- Specialized models before generic reasoning for supported ML tasks.
- Uncertainty before autonomy.
- Clinical concepts before opaque explanations.
- Longitudinal context before isolated snapshots when authorized.
- Fairness must be measured, not assumed from data diversity.
- Clinical benefit must be measured, not inferred from model accuracy.
- Every model, dataset, policy, explanation, and result is versioned and traceable.
- Safe failure is a designed state, including NO_GROUNDED_ANSWER and ABSTAIN/REVIEW.

## 13. Research Traceability to Reviewed Literature

| Literature finding | OncoSentinel v2.0 response |
|---|---|
| Small datasets and limited external validation [Kourou et al., 2015] | Federated multi-site learning + unseen-site, temporal, and external validation gates. |
| Generalizability enabled by large diverse distributed data [Pati et al., 2022] | Federated coordinator, secure aggregation, local data retention, out-of-site evaluation. |
| Clinical AI remains fragmented and incompletely translated [Zhang et al., 2023] | Workflow-oriented platform with explicit clinical outcomes and staged deployment. |
| Pixel attribution may not match clinical reasoning [Sangwan, 2024] | Concept-based clinical explanations linked to evidence and counter-evidence. |
| End-to-end workflow is more clinically aligned than isolated extraction [Shyr et al., 2026] | Unified input routing, evidence, longitudinal context, explanation, uncertainty, human review, and outcome loop. |

---
---

# PART C — ONCOSENTINEL: PRODUCT REQUIREMENTS DOCUMENT (PRD v2.0)

**PRD v2.0 — Research-gap aligned**
Version 2.0 | Research-gap aligned baseline | Body text 10 pt

## 1. Product Overview

OncoSentinel v2.0 is a multimodal cancer AI and clinical decision-support platform that combines specialized disease models, intelligent routing, evidence-grounded retrieval, a local reasoning layer, federated learning, clinically grounded explainability, longitudinal patient context, uncertainty-aware safety controls, fairness evaluation, and clinical outcome measurement.

## 2. Product Vision

Build a trustworthy oncology intelligence platform that does not merely predict a disease, but determines when a prediction is appropriate, quantifies uncertainty, explains clinically meaningful evidence, incorporates authorized longitudinal context, detects subgroup disparities, supports human review, and measures whether the product improves real clinical work.

## 3. Research Problem

The supplied literature shows a persistent gap between predictive capability and clinical translation.

- Earlier cancer ML reviews identify limited external validation, small samples, and weak clinical adoption [Kourou et al., 2015].
- Federated learning improves access to diverse data and out-of-sample generalization [Pati et al., 2022].
- Explainability research shows that quantitative explanation metrics are needed, while clinically meaningful concept-based explanations remain underdeveloped [Sangwan, 2024].
- End-to-end clinical phenotyping demonstrates the value of workflow alignment but still requires prospective clinical-impact evaluation [Shyr et al., 2026].

OncoSentinel v2.0 is positioned to address these gaps as a product and research platform.

## 4. Product Goals

1. Provide safe multimodal cancer analysis across the authoritative eight-category taxonomy.
2. Prevent irrelevant or unsupported inputs from reaching inappropriate ML models.
3. Use federated learning to support multi-institutional model development without centralized raw patient-data movement.
4. Make uncertainty and abstention first-class product behaviors.
5. Generate clinically grounded, concept-based explanations tied to evidence and counter-evidence.
6. Use longitudinal patient context when authorized and disclose the historical evidence used.
7. Continuously evaluate subgroup fairness and route-level disparities.
8. Measure product value through clinical and workflow outcomes rather than accuracy alone.
9. Maintain complete provenance, versioning, auditability and safe-failure behavior.

## 5. Target Users

| User | Primary value |
|---|---|
| Clinician | Review multimodal evidence, prediction, uncertainty, explanation, longitudinal context and structured reports. |
| Researcher | Run experiments, inspect datasets/models, compare sites, analyze fairness/uncertainty and outcomes. |
| Clinical study reviewer | Review endpoint definitions, adjudication, safety signals and subgroup results. |
| Administrator | Manage access, models, datasets, governance, deployment and audit. |
| Analyst | Monitor operational, model, fairness, drift and outcome dashboards. |
| Auditor | Inspect provenance, decisions, evidence, model versions and safety trails. |

## 6. Product Principles

- Evidence before generation.
- Routing before execution.
- Uncertainty before autonomy.
- Clinical concepts before opaque explanations.
- Longitudinal context before isolated snapshots when authorized.
- Fairness must be measured, not assumed.
- Clinical impact must be measured, not inferred from model accuracy.
- Safe failure is a product feature.
- Version everything: data, models, prompts, calibration, explanation policies, thresholds and evaluation studies.

## 7. Core User Journeys

### 7.1 Multimodal image analysis
Upload image/PDF -> validate -> modality/quality detection -> relevance gate -> disease category -> model head -> calibrated prediction -> uncertainty/OOD -> longitudinal context -> concept-based explanation -> evidence verification -> clinician review -> report -> outcome capture.

### 7.2 Document knowledge analysis
Upload PDF -> validate -> extract text/pages/images -> intent classification -> RAG -> vector search -> rerank -> evidence check -> local LLM -> citation/provenance -> verifier -> answer/report.

### 7.3 Longitudinal case review
Open case -> render timeline -> select relevant episodes -> model/reasoning uses authorized history -> show timepoints influencing result -> clinician review -> update timeline/outcome.

### 7.4 Uncertain result
Prediction -> uncertainty/OOD -> if above threshold: review or abstain -> present reason for uncertainty -> request additional evidence when possible -> no forced diagnosis.

### 7.5 Fairness dashboard
Model release -> subgroup evaluation -> compare performance/calibration/error/abstention -> review disparities -> mitigation decision -> approval gate or hold release.

### 7.6 Clinical outcome study
Prospective study enrollment -> baseline workflow -> AI-assisted workflow -> timestamped decisions -> clinician actions -> endpoint collection -> adjudication -> subgroup analysis -> final study report.

## 8. Product Feature Set

| Area | Features |
|---|---|
| Core AI | 8 category heads, shared backbone, intelligent routing, multimodal ingestion, model registry |
| Safety | uncertainty quantification, calibration, OOD detection, abstention, safe-failure states |
| Clinical XAI | concept extraction, evidence linking, counter-evidence, technical attribution, explanation evaluation |
| Longitudinal | timeline, event provenance, trend features, treatment-response linkage, temporal integrity |
| Knowledge | Vector DB, knowledge graph, RAG, reranking, evidence scoring, citation grounding |
| Privacy/Federation | federated coordinator, secure aggregation, local training, privacy controls, node governance |
| Fairness | subgroup metrics, calibration gap analysis, error disparity reports, release gates |
| Clinical research | external validation, prospective pilots, outcome capture, comparative evaluation |
| Platform | RBAC, cases, reports, audit, monitoring, dashboards, CI/CD, deployment, rollback |

## 9. Product Differentiation

The differentiator is not the number of models. It is the coordinated decision fabric that determines which capability should execute, how certain the result is, how the result can be explained clinically, how longitudinal context changes interpretation, whether performance is equitable, and whether the system improves the workflow.

## 10. Updated Product Roadmap

| Phase | Product milestone | Major deliverables |
|---|---|---|
| 1 | Research-safe ML MVP | Breast + Kidney; multimodal ingestion; routing; calibration/uncertainty baseline; model registry; external-validation harness |
| 2 | Multi-Cancer Engine | All 8 categories; authoritative taxonomy; category heads; fairness evaluation skeleton; timeline data model |
| 3 | Clinical Intelligence | RAG/KG; local LLM; concept-based XAI; longitudinal review; evidence verifier; reports |
| 4 | Federated Trust Layer | Federated coordinator; secure aggregation; drift monitoring; continual-learning gates; fairness/calibration release controls |
| 5 | Clinical Evaluation | Prospective pilot; outcome capture; comparative workflow study; clinician usability/trust evaluation; hospital integration |

## 11. MVP Definition v2.0

The first research-grade MVP is not only "prediction works". For a supported Breast or Kidney case, the platform must validate input quality, route correctly, provide a calibrated prediction, quantify uncertainty, generate a basic clinically grounded explanation, store provenance, and support safe clinician review.

## 12. Success Metrics

| Metric group | Example metrics |
|---|---|
| Model | AUC, sensitivity, specificity, F1, Dice, calibration error |
| Uncertainty | selective risk, abstention precision, OOD detection AUROC where appropriate, calibration |
| Explainability | faithfulness, robustness, localization, clinician usefulness, agreement with clinical concepts |
| Longitudinal | event retrieval accuracy, timeline integrity, temporal leakage rate, trajectory prediction metrics |
| Fairness | subgroup sensitivity/specificity, calibration gap, FNR/FPR gap, abstention gap |
| Workflow | time-to-diagnosis, time-to-review, workload, completion rate, override rate |
| Clinical | decision quality, unsafe miss rate, appropriate escalation, study-specific downstream outcomes |
| Platform | availability, latency, error rate, retrieval precision/recall proxies, audit completeness |

## 13. Product Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Overconfident wrong prediction | calibration + uncertainty + OOD + abstention + human review |
| Clinically misleading explanation | concept-based XAI + evidence linking + clinician evaluation |
| Historical context causing leakage | timestamp-aware datasets and temporal split controls |
| Subgroup performance disparity | mandatory fairness evaluation and release gate |
| Model drift | drift detection + scheduled and event-triggered evaluation + rollback |
| Clinical value not demonstrated | prospective outcome study and comparative workflow evaluation |
| Hallucinated knowledge response | evidence gate + grounded local LLM + verifier + NO_GROUNDED_ANSWER |
| Privacy exposure | federated/local processing, access controls, minimization, audit, approved privacy mechanisms |

## 14. Definition of Done — Research-grade Product

- All eight categories are versioned and routable through the authoritative taxonomy.
- Supported multimodal input flows are validated and safe-fail paths are operational.
- Predictions expose uncertainty, calibration state and OOD status.
- Clinical explanations are concept-based, evidence-linked and quantitatively evaluated.
- Longitudinal timelines are immutable, provenance-linked and usable in authorized reasoning.
- Fairness evaluation is mandatory before production-oriented model promotion.
- Federated learning and multi-site external validation are operational at research scale.
- Clinical outcomes can be captured under a defined prospective study protocol.
- Monitoring includes performance, drift, fairness, uncertainty, safety and operational metrics.
- Every production-oriented model release has dataset/model/provenance/evaluation/rollback artifacts.

## 15. Updated Product Positioning

OncoSentinel should be positioned as a multimodal cancer AI and clinical decision-support research platform that combines specialized ML, evidence-grounded knowledge retrieval, controlled AI assistance, federated learning, uncertainty-aware safety, clinically grounded explainability, longitudinal reasoning, fairness evaluation, and clinical outcome measurement. Its promise is not autonomous medical authority; it is an auditable, evidence-grounded and uncertainty-aware decision-support fabric that can be scientifically evaluated.

## 16. Literature References

- Kourou, K., Exarchos, T. P., Exarchos, K. P., Karamouzis, M. V., & Fotiadis, D. I. (2015). Machine learning applications in cancer prognosis and prediction.
- Pati, S., et al. (2022). Federated Learning Enables Big Data for Rare Cancer Boundary Detection.
- Zhang, B., Shi, H., & Wang, H. (2023). Machine Learning and AI in Cancer Prognosis, Prediction, and Treatment Selection: A Critical Approach.
- Sangwan, H. (2024). Quantifying Explainable AI Methods in Medical Diagnosis: A Study in Skin Cancer.
- Shyr, C., Hu, Y., Tinker, R. J., et al. (2026). An artificial intelligence framework for end-to-end rare disease phenotyping from clinical notes using large language models.

---
---

# PART D — RESEARCH GAP ANALYSIS

**Research Gap Analysis: Artificial Intelligence, Machine Learning, Federated Learning, Large Language Models, and Explainable AI in Cancer and Rare-Disease Diagnosis**

## 1. Scope and Overview of the Reviewed Literature

This research-gap analysis synthesizes five uploaded papers addressing complementary aspects of artificial intelligence (AI) and machine learning (ML) in oncology and rare-disease diagnosis:

1. Kourou et al. (2015) — Machine learning applications in cancer prognosis and prediction
2. Pati et al. (2022) — Federated Learning Enables Big Data for Rare Cancer Boundary Detection
3. Zhang, Shi, and Wang (2023) — Machine Learning and AI in Cancer Prognosis, Prediction, and Treatment Selection: A Critical Approach
4. Sangwan (2024) — Quantifying Explainable AI Methods in Medical Diagnosis: A Study in Skin Cancer
5. Shyr et al. (2026) — An artificial intelligence framework for end-to-end rare disease phenotyping from clinical notes using large language models

Collectively, the literature demonstrates a clear progression from conventional predictive ML toward distributed learning, multimodal clinical AI, explainability, and end-to-end workflow-oriented systems. However, this progression has not yet produced a unified framework that simultaneously addresses **generalizability, heterogeneous multimodal data, privacy-preserving learning, explainability, clinical workflow integration, prospective validation, and applicability across both common and rare diseases**.

The central research gap is therefore not simply the absence of more accurate predictive models. Rather, the major unresolved problem is the development and prospective validation of clinically deployable, generalizable, interpretable, privacy-preserving, multimodal AI systems that can translate heterogeneous patient data into actionable decision support across diverse cancer and rare-disease contexts.

## 2. Literature Synthesis

### 2.1 Thematic Cluster I: Conventional ML for Cancer Prediction and Prognosis

#### Kourou et al. (2015)

Kourou et al. provide an early systematic overview of ML applications in cancer susceptibility, recurrence, and survival prediction. The review examines methods including artificial neural networks, Bayesian networks, support vector machines, decision trees, and semi-supervised learning, with inputs spanning clinical, genomic, histological, demographic, and imaging data. The authors identify a strong trend toward integrating heterogeneous data sources.

The review concludes that ML can improve prediction of cancer susceptibility, recurrence, and survival, but repeatedly emphasizes insufficient external validation, small datasets, unstable models, heterogeneous data challenges, and limited translation into clinical practice. The review specifically notes that small sample sizes relative to feature dimensionality can lead to biased or unstable models and impair generalizability.

Kourou et al. also argue that appropriate statistical treatment of heterogeneous datasets and the construction of broader public cancer databases are necessary for more valid predictive modeling and integrated clinical decision-making.

#### Zhang, Shi, and Wang (2023)

Zhang et al. extend this perspective by reviewing contemporary applications of AI and ML in cancer diagnosis, prognosis, risk assessment, and treatment selection. Their review covers a wide range of cancers and emphasizes the potential of data-driven methods to improve diagnostic accuracy, prognosis estimation, clinical workflow, and treatment decisions.

At the same time, the authors characterize clinical AI as remaining relatively immature, noting that only a limited number of AI solutions had achieved real-world authorization or adoption at the time of publication. The review also identifies difficulties arising from inaccessible medical data, heterogeneous data sources, normalization requirements, and the interpretability problem associated with complex AI systems.

#### Synthesis of Cluster I

The two reviews establish the fundamental capability of ML for cancer prediction but reveal a persistent implementation paradox: **predictive capability has advanced faster than clinical validity and deployment readiness.** The literature demonstrates that increasingly sophisticated algorithms do not automatically solve issues of sample adequacy, dataset shift, external validation, data interoperability, interpretability, or clinical integration.

### 2.2 Thematic Cluster II: Federated Learning and Cross-Institutional Generalizability

#### Pati et al. (2022)

Pati et al. address one of the limitations identified in earlier cancer-ML research: insufficiently diverse training data. Their study uses federated learning (FL) to train a glioblastoma tumor-boundary segmentation model across **71 geographically distinct healthcare institutions spanning six continents, involving 6,314 patients and 25,256 MRI scans**. The system uses a **3D-ResUNet** architecture and enables participating institutions to retain their data locally while sharing model updates rather than patient-level data.

The study incorporated both local validation and genuinely unseen out-of-sample sites. The final consensus model produced substantial improvements over the initial model, including improvements of **27%, 33%, and 16%** for different tumor sub-compartments on local validation data and **15%, 27%, and 16%** on unseen data.

This study is particularly important because it provides empirical evidence that geographically distributed and heterogeneous data can improve generalizability while avoiding centralized transfer of sensitive medical data. Its **590-case** out-of-sample cohort was deliberately excluded from training, creating a stronger test of generalization than a conventional random train/test partition.

#### Synthesis of Cluster II

Pati et al. demonstrate that federated learning can mitigate an important weakness of conventional ML: restricted access to heterogeneous multi-institutional datasets. However, the study remains focused on a specific imaging task in glioblastoma, rather than an end-to-end clinical decision-support framework. Consequently, FL successfully addresses the data-distribution and privacy dimension of the research problem, but not the complete spectrum of clinical AI requirements.

### 2.3 Thematic Cluster III: Explainable AI and Trustworthy Medical AI

#### Sangwan (2024)

Sangwan investigates explainability specifically within skin-cancer diagnosis. The study uses the **HAM10000** dataset containing **10,015 dermoscopic images from seven lesion categories** and compares multiple deep-learning architectures, including custom CNNs, DenseNet, MobileNet, and ResNet. **SHAP, LIME, and Integrated Gradients** are then applied to generate post-hoc explanations.

The principal contribution is methodological: rather than relying only on visual inspection of attribution maps, the study quantitatively evaluates explanations using measures associated with **faithfulness, robustness, complexity, localization, monotonicity, stability, and input-reduction fidelity**.

The study nevertheless identifies an important conceptual limitation. Pixel-level explanations may not correspond to the semantic features clinicians actually use when diagnosing skin lesions. The authors therefore recommend moving toward segmentation-based or concept-based explanations and incorporating expert user studies and domain-specific diagnostic criteria. They also explicitly identify generalizability to diverse datasets and continuous adaptation as important future directions.

#### Synthesis of Cluster III

This work shifts the research question from "Is the model accurate?" to "Can we quantitatively evaluate why the model makes its prediction, and is that explanation clinically meaningful?" However, explainability remains largely evaluated as a computational property rather than as a demonstrated contributor to improved clinician decisions or patient outcomes.

### 2.4 Thematic Cluster IV: End-to-End LLM-Based Clinical Phenotyping

#### Shyr et al. (2026)

Shyr et al. represent a newer generation of clinical AI research through **RARE-PHENIX**, an end-to-end framework for rare-disease phenotyping from unstructured clinical notes. Rather than treating phenotype extraction, ontology normalization, and diagnostic prioritization as isolated tasks, the framework integrates three sequential stages:

1. LLM-based phenotype extraction,
2. ontology-grounded standardization to Human Phenotype Ontology (HPO) terms through retrieval-augmented generation, and
3. supervised ranking of diagnostically informative phenotypes.

The study trained the framework using **2,671 patients from 11 Undiagnosed Diseases Network sites** and externally evaluated it using **16,357 real-world clinical notes from Vanderbilt University Medical Center**. The framework outperformed PhenoBERT, with an ontology-based similarity of **0.70 versus 0.58** in the reported end-to-end evaluation.

Importantly, the paper identifies several limitations even after achieving external validation:

- The UDN cohort is enriched for complex multisystem cases.
- Large 70-billion-parameter models may be difficult to deploy in resource-constrained environments.
- Clinician-curated HPO terms may be incomplete or variable between clinicians.
- Retrospective model performance does not establish improvement in diagnostic accuracy, time-to-diagnosis, or clinician workload.

The systematic error analysis further shows that many errors originate not from simple extraction failure but from linguistic variability, indirect descriptions in clinical notes, undocumented physical findings, and ontology-granularity differences.

#### Synthesis of Cluster IV

RARE-PHENIX demonstrates a major conceptual advance: **clinical AI should model the workflow that clinicians actually perform rather than optimizing a single computational subtask.** Nevertheless, the work remains concentrated on rare-disease phenotyping from clinical text and does not yet unify multimodal cancer imaging, clinical variables, treatment history, molecular information, federated learning, and clinically validated explanations within one architecture.

## 3. Cross-Paper Synthesis

Across the five papers, six broad developments can be identified.

**First,** predictive performance is no longer the only major research objective. Earlier cancer-ML literature concentrated primarily on prediction accuracy, whereas newer research increasingly considers generalizability, privacy, explainability, and workflow alignment.

**Second,** data heterogeneity is both an asset and a major methodological problem. Kourou et al. identify the value of combining clinical, genomic, imaging, and histological information but also highlight validation and dataset limitations. Pati et al. show that geographically distributed data can improve performance, while Zhang et al. describe data normalization and interoperability as continuing barriers.

**Third,** generalizability remains a central unresolved problem, although the meaning of generalizability has evolved. Earlier studies frequently lacked external validation; Pati et al. address cross-site generalization explicitly through federated and out-of-sample validation, while Shyr et al. demonstrate external validation across institutions. Yet both remain disease- or modality-specific.

**Fourth,** explainability has become increasingly quantitative but remains insufficiently clinical. Sangwan demonstrates that explanation methods can be objectively evaluated, but also notes that computationally faithful explanations may not necessarily correspond to clinically meaningful concepts.

**Fifth,** workflow integration is emerging but fragmented. RARE-PHENIX is explicitly designed around the clinical phenotyping workflow, whereas much cancer AI research still concentrates on individual prediction or classification tasks.

**Sixth,** there remains a substantial distinction between retrospective technical validity and demonstrated clinical utility. This gap is explicit in both the rare-disease and cancer literatures. Shyr et al. state that prospective evaluation is required to establish effects on diagnostic accuracy, time to diagnosis, and clinician workload. Zhang et al. similarly note that only a limited number of AI applications had reached real-world use.

## 4. Research Gap Identification

### 4.1 Methodological Gaps

#### 4.1.1 Insufficient integration of validation paradigms

Older cancer-ML studies commonly rely on internal cross-validation or relatively small datasets, creating a risk that apparent performance reflects dataset-specific characteristics rather than genuine clinical generalization. Kourou et al. explicitly identify lack of external validation, small samples, and inadequate validation as recurring problems.

More recent work demonstrates stronger validation, but the methods remain fragmented. Pati et al. employ geographically unseen sites, while Shyr et al. use a separate institutional external cohort. A systematic framework combining **patient-level, temporal, institution-level, geographic, demographic, and prospective validation** remains underdeveloped.

#### 4.1.2 Limited multimodal methodological integration

The reviewed research considers different modalities—MRI, dermoscopic images, clinical notes, clinical variables, genomic information—but typically does not integrate these modalities into one validated architecture.

This creates a significant methodological gap because cancer diagnosis and treatment decisions are inherently multimodal. A model that processes only imaging, only clinical text, or only structured clinical variables may miss clinically important relationships that emerge across modalities.

#### 4.1.3 Dataset and annotation limitations

The literature demonstrates that ground truth is not necessarily objective. RARE-PHENIX depends on clinician-curated HPO terms that may be incomplete or subject to inter-clinician variability. Sangwan's work also identifies data diversity as a limitation.

A methodological need therefore exists for **multi-expert annotation protocols, uncertainty-aware labels, adjudication procedures, and explicit modeling of annotation disagreement.**

#### 4.1.4 Computational constraints are insufficiently incorporated into model design

High-performing systems frequently use computationally expensive architectures. Shyr et al. report that the strongest RARE-PHENIX performance was achieved using large 70B-parameter models, which may be impractical in resource-constrained environments.

The literature therefore lacks sufficient comparative work on the trade-off between accuracy, latency, memory consumption, energy requirements, privacy, and clinical usefulness.

### 4.2 Theoretical Gaps

#### 4.2.1 Absence of a unified theory of trustworthy clinical AI

The papers separately address prediction, federated learning, explainability, or workflow alignment. What is missing is an integrated theoretical framework that defines clinical AI quality as a multidimensional construct involving:

> **predictive accuracy + generalizability + uncertainty + explainability + privacy + workflow compatibility + clinical utility.**

Current studies tend to optimize individual dimensions rather than model the interactions among them.

#### 4.2.2 Limited theoretical integration between AI reasoning and clinical reasoning

RARE-PHENIX moves toward clinically aligned workflow modeling, while Sangwan demonstrates that mathematical explanation quality does not necessarily imply clinical meaningfulness. These findings indicate a deeper theoretical question: *What constitutes a clinically valid explanation?*

A future theoretical framework should distinguish between:

- computational explanation,
- causal or mechanistic explanation,
- clinically interpretable explanation,
- actionable explanation.

These concepts are often conflated in medical AI.

#### 4.2.3 Insufficient theory for adaptive, longitudinal clinical AI

Most reviewed systems treat prediction as relatively static. However, cancer patients generate longitudinal data through repeated imaging, laboratory tests, clinical notes, pathology, treatment response, and disease progression.

The literature provides insufficient theoretical development regarding continual learning, temporal adaptation, concept drift, model updating, and longitudinal uncertainty in real clinical environments.

### 4.3 Empirical and Contextual Gaps

#### 4.3.1 Underrepresentation of rare cancers and uncommon disease subtypes

Although Pati et al. specifically target glioblastoma and Shyr et al. address rare diseases, most of the wider cancer-AI literature remains concentrated in more data-rich disease areas.

Kourou et al. already identified limitations caused by restricted disease-specific datasets and noted that some predictive models could not generalize across cancer types.

A major empirical opportunity therefore exists in developing models capable of learning across multiple cancer types while preserving disease-specific distinctions and rare-subtype sensitivity.

#### 4.3.2 Geographic and demographic representativeness

Pati et al. substantially improve geographic diversity through 71 institutions across six continents. However, geographic participation alone does not guarantee demographic equity.

The reviewed literature provides insufficient evidence concerning performance variation across socioeconomic groups, ethnic populations, age groups, healthcare systems, resource levels, and demographic subgroups.

#### 4.3.3 Limited prospective clinical evidence

This is one of the strongest gaps across all five papers.

Technical validation is relatively well established, but evidence that AI changes real clinical outcomes remains limited. Shyr et al. explicitly identify the need for prospective evaluation of diagnostic accuracy, time-to-diagnosis, and clinician workload. Zhang et al. similarly describe the limited real-world adoption of AI systems.

Thus, the literature lacks sufficient prospective, randomized, workflow-aware evaluations measuring clinical effectiveness rather than merely model performance.

### 4.4 Practical and Applied Gaps

#### 4.4.1 Disconnection between model output and clinical action

Most studies report a prediction, classification, segmentation, ranked phenotype, or explanation. Much less attention is given to how that output changes the clinician's next action.

A clinically useful system should answer not only:

> "What is the predicted condition?"

but also:

> "How certain is the prediction, what evidence supports it, what additional evidence is needed, and how should the result be incorporated into the clinical workflow?"

#### 4.4.2 Limited human-in-the-loop evaluation

RARE-PHENIX explicitly identifies human-in-the-loop diagnosis as a potential application, but prospective evaluation of clinician interaction remains necessary.

Similarly, Sangwan recommends healthcare-professional user studies to determine whether explanations genuinely address clinical needs.

This indicates a substantial applied gap in human-AI interaction design, clinician trust calibration, cognitive workload, and decision-support effectiveness.

#### 4.4.3 Lack of integrated privacy-preserving clinical infrastructure

Pati et al. demonstrate that federated learning can allow institutions to collaborate without centralizing patient data. However, federated learning is primarily evaluated as a training strategy rather than as one component of a complete clinical architecture integrating multimodal data, LLMs, vector retrieval, explainability, uncertainty estimation, model routing, and deployment governance.

#### 4.4.4 Limited resource-aware deployment

Clinical deployment frequently occurs under computational and infrastructural constraints. Pati et al. explicitly consider low-resource inference and report runtime optimizations through quantization, while Shyr et al. identify very large LLMs as difficult to deploy in constrained environments.

However, systematic comparisons between cloud-based, institutional, edge, and hybrid deployment architectures remain limited.

## 5. Consolidated Research-Gap Matrix

| Gap Category | Evidence from Literature | Unresolved Problem | Research Opportunity |
|---|---|---|---|
| Methodological | Small datasets and inadequate external validation in earlier cancer ML studies | Performance may not generalize across institutions or populations | Multi-level external, temporal, geographic, and prospective validation |
| Methodological | Heterogeneous clinical, genomic, imaging, and text data | Modalities are often analyzed separately | Unified multimodal learning architecture |
| Methodological | Clinician-curated labels may be incomplete or variable | Ground truth uncertainty is under-modeled | Multi-expert annotation and uncertainty-aware supervision |
| Theoretical | Prediction, explainability, privacy, and workflow treated separately | No unified model of trustworthy clinical AI | Integrated trustworthy-AI framework |
| Theoretical | Pixel-level explanations may not map to clinical concepts | Computational explanation ≠ clinical explanation | Concept-based and clinically grounded explainability |
| Theoretical | Mostly static prediction models | Insufficient treatment of temporal change | Longitudinal and continual-learning framework |
| Empirical | Rare diseases and rare cancer subtypes remain data limited | Underrepresentation of uncommon conditions | Cross-disease and rare-subtype learning |
| Empirical | Geographic diversity does not necessarily establish demographic fairness | Unequal performance may remain hidden | Subgroup fairness and healthcare-system evaluation |
| Practical | Retrospective evaluation dominates | Clinical outcome benefit remains uncertain | Prospective workflow and outcome studies |
| Practical | AI outputs are often isolated predictions | Limited connection to subsequent clinical actions | Human-in-the-loop decision-support architecture |
| Practical | Large models can be computationally demanding | Deployment barriers in low-resource settings | Efficient, adaptive, resource-aware AI |

## 6. Overall Research Gap

The reviewed literature demonstrates that the principal limitation of contemporary clinical AI is no longer the absence of capable algorithms. Instead, the field lacks a unified, clinically validated architecture capable of combining heterogeneous data while maintaining generalizability, privacy, interpretability, uncertainty awareness, computational efficiency, and workflow compatibility.

The literature has progressively solved individual parts of this problem:

- **Kourou et al.** established the potential of ML for cancer prediction but emphasized sample-size and validation limitations.
- **Pati et al.** demonstrated that federated learning can enable large-scale geographically diverse training and stronger out-of-sample generalization.
- **Sangwan** introduced quantitative evaluation of explanation quality while recognizing that explanations must eventually become clinically meaningful.
- **Shyr et al.** demonstrated that modeling an end-to-end clinical workflow can outperform isolated phenotyping approaches while identifying the need for prospective clinical evaluation.

Consequently, the most significant opportunity is to move from task-specific AI models toward a generalizable clinical intelligence framework capable of dynamically selecting and integrating models according to patient data type, disease context, evidence availability, uncertainty, and clinical requirements.

## 7. Proposed Research Agenda

### Research Question 1: Multimodal Clinical Intelligence

**RQ1:** Can a unified multimodal AI architecture integrating medical images, clinical notes, structured clinical variables, pathology, and molecular information improve diagnostic and prognostic performance compared with modality-specific models across multiple cancer types and rare cancer subtypes?

**Hypothesis H1:** A multimodal architecture will demonstrate superior discrimination, calibration, robustness, and clinical utility compared with single-modality models, particularly when complementary information is distributed across different clinical data sources.

### Research Question 2: Federated Multimodal Learning

**RQ2:** Can privacy-preserving federated learning improve the cross-institutional generalizability of multimodal cancer AI models while maintaining clinically acceptable computational and communication costs?

**Hypothesis H2:** Federated training across heterogeneous institutions will produce models with significantly stronger out-of-site generalization than single-institution training while preserving data locality and reducing the need for centralized patient-level data aggregation.

This research directly extends the multi-institutional success demonstrated by Pati et al. from imaging segmentation toward multimodal clinical intelligence.

### Research Question 3: Clinically Grounded Explainability

**RQ3:** Do concept-based, clinically grounded explanations improve clinician trust, diagnostic accuracy, and decision efficiency more effectively than conventional pixel- or feature-attribution explanations?

**Hypothesis H3:** Explanations expressed in clinically meaningful concepts and linked to supporting evidence will produce higher clinician comprehension, appropriate reliance, and decision accuracy than conventional post-hoc attribution maps.

This directly addresses Sangwan's observation that pixel-level explanations may fail to correspond to clinically meaningful diagnostic reasoning.

### Research Question 4: End-to-End Clinical Workflow

**RQ4:** Can an end-to-end AI pipeline that performs input interpretation, evidence extraction, disease-specific model routing, knowledge retrieval, uncertainty assessment, explanation generation, and human review reduce diagnostic time and clinician workload without compromising diagnostic safety?

**Hypothesis H4:** Workflow-oriented AI will provide greater clinical utility than isolated prediction models because its outputs are directly connected to the sequence of decisions clinicians must make.

This research builds conceptually on RARE-PHENIX, which demonstrated the value of integrating extraction, standardization, and prioritization rather than treating these tasks independently.

### Research Question 5: Prospective Clinical Utility and Adaptive Learning

**RQ5:** Does prospective deployment of an uncertainty-aware, continuously monitored clinical AI system improve diagnostic accuracy, time-to-diagnosis, treatment decision quality, and clinician workload across diverse healthcare environments?

**Hypothesis H5:** Prospective, continuously monitored AI assistance will improve clinical outcomes relative to conventional workflows, provided that model uncertainty, subgroup performance, data drift, and clinician override behavior are explicitly monitored.

This question addresses the strongest remaining translational gap identified by the literature: retrospective performance does not establish real-world clinical benefit. Shyr et al. explicitly call for prospective studies examining diagnostic accuracy, time to diagnosis, gene/variant prioritization, and clinician workflow.

## 8. Recommended Conceptual Direction for Future Research

The literature supports a future research architecture organized around six interacting layers:

**Data Layer → Multimodal Learning Layer → Federated/Privacy Layer → Knowledge and Reasoning Layer → Explainability and Uncertainty Layer → Human Clinical Decision Layer**

Such an architecture would address limitations identified across the five papers rather than solving only one isolated problem.

- The **Data Layer** should support clinical notes, imaging, pathology, structured records, laboratory data, and molecular information.
- The **Multimodal Learning Layer** should dynamically combine disease-specific prediction models rather than assuming one model is optimal for every input.
- The **Federated/Privacy Layer** should enable institutions to collaboratively improve models without requiring centralized patient-level data, extending the principle demonstrated by Pati et al.
- The **Knowledge and Reasoning Layer** should connect model outputs with structured biomedical knowledge, ontologies, guidelines, and evidence resources. RARE-PHENIX provides a useful precedent for ontology-grounded processing and retrieval-based standardization.
- The **Explainability and Uncertainty Layer** should provide both quantitative explanation evaluation and clinically meaningful evidence presentation, addressing the concerns identified by Sangwan.
- Finally, the **Human Clinical Decision Layer** should explicitly incorporate clinician review, disagreement, confidence, override behavior, and prospective outcome monitoring.

## 9. Final Research Gap Statement

Despite substantial progress in machine learning, federated learning, large language models, and explainable AI for cancer and rare-disease applications, existing research remains fragmented across prediction, privacy, explainability, phenotyping, and workflow integration. There is insufficient evidence for a unified, multimodal, privacy-preserving, clinically interpretable, uncertainty-aware, and prospectively validated AI framework capable of generalizing across institutions, populations, cancer types, and rare disease contexts while producing clinically actionable outputs. Future research should therefore shift from isolated model optimization toward end-to-end clinical AI systems evaluated not only by predictive accuracy but also by external generalizability, fairness, explanation quality, computational efficiency, workflow compatibility, and measurable clinical outcomes.

## 10. Literature Base Used

- Kourou, K., Exarchos, T. P., Exarchos, K. P., Karamouzis, M. V., & Fotiadis, D. I. (2015). Machine learning applications in cancer prognosis and prediction. *Computational and Structural Biotechnology Journal*, 13, 8–17.
- Pati, S., et al. (2022). Federated Learning Enables Big Data for Rare Cancer Boundary Detection. The study evaluates federated learning using data from 71 institutions across six continents and 6,314 glioblastoma patients.
- Zhang, B., Shi, H., & Wang, H. (2023). Machine Learning and AI in Cancer Prognosis, Prediction, and Treatment Selection: A Critical Approach. *Journal of Multidisciplinary Healthcare*, 16, 1779–1791.
- Sangwan, H. (2024). Quantifying Explainable AI Methods in Medical Diagnosis: A Study in Skin Cancer. medRxiv preprint, posted December 10, 2024. The uploaded paper explicitly states that the manuscript had not undergone peer review at the time of posting.
- Shyr, C., Hu, Y., Tinker, R. J., et al. (2026). An artificial intelligence framework for end-to-end rare disease phenotyping from clinical notes using large language models. The study presents and externally validates RARE-PHENIX across UDN and Vanderbilt data.

---

*End of consolidated document.*
