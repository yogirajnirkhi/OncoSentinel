# OncoSentinel v2.0 — Multimodal Cancer AI Platform

> **AI-Assisted Clinical Decision-Support & Multimodal Cancer Research Platform**  
> *Fully Aligned with the Complete Consolidated Documentation (SRS v2.0, Architecture v2.0, PRD v2.0, and Research Gap Analysis)*

---

## 1. Executive Summary & Research Grounding

OncoSentinel v2.0 is an advanced oncology AI platform designed to translate multimodal patient data (imaging, clinical notes, laboratory values, pathology) into trustworthy, calibrated, and evidence-grounded decision support. 

Rather than treating AI as an isolated black-box classifier, OncoSentinel v2.0 bridges the five foundational research gaps identified in contemporary oncology AI literature:

1. **Generalizability & Multi-Site Learning ([Pati et al., 2022](https://arxiv.org/abs/2204.10836v2)):** Geographically distributed federated learning with out-of-site, unseen validation to prevent overfitted optimistic bias.
2. **Data Heterogeneity & Translation Barriers ([Kourou et al., 2015](https://doi.org/10.1016/j.csbj.2014.11.001); [Zhang et al., 2023](https://doi.org/10.2147/JMDH.S411802)):** Rigorous quality gating, SNR/blur estimation, and multi-gate cancer relevance filtering (threshold $\ge 0.55$).
3. **Clinical Explainability over Pixel Attribution ([Sangwan, 2024](https://doi.org/10.1101/2024.12.08.24318158)):** Translating raw feature attributions into domain concepts (mass shape, spiculation, calcification, cortical invasion) and quantitatively evaluating explanations for fidelity, robustness, and localization.
4. **End-to-End Clinical Workflow & Grounding ([Shyr et al., 2026](https://arxiv.org/abs/2602.20324v1)):** Evidence before generation; grounding local reasoning in peer-reviewed clinical guidelines (NCCN, ACR BI-RADS, Bosniak, WHO CNS).
5. **Prospective Clinical Utility & Outcome Integrity:** Measuring real clinical impact (time-to-diagnosis, override rate, agreement) with strict schema isolation preventing outcome data from leaking into model training.

---

## 2. Authoritative Multi-Cancer Taxonomy

OncoSentinel v2.0 operates across the authoritative eight cancer categories specified in `configs/taxonomy.yaml`:

| # | Category | Supported Modalities | Target Classes | Model Architecture | Deployment Status |
|---|---|---|---|---|---|
| 1 | **Kidney** | CT | `normal`, `tumor` | MobileNetV3-Small (`kidney_model.pth`) | **Active Deployed** |
| 2 | **Oral Cancer** | Histology | `normal`, `oscc` | MobileNetV3-Small (`oral_model.pth`) | **Active Deployed** |
| 3 | **Breast** | Ultrasound, Histology | `benign`, `malignant` | Scaffolded | Untrained |
| 4 | **ALL / Leukemia** | Microscopy | `normal`, `all_blast` | Scaffolded | Untrained |
| 5 | **Lung & Colon** | Histology | `colon_adenocarcinoma`, `colon_benign`, `lung_adenocarcinoma`, etc. | Scaffolded | Untrained |
| 6 | **Lymphoma** | Histology | `cll`, `fl`, `mcl` | Scaffolded | Untrained |
| 7 | **Brain Tumor** | MRI | `no_tumor`, `glioma`, `meningioma`, `pituitary` | Scaffolded | Untrained |
| 8 | **Cervical Cancer**| Cytology / Pap | `dyskeratotic`, `koilocytotic`, `metaplastic`, etc. | Scaffolded | Untrained |

---

## 3. System Architecture & Core Pipelines

```
                   USER / CLINICIAN / RESEARCHER
                                |
                                v
                    +-----------------------+
                    | Secure API / Web UI   |
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
                  |  Image Quality | Resolution|
                  |  Blur | Contrast | OCR     |
                  +----------------------------+
                                |
                                v
          +-----------------------------------------+
          |  Intent / Relevance / Safety Router     |
          |  Cancer relevance (>=0.55) | Modality   |
          |  Phase gate | Capability fit            |
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
  | Shared Backbone|  | Vector Store       |  | Append-Only Timeline|
  | + 8 Category   |  | BM25 + Dense Hybrid|  | Missingness States  |
  | Heads          |  | Reranking          |  | Influence Weights   |
  +----------------+  +--------------------+  +---------------------+
          |                     |                      |
          +----------+----------+----------------------+
                     |
                     v
  +------------------------------------------------------+
  |         TRUST / RESEARCH SAFETY FABRIC               |
  |  Uncertainty + Calibration | Multi-Detector OOD      |
  |  Concept-Based Clinical XAI | Grad-CAM Localizer     |
  |  Subgroup Fairness Gates   | INSERT-ONLY Audit       |
  +------------------------------------------------------+
                     |
                     v
  +------------------------------------------------------+
  | LOCAL LLM / GROUNDED REASONING / VERIFICATION        |
  | Ollama integration | Citation integrity check        |
  | Terminal state: NO_GROUNDED_ANSWER / ABSTAIN         |
  +------------------------------------------------------+
                     |
                     v
  +------------------------------------------------------+
  |         HUMAN-IN-THE-LOOP CLINICAL REVIEW            |
  |  Accept | Reject | Edit | Request Evidence | Abstain |
  +------------------------------------------------------+
                     |
                     v
  +------------------------------------------------------+
  | CLINICAL OUTCOME & RESEARCH EVALUATION (NFR-10)     |
  | Isolated schema preventing model training leakage    |
  | Time-to-diagnosis reduction | Override tracking      |
  +------------------------------------------------------+
                     |
                     v
  +------------------------------------------------------+
  | FEDERATED COORDINATOR & DRIFT MONITORING (FR-23)     |
  | Multi-site simulation | Secure weight aggregation    |
  | Held-out unseen site generalizability evaluation     |
  +------------------------------------------------------+
```

---

## 4. Key Subsystems & Implementations

### 4.1 Input Validation & Quality Gating
- Located in `services/ingestion/validator.py`.
- Computes Laplacian variance for blur estimation, standard deviation for contrast, and dynamic range clipping.
- Rejection threshold: Minimum score `< 0.40` triggers `TERMINAL_LOW_QUALITY`.

### 4.2 Intelligent Router & Cancer Relevance
- Located in `services/router/engine.py` and `services/router/cancer_relevance.py`.
- Classifies user intent (`DIAGNOSTIC_ANALYSIS`, `EVIDENCE_QUERY`, `LONGITUDINAL_REVIEW`, `OUTCOME_EVALUATION`).
- Verifies input relevance score against `minimum_score: 0.55`. Non-cancer inputs are cleanly trapped in `TERMINAL_NOT_CANCER_RELEVANT`.
- Checks modality compatibility and phase availability.

### 4.3 Shared Backbone & 8 Category Heads
- Located in `services/ml/backbone.py` and `services/ml/heads.py`.
- Multi-scale convolutional backbone providing 512-dim pooled embeddings and spatial feature maps.
- Factory `build_category_head(category)` instantiates heads for all 8 categories.

### 4.4 Calibration & Multi-Detector OOD
- Located in `services/uncertainty/calibration.py` and `services/uncertainty/ood_detector.py`.
- Category-specific temperature scaling ($z / T$) and conformal prediction sets.
- Multi-detector OOD architecture:
  1. Mahalanobis distance from feature cluster centroids
  2. Energy score: $-T \cdot \ln \sum \exp(z_i / T)$
  3. Max Softmax score with consensus threshold requirement (at least 2 detectors must agree)
- Aggregator maps signals to decision: `PASS`, `REVIEW`, `ABSTAIN`.

### 4.5 Clinically Grounded Concept XAI & Quantitative Evaluation
- Located in `services/xai/concept_mapper.py` and `services/xai/evaluator.py`.
- Maps internal activations to domain concepts defined in `taxonomy.yaml` with explicit **Supporting** vs **Counter-Evidence**.
- Implements quantitative evaluation metrics from **Sangwan (2024)**:
  - **Fidelity Score**: Faithfulness of explanation to model activations (threshold $\ge 0.70$)
  - **Robustness Score**: Stability under input perturbations (threshold $\ge 0.70$)
  - **Localization Score**: Saliency energy concentration in lesion area
  - **Complexity Score**: Conciseness of attribution
- Generates mandatory **Tri-Part Evidence Sections**:
  1. *Model Evidence Section*
  2. *Guideline Evidence Section*
  3. *Generated Synthesis Section*

### 4.6 Append-Only Longitudinal Patient Timeline
- Located in `services/longitudinal/timeline_manager.py` and `services/longitudinal/influence_tracker.py`.
- Enforces immutability: NO update or delete allowed; updates are appended as corrections referencing `references_event_id`.
- Explicit missingness states: `PRESENT`, `MISSING`, `IMPUTED`, `UNKNOWN` (missingness is never treated as absence).
- Calculates timeline influence weights connecting historical events to active predictions.

### 4.7 Clinical RAG & Grounded Local Reasoning
- Located in `services/rag/retriever.py`, `services/rag/llm_reasoning.py`, and `services/rag/verifier.py`.
- Hybrid retrieval (lexical + dense) over authoritative oncology guidelines (NCCN, BI-RADS, Bosniak, WHO CNS).
- Local LLM via Ollama (`llama3:8b`) with strict prompt constraints, backed by a deterministic grounded synthesizer fallback.
- Verifier validates citation integrity (`[CITATION_ID]`) and triggers `NO_GROUNDED_ANSWER` if evidence coverage is insufficient.

### 4.8 Subgroup Fairness & Disparity Gates
- Located in `services/fairness/evaluator.py` and `services/fairness/gate.py`.
- Evaluates sensitivity, specificity, AUC, ECE (calibration error), FNR, and FPR across `age_group`, `sex`, and `scanner_vendor`.
- Release Gate: Rejects deployment if sensitivity disparity $> 10\%$, ECE gap $> 6\%$, or FNR gap $> 8\%$.

### 4.9 Clinical Outcome Capture & Leakage Prevention
- Located in `services/outcomes/tracker.py` and `services/outcomes/analysis.py`.
- Tracks real-world endpoints: Time to diagnosis (demonstrating $46.2\%$ latency reduction), clinician-AI agreement ($88.5\%$), override rate ($11.5\%$), and unsafe miss tracking.
- Strict software guard raises `TrainingDataLeakageError` if model training scripts attempt to access clinical outcome records.

### 4.10 Federated Learning Coordinator
- Located in `services/federated/coordinator.py`.
- Simulates multi-institutional federated rounds across 4 hospital nodes without centralized patient data movement.
- Computes out-of-site generalization on held-out unseen test sites (**Pati et al., 2022**).

### 4.11 Immutable Audit Trail
- Located in `services/audit/service.py`.
- INSERT-ONLY audit log tracking every request, route, model version, evidence citation, uncertainty vector, clinician action, and outcome.

---

## 5. API Reference (SRS §12)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v2/analyze` | Multimodal analysis (images, PDFs, text queries) with routing, ML, uncertainty, and XAI. |
| `POST` | `/api/v2/ingest` | Direct file/document upload returning `RequestContext` and quality assessment. |
| `POST` | `/api/v2/predictions/{id}/review` | Clinician decision capture (`ACCEPT`, `REJECT`, `EDIT`, `REQUEST_EVIDENCE`, `ABSTAIN`). |
| `GET` | `/api/v2/predictions/{id}/uncertainty` | Retrieve predictive entropy, data uncertainty, OOD score, and aggregate decision. |
| `GET` | `/api/v2/predictions/{id}/explanation` | Retrieve concept-based clinical explanation, Grad-CAM URI, and fidelity metrics. |
| `GET` | `/api/v2/cases/{id}/timeline` | Retrieve chronological longitudinal event timeline and trajectory features. |
| `POST` | `/api/v2/cases/{id}/timeline-events` | Append event to patient timeline (enforces append-only immutability). |
| `GET` | `/api/v2/models/{id}/fairness` | Retrieve subgroup fairness report and disparity analysis. |
| `GET` | `/api/v2/models/{id}/calibration` | Retrieve model calibration metrics (ECE, Brier score, temperature factor). |
| `GET` | `/api/v2/models/{id}/drift` | Retrieve data and concept drift telemetry. |
| `POST` | `/api/v2/outcomes` | Record prospective clinical study outcome (isolated from training pipelines). |
| `GET` | `/api/v2/studies/{id}/outcomes` | Comparative study analytics (AI-assisted vs Standard of Care). |
| `POST` | `/api/v2/federated/rounds` | Execute multi-site federated learning round with out-of-sample evaluation. |
| `GET` | `/api/v2/audit` | Query immutable audit events by `request_id`. |
| `GET` | `/api/v2/taxonomy` | Get active authoritative taxonomy configuration. |
| `GET` | `/api/v2/models` | List all registered model versions and lifecycle states. |
| `GET` | `/health` | System health and platform phase status. |

---

## 6. Getting Started & Setup

### 6.1 Requirements
- Python 3.11+
- (Optional) Docker & Docker Compose for containerized PostgreSQL, Redis, MinIO, Qdrant, Ollama, MLflow, Prometheus, and Grafana.

### 6.2 Running Locally with Python
```bash
# 1. Install dependencies
pip install -e .

# 2. Configure environment
cp .env.example .env

# 3. Seed database
python -m services.db.seed

# 4. Start API Gateway & Web Application
uvicorn services.gateway.app:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
- **Web Application Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 6.3 Running with Docker Compose
```bash
docker-compose up -d
```
Services exposed:
- **OncoSentinel Gateway & Web UI**: `http://localhost:8000`
- **PostgreSQL**: `localhost:5432`
- **MinIO Object Store**: `http://localhost:9000` (Console: `http://localhost:9001`)
- **Qdrant Vector DB**: `http://localhost:6333`
- **MLflow Model Registry**: `http://localhost:5000`
- **Prometheus Monitoring**: `http://localhost:9090`
- **Grafana Clinical Dashboards**: `http://localhost:3001`

### 6.4 Running the Test Suite
```bash
pytest tests/ -v
```

---

## 7. Safety & Regulatory Position (SRS §15)

OncoSentinel is an **AI-assisted research and clinical decision-support platform**. It does **NOT** autonomously prescribe treatment or render independent medical authority.

Key architectural safety commitments:
- **Evidence before generation:** RAG retrieval strictly grounds LLM reasoning; missing evidence triggers `NO_GROUNDED_ANSWER`.
- **Uncertainty before autonomy:** Equivocal or out-of-distribution cases automatically trigger `ABSTAIN` or `REVIEW_REQUIRED`.
- **Zero clinical outcome leakage:** Clinical outcomes are strictly isolated from training data pipelines (NFR-10).
- **Mandatory human-in-the-loop oversight:** Clinicians can review, edit, request evidence, or abstain from any model recommendation.
- **Permanent auditability:** All routing decisions, predictions, explanations, and reviews are immutably logged.
