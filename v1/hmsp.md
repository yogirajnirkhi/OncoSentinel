# HMS Structural Schematic Prompt

## Target Project Context

Build a Hospital Management System (HMS) as a healthcare-specific ERP integrating finance, billing, inventory, pharmacy, patient records, lab, radiology, and staff scheduling into a single platform.

The HMS must be structurally compatible with and extend the existing project codebase at `C:\Users\CYBORG\Desktop\RMP` (OncoSentinel v2.0 — Multimodal Cancer AI Clinical Decision-Support & Research Platform). The HMS is not a separate stack; it must uphold the current project's techstack, structural bindings, conventions, and safety commitments.

---

## 1. Current Project Analysis (Binding Constraints)

### 1.1 Techstack (must be upheld)

| Layer | Technology | Version/Pin | Notes |
|-------|-----------|-------------|-------|
| Language | Python | 3.11+ | `requires-python = ">=3.11"` |
| Web Framework | FastAPI | 0.111.0 | Async API gateway pattern |
| ASGI Server | Uvicorn | 0.29.0 | `uvicorn[standard]` |
| Data Validation | Pydantic | 2.7.1 | v2 models, `BaseModel`, `Field` |
| Settings | pydantic-settings | 2.2.1 | Env + `.env` loading, `SecretStr` |
| ORM | SQLAlchemy | 2.0.30 | `DeclarativeBase`, `Mapped`, `mapped_column` |
| Migrations | Alembic | 1.13.1 | Schema versioning |
| DB Driver | asyncpg / psycopg2-binary | 0.29.0 / 2.9.9 | Async + sync Postgres access |
| Task Queue | Celery | 5.4.0 | Background workers |
| Broker/Cache | Redis | 5.0.4 | Celery broker + caching |
| ML Framework | PyTorch | 2.3.0 | `torch`, `torchvision` |
| Model Zoo | timm | 1.0.3 | Backbone architectures |
| Medical Imaging | MONAI | 1.3.0 | Medical imaging domain |
| NIfTI Volumes | nibabel | 5.2.1 | CT/MRI volume I/O |
| Image Processing | OpenCV, Pillow | 4.9.0 / 10.3.0 | CV preprocessing |
| Scientific | numpy, scipy, scikit-learn | 1.26.4 / 1.13.0 / 1.5.0 | Arrays, stats, ML |
| Uncertainty/Calibration | mapie, netcal | 0.8.3 / 1.3.5 | Conformal prediction, ECE |
| XAI | captum, SHAP, quantus | 0.7.0 / 0.45.0 / 0.5.3 | Attribution, fidelity |
| Fairness | fairlearn | 0.10.0 | Disparity evaluation |
| Vector Store | Qdrant client | 1.9.1 | Hybrid dense + BM25 RAG |
| Object Store | MinIO | 7.2.7 | S3-compatible file storage |
| Embeddings | sentence-transformers | 3.0.1 | Dense retrieval |
| Lexical Search | rank-bm25 | 0.2.2 | Sparse retrieval |
| Local LLM | ollama | 0.2.1 | `llama3:8b` grounded reasoning |
| PDF/OCR | pymupdf, pytesseract | 1.24.3 / 0.3.10 | Document ingestion |
| MLOps | mlflow, dvc, evidently | 2.13.0 / 3.51.2 / 0.4.30 | Tracking, versioning, drift |
| Monitoring | prometheus-fastapi-instrumentator, opentelemetry | 6.1.0 / 1.24.0 | Metrics + tracing |
| Federated | flwr | 1.8.0 | Multi-site simulation |
| Config | pyyaml | 6.0.1 | YAML-driven config |
| Logging | structlog | 24.1.0 | Structured logging |
| CLI | typer, rich | 0.12.3 / 13.7.1 | Terminal UX |
| Resilience | tenacity | 8.3.0 | Retry logic |
| Auth | python-jose, passlib | 3.3.0 / 1.7.4 | JWT HS256 + bcrypt |
| Lint/Format | ruff | 0.4.4 | line-length 100, target py311 |
| Typecheck | mypy | 1.10.0 | strict = true |
| Security | bandit | 1.7.8 | SAST scanning |
| Tests | pytest, pytest-asyncio | 8.2.0 / 0.23.7 | coverage floor 80% |

**Rule:** Every HMS dependency must be a subset or additive extension of this list. No new language runtimes (Node, Go, Java, .NET). No new primary web frameworks. No new ORMs.

### 1.2 Infrastructure Bindings (docker-compose.yml)

The HMS must run within the existing Docker Compose service mesh (`oncosentinel_net`):

- **PostgreSQL 16 + pgvector** (`pgvector/pgvector:pg16`, port 5432) — primary relational DB. HMS tables must live in the same Postgres instance, ideally a separate schema (e.g., `hms`) to avoid collision with OncoSentinel tables, sharing the same connection pool pattern (`DATABASE_URL` env var, `postgresql+asyncpg://`).
- **Redis 7-alpine** (port 6379) — Celery broker + cache. HMS async tasks (billing jobs, report generation, inventory alerts) use the same Redis instance.
- **MinIO** (ports 9000/9001) — object storage for HMS document invoices, pharmacy labels, radiology DICOM derivatives, staff photos.
- **Qdrant** (port 6333) — vector store. HMS can reuse for semantic search over clinical documentation, formulary, policy PDFs.
- **Ollama** (port 11434, `llama3:8b`) — local LLM. HMS grounded reasoning (billing policy queries, formulary lookup) must use the same Ollama instance and citation-integrity pattern.
- **MLflow** (port 5000) — model registry. HMS ML models (demand forecasting, no-show prediction) register here.
- **Prometheus + Grafana** (ports 9090/3001) — monitoring. HMS must emit metrics via `prometheus-fastapi-instrumentator` and expose dashboards under Grafana provisioning.
- **Gateway** (FastAPI, port 8000) — HMS endpoints mount under the same gateway app or a namespaced router (e.g., `/api/v2/hms/...`) sharing CORS, auth, exception handling, and observability middleware.
- **Celery Worker** — same Dockerfile as gateway; HMS tasks registered in `services/tasks/celery_app.py`.

**Rule:** Do not introduce new infrastructure services. HMS reuses the ten existing containers. HMS environment variables follow `.env.example` naming conventions.

### 1.3 Structural Bindings (code organization)

The project follows a service-oriented layout under `services/`:

```
services/
  core/           # config_loader, exceptions, logging, settings
  db/             # SQLAlchemy ORM models, session, seed
  gateway/        # FastAPI app, auth (JWT RBAC), routes, schemas (Pydantic)
  ingestion/      # validator (quality gating)
  interop/        # fhir_adapter (HL7 FHIR R4 bidirectional)
  longitudinal/   # timeline_manager, influence_tracker (append-only)
  ml/             # backbone (shared), heads (category factory)
  outcomes/       # tracker, analysis (isolated clinical outcomes)
  rag/            # retriever, llm_reasoning, verifier (RAG + grounded LLM)
  router/         # engine, intent classifier, cancer relevance, modality checker
  tasks/          # celery_app
  uncertainty/    # calibration, ood_detector
  web/            # static web UI
  xai/            # concept_mapper, evaluator (concept-based XAI)
  audit/          # audit service (INSERT-ONLY)
  fairness/       # evaluator, gate (subgroup disparity)
  federated/      # coordinator (FL rounds)
```

**Rules for HMS placement:**
- HMS domain modules go under `services/hms/` (e.g., `services/hms/patient.py`, `services/hms/billing.py`, `services/hms/pharmacy.py`, `services/hms/inventory.py`, `services/hms/scheduling.py`, `services/hms/finance.py`, `services/hms/lab.py`, `services/hms/radiology.py`).
- HMS ORM models extend `services/db/models.py` pattern (same `Base`, UUID primary keys, `created_at`/`updated_at` server defaults, JSON metadata columns, CheckConstraints) OR live in a dedicated `services/hms/models.py` importing from `services.db.models.Base`.
- HMS Pydantic schemas follow `services/gateway/schemas.py` pattern (`BaseModel`, `Field`, `datetime`, `Optional`, `list[str]`, `dict[str, Any]`).
- HMS API routes follow `services/gateway/routes.py` pattern (APIRouter, versioned `/api/v2/...`, dependency injection via `Depends`).
- HMS auth reuses `services/gateway/auth.py` (`UserPrincipal`, roles `CLINICIAN`, `RESEARCHER`, `ADMIN`, `AUDITOR`, `ANALYST`, `require_roles(...)`).
- HMS config loads from YAML via `services/core/config_loader.py` pattern; no hard-coded thresholds or business rules in Python.
- HMS logging uses `structlog` via `services/core/logging.py`.
- HMS exceptions extend `services/core/exceptions.py` (`OncoSentinelError`).
- HMS settings extend `services/core/settings.py` (`Settings`, `get_settings()` lru_cache singleton).
- HMS DB session uses `services/db/session.py` (`init_db`, async engine/session pattern).

### 1.4 Conventions & Compatibility Requirements

| Convention | Requirement |
|-----------|-------------|
| Linting | `ruff` with `line-length = 100`, `target-version = "py311"`, select `E F W I N UP S B A C4 PT SIM TCH ANN` |
| Typechecking | `mypy` strict = true, python 3.11 |
| Security scan | `bandit` (exclude tests/scripts) |
| Formatting | `ruff-format` |
| Pre-commit | ruff (fix + format), mypy, bandit, check-yaml/json/toml, end-of-file-fixer, trailing-whitespace, detect-secrets, no-commit-to-branch main |
| Testing | `pytest tests/ -v`, coverage `--cov=services --cov-fail-under=80`, `asyncio_mode = "auto"` |
| Secrets | Never in code; `.env` only; `detect-secrets` baseline; `SecretStr` for secrets |
| Config-driven | All thresholds in `configs/*.yaml`; no hard-coded business values in Python |
| Immutability | Audit tables INSERT-ONLY; timeline tables APPEND-ONLY (no UPDATE/DELETE, DB triggers + app guards) |
| Schema isolation | Clinical outcomes isolated from training pipelines (NFR-10 pattern) |
| FHIR R4 | `services/interop/fhir_adapter.py` pattern for HL7 FHIR R4 bidirectional mapping (DiagnosticReport, Observation, Bundle) |
| JWT RBAC | HS256, roles CLINICIAN/RESEARCHER/ADMIN/AUDITOR/ANALYST, `require_roles` dependency |
| Error handling | Custom exception handler returning `HTTP 422` with `{"error": ..., "message": ...}` |
| Health endpoint | `/health` returning status, version, environment, platform_phase |
| API docs | Swagger at `/docs`, ReDoc at `/redoc` |
| Versioning | Semantic version in `pyproject.toml` `[project] version` |

### 1.5 Safety & Regulatory Commitments (SRS §15, must extend to HMS)

- **Evidence before generation:** RAG grounding; missing evidence triggers safe-fail states.
- **Uncertainty before autonomy:** Equivocal cases trigger review/abstain, not automatic action.
- **Zero clinical outcome leakage:** Outcome/adjudication data isolated from model training pipelines.
- **Mandatory human-in-the-loop:** Clinician can accept, reject, edit, request evidence, or abstain.
- **Permanent auditability:** All routing decisions, actions, and outcomes immutably logged by `request_id`.
- **No secrets in code:** NFR-06 — detect-private-key + detect-secrets pre-commit hooks.
- **Research Use Only / clinical decision-support disclaimer:** HMS does not autonomously prescribe or render independent medical authority.

---

## 2. HMS Structural Schematic (Prompt for Implementation)

The following is the detailed structural schematic prompt to be fed into an implementation agent. It is written so the output HMS upholds every binding above.

---

### HMS Implementation Prompt

You are implementing a Hospital Management System (HMS) module for the **OncoSentinel v2.0** codebase at `C:\Users\CYBORG\Desktop\RMP`.

**Project identity:** OncoSentinel v2.0 — Multimodal Cancer AI Clinical Decision-Support & Research Platform (healthcare-specific ERP extension). Version 2.0.0, Python 3.11+, FastAPI.

**Core mandate:** Build an HMS that integrates finance, billing, inventory, pharmacy, patient records (EMR/EHR), laboratory, radiology, and staff scheduling into a single platform, while remaining **structurally compatible** with the existing OncoSentinel codebase. The HMS must not introduce new languages, frameworks, ORMs, or infrastructure services. It must reuse the existing techstack, service layout, config-driven conventions, auth/RBAC model, DB session pattern, safety commitments, and CI/tooling configuration.

---

#### A. Structural Location & Naming

1. Create all HMS domain code under `services/hms/`:
   - `services/hms/__init__.py`
   - `services/hms/models.py` — SQLAlchemy ORM models (inherit `services.db.models.Base`)
   - `services/hms/schemas.py` — Pydantic v2 request/response DTOs (inherit patterns from `services/gateway/schemas.py`)
   - `services/hms/routes.py` — FastAPI `APIRouter` mounted under `/api/v2/hms` (prefix), reusing `services/gateway/app.py` CORS/exception/health middleware
   - `services/hms/patient.py` — patient registry / EMR core domain service
   - `services/hms/billing.py` — billing & invoicing domain service
   - `services/hms/finance.py` — finance / general ledger domain service
   - `services/hms/pharmacy.py` — pharmacy & formulary domain service
   - `services/hms/inventory.py` — inventory & stock management domain service
   - `services/hms/scheduling.py` — staff scheduling / appointment domain service
   - `services/hms/lab.py` — laboratory orders & results domain service
   - `services/hms/radiology.py` — radiology orders & imaging workflow domain service
   - `services/hms/interop.py` — HL7 FHIR R4 adapter (extend `services/interop/fhir_adapter.py` patterns: Patient, Encounter, MedicationRequest, ServiceRequest, DiagnosticReport, Observation, Bundle)
   - `services/hms/tasks.py` — Celery tasks (billing runs, inventory alerts, claim submissions, report generation) registered in `services/tasks/celery_app.py`
   - `services/hms/exceptions.py` — HMS domain exceptions extending `services.core.exceptions.OncoSentinelError`
   - `services/hms/audit.py` — HMS audit event logging reusing `services.audit.service` INSERT-ONLY pattern

2. HMS ORM models in `services/hms/models.py` or appended to `services/db/models.py`:
   - Follow `services/db/models.py` conventions exactly: `DeclarativeBase` import, UUID primary keys via `_uuid()`, `DateTime(timezone=True)` with `server_default=func.now()`, `JSON` metadata columns, `String` lengths, `CheckConstraint` for enums, `Index` on foreign keys and lookup columns, `Mapped`/`mapped_column` typing, `relationship` back-populates.
   - HMS tables live in the same PostgreSQL database (`oncosentinel`), preferably under an `hms_` table-name prefix or dedicated `hms` schema to avoid collision with OncoSentinel tables.
   - **Insert-only / append-only critical tables** (audit, ledger entries, prescription records) enforce no UPDATE/DELETE at DB trigger level + application guard, mirroring `PatientTimelineEvent` and `AuditEvent`.
   - **Financial/adjudication isolation:** Billing/finance outcome tables must be isolated from any ML training pipeline (NFR-10 pattern — `ClinicalOutcome` isolation).

3. HMS Pydantic schemas in `services/hms/schemas.py`:
   - Follow `services/gateway/schemas.py`: `from __future__ import annotations`, `from pydantic import BaseModel, Field`, use `datetime`, `Optional`, `list[str]`, `dict[str, Any]`, `Field(default_factory=list)`, `description=` strings.
   - All HMS request/response models must be JSON-serializable and documented for Swagger (`/docs`).

4. HMS routes in `services/hms/routes.py`:
   - FastAPI `APIRouter(prefix="/api/v2/hms", tags=["HMS"])`.
   - Dependencies: `Depends(get_current_user)` from `services.gateway.auth`, `require_roles(...)` for RBAC enforcement.
   - Roles: `CLINICIAN`, `RESEARCHER`, `ADMIN`, `AUDITOR`, `ANALYST` (plus HMS-specific roles if needed: `PHARMACIST`, `BILLING_CLERK`, `INVENTORY_MANAGER`, `SCHEDULER` — but must be additive to existing set and declared in `auth.py`).
   - Every route must log via `structlog` (`services.core.logging.get_logger`).
   - Every route must wrap domain calls in try/except raising `OncoSentinelError` (caught by global exception handler → HTTP 422).

5. HMS configuration:
   - All HMS thresholds, business rules, role permissions, and integrations configured in `configs/hms.yaml` (new file) following `configs/taxonomy.yaml` / `configs/thresholds.yaml` conventions: versioned, `updated_at`, single source of truth, no hard-coded values in Python.
   - `services/core/settings.py` gains optional HMS fields (e.g., `hms_config_path: Path = Path("configs/hms.yaml")`).
   - `.env.example` gains any new HMS env vars (DB, Redis, MinIO, Ollama URLs reuse existing vars; do not duplicate).

---

#### B. Domain Modules — Required Entities & Responsibilities

**Patient Registry / EMR (`patient.py`):**
- `Patient` (demographics, MRN, contact, insurance, consent flags)
- `Encounter` (visit, admission/discharge, department, attending clinician)
- `MedicalRecord` (allergies, problems, medications, immunizations — problem list)
- Append-only clinical document store referencing MinIO URIs
- FHIR R4: `Patient` resource mapping in `interop.py`

**Billing & Finance (`billing.py`, `finance.py`):**
- `ChargeItem`, `Invoice`, `InvoiceLine`, `Payment`, `Claim` (insurance claim), `Adjustment`
- Fee schedule, coding (ICD-10/CPT/HCPCS references), pricing rules from config
- General ledger entries, double-entry accounting entries, period close
- Insert-only ledger (no UPDATE/DELETE on posted entries; corrections via reversing entries referencing original)
- Financial reports (aging, revenue, collection rate) — read-only aggregates
- HMS financial data must never feed ML training (NFR-10 isolation)

**Pharmacy (`pharmacy.py`):**
- `Medication` (formulary entry, NDC, strength, dosage form, route)
- `Prescription` / `MedicationOrder` (prescriber, patient, encounter, dispense status, refills)
- `DispenseRecord` (pharmacist, quantity, lot number, expiry)
- Drug interaction / allergy checking service (rule-based, config-driven)
- FHIR R4: `MedicationRequest`, `Medication` resource mapping

**Inventory (`inventory.py`):**
- `StockItem` (SKU, name, category, unit, par level, reorder point)
- `StockMovement` (inbound/outbound/adjustment, insert-only ledger)
- `PurchaseOrder`, `ReceiveRecord`
- Expiry/batch/lot tracking, FIFO allocation
- Low-stock alerts via Celery tasks

**Staff Scheduling (`scheduling.py`):**
- `StaffMember` (role, department, credentials, license expiry, contact)
- `Shift` / `Roster` (shift templates, assignments, swap requests)
- `Appointment` (patient, provider, encounter, start/end, status, type)
- `Availability` (provider time blocks)
- Conflict detection (double-booking, credential validity)

**Laboratory (`lab.py`):**
- `LabTest` (catalog, LOINC code, specimen type, reference range)
- `LabOrder` (ordering clinician, patient, encounter, status: ordered/collected/resulted/cancelled)
- `LabResult` (value, unit, flag: normal/abnormal/critical, result datetime, verifying pathologist)
- Insert-only results (corrections via amended result referencing original)
- Critical-value alerting via Celery

**Radiology (`radiology.py`):**
- `RadiologyStudy` (modality: X-ray/CT/MRI/ultrasound, body part, ordering clinician)
- `RadiologyOrder` (status, priority, patient prep)
- `RadiologyReport` (findings, impression, radiologist, signed datetime)
- Image references stored in MinIO; DICOM metadata in JSON metadata column
- Integrates with OncoSentinel ingestion/validator pipeline for image quality gating when imaging is used diagnostically

**Interop / FHIR R4 (`interop.py`):**
- Extend `services/interop/fhir_adapter.py` (`FHIRAdapter`) to support HMS resources:
  - `Patient`, `Encounter`, `MedicationRequest`, `Medication`, `ServiceRequest` (lab/radiology orders), `DiagnosticReport`, `Observation`, `Bundle`, `Appointment`, `Schedule`, `Slot`
- Bidirectional parsing: FHIR R4 → HMS domain payloads; HMS domain → FHIR R4 resources
- Use existing `system_loinc`, `system_snomed`, `system_onco` URI patterns

**Audit (`audit.py`):**
- Every HMS action logged to `audit_events` (reuse `AuditEvent` model) with `request_id`, `actor_id`, `actor_role`, `action`, `service_name="hms"`, `trace_id`
- INSERT-ONLY enforcement

**Tasks (`tasks.py`):**
- Celery tasks: end-of-day billing run, claim submission, low-stock reorder, expiry sweep, critical-result notification, invoice reminder, financial period close
- Register in `services/tasks/celery_app.py`, reuse `REDIS_URL` broker

---

#### C. API Endpoint Schematic (must mount under `/api/v2/hms`)

Mirror `services/gateway/schemas.py` DTO style and `README.md` API Reference table style. Required endpoint groups:

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/api/v2/hms/patients` | Register patient (EMR) | CLINICIAN, ADMIN, RECEPTION |
| GET | `/api/v2/hms/patients/{id}` | Get patient record | CLINICIAN, RESEARCHER, ADMIN, AUDITOR |
| PUT | `/api/v2/hms/patients/{id}` | Update demographics (audited) | CLINICIAN, ADMIN |
| POST | `/api/v2/hms/encounters` | Create encounter/visit | CLINICIAN, ADMIN |
| POST | `/api/v2/hms/billing/invoices` | Generate invoice | BILLING_CLERK, ADMIN |
| POST | `/api/v2/hms/billing/payments` | Record payment | BILLING_CLERK, ADMIN |
| POST | `/api/v2/hms/billing/claims` | Submit insurance claim | BILLING_CLERK, ADMIN |
| GET | `/api/v2/hms/finance/ledger` | General ledger entries (read-only) | ADMIN, AUDITOR, FINANCE |
| POST | `/api/v2/hms/pharmacy/prescriptions` | Create medication order | CLINICIAN, PHARMACIST |
| POST | `/api/v2/hms/pharmacy/dispense` | Record dispensing | PHARMACIST, ADMIN |
| POST | `/api/v2/hms/inventory/movements` | Stock movement (insert-only ledger) | INVENTORY_MANAGER |
| GET | `/api/v2/hms/inventory/low-stock` | Low-stock report | INVENTORY_MANAGER, ADMIN |
| POST | `/api/v2/hms/scheduling/appointments` | Book appointment | SCHEDULER, CLINICIAN, ADMIN |
| PUT | `/api/v2/hms/scheduling/appointments/{id}` | Reschedule/cancel | SCHEDULER, CLINICIAN, ADMIN |
| POST | `/api/v2/hms/lab/orders` | Create lab order | CLINICIAN, ADMIN |
| POST | `/api/v2/hms/lab/results` | Enter/verify lab result | LAB_TECH, PATHOLOGIST, ADMIN |
| POST | `/api/v2/hms/radiology/orders` | Create radiology order | CLINICIAN, ADMIN |
| POST | `/api/v2/hms/radiology/reports` | Sign radiology report | RADIOLOGIST, ADMIN |
| GET | `/api/v2/hms/audit` | Query HMS audit events by request_id | AUDITOR, ADMIN |
| POST | `/api/v2/hms/fhir/patient` | Inbound FHIR Patient → HMS | CLINICIAN, ADMIN |
| GET | `/api/v2/hms/fhir/patient/{id}` | Outbound HMS → FHIR Patient bundle | CLINICIAN, RESEARCHER, ADMIN |

All responses use HMS Pydantic schemas; errors use `OncoSentinelError` → HTTP 422.

---

#### D. Database Schema Binding (extend `services/db/models.py`)

Follow `services/db/models.py` exactly. Suggested HMS tables (prefix `hms_`):

- `hms_patients`, `hms_encounters`, `hms_medical_records`
- `hms_charge_items`, `hms_invoices`, `hms_invoice_lines`, `hms_payments`, `hms_claims`, `hms_ledger_entries`
- `hms_medications`, `hms_prescriptions`, `hms_dispense_records`
- `hms_stock_items`, `hms_stock_movements`, `hms_purchase_orders`
- `hms_staff`, `hms_shifts`, `hms_appointments`, `hms_availabilities`
- `hms_lab_tests`, `hms_lab_orders`, `hms_lab_results`
- `hms_radiology_studies`, `hms_radiology_orders`, `hms_radiology_reports`
- `hms_audit_events` (reuse existing `audit_events` with `service_name="hms"`)

Constraints to mirror:
- UUID PKs, `CheckConstraint` for status enums, `Index` on FKs, `missingness_state`-style explicit NULL handling where applicable, insert-only triggers on ledger/audit/prescription/result tables.

---

#### E. Safety, Compliance & Observability Bindings

1. **Auth/RBAC:** Reuse `services/gateway/auth.py` `UserPrincipal`, `get_current_user`, `require_roles`. JWT HS256 from `JWT_SECRET_KEY`. HMS routes enforce least-privilege roles.
2. **No hard-coded secrets:** All HMS secrets via `SecretStr` settings + `.env`; `detect-secrets` baseline updated.
3. **No hard-coded thresholds:** All HMS business thresholds in `configs/hms.yaml`; loaded at runtime via `services.core.config_loader`.
4. **Immutability:** HMS financial ledger, prescriptions, lab results, and audit logs are INSERT-ONLY (DB trigger + app guard), mirroring `PatientTimelineEvent` / `AuditEvent`.
5. **Outcome isolation:** Billing/financial adjudication data is isolated from any ML training pipeline (NFR-10 pattern).
6. **Human-in-the-loop:** HMS actions with clinical impact (dispensing, result verification, claim submission) require explicit actor attribution and support edit/reject/void-with-reversal patterns; no fully autonomous financial or clinical execution.
7. **Auditability:** Every HMS request, state change, and financial posting immutably logged in `audit_events` traceable by `request_id`.
8. **Observability:** HMS endpoints instrumented via `prometheus-fastapi-instrumentator`; traces via OpenTelemetry; health via `/health`.
9. **FHIR R4 interop:** HMS exchanges must be valid HL7 FHIR R4 resources, following `services/interop/fhir_adapter.py` conventions.

---

#### F. Tooling & CI Bindings

Update/add to existing config (do not create new tooling):

- `pyproject.toml`: Add HMS-specific dependencies only if not already in the list (prefer reuse). Keep `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]`, `[tool.bandit]` sections intact.
- `.pre-commit-config.yaml`: Keep existing hooks; ensure HMS files pass `ruff`, `mypy strict`, `bandit`.
- `tests/`: Add `tests/hms/` test files following existing pytest style (`pytest-asyncio`, `asyncio_mode = "auto"`), coverage contributes to the 80% floor.
- `docker-compose.yml`: Do not add services. HMS runs in existing `gateway` and `celery_worker` containers; env vars reused.
- `.env.example`: Add HMS env var placeholders only if new (reuse `DATABASE_URL`, `REDIS_URL`, etc.).

---

#### G. Deliverable Acceptance Criteria

1. HMS imports and runs within the existing OncoSentinel FastAPI app (`services/gateway/app.py`) without new infrastructure.
2. `pytest tests/ -v` passes with coverage ≥ 80% including new `tests/hms/`.
3. `ruff` check and `ruff format --check` pass on `services/hms/`.
4. `mypy --strict` passes on `services/hms/`.
5. `bandit` passes on `services/hms/`.
6. No secrets committed; `.env` only; `detect-secrets` baseline clean.
7. All HMS thresholds in `configs/hms.yaml`; zero hard-coded business values in `services/hms/*.py`.
8. HMS routes documented at `http://localhost:8000/docs` under HMS tag.
9. Insert-only enforcement verified on ledger/prescription/result/audit tables.
10. FHIR R4 round-trip (HMS → FHIR → HMS) validated for Patient, Encounter, MedicationRequest, ServiceRequest, DiagnosticReport, Observation, Bundle.

---

### End of HMS Structural Schematic Prompt
