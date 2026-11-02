# OncoSentinel v2.0 — Architecture & Research Decision Log (ADR)

This living document records all major architectural, scientific, data-governance, and engineering decisions for OncoSentinel v2.0, as mandated by the **Master Project Roadmap, Architecture & Faculty Review Guide** (§21).

---

## Decision Log Summary

| ADR ID | Date | Title | Status | Impact Area |
|---|---|---|---|---|
| **ADR-01** | 2026-10-11 | Dual-Mode Persistence & Zero-Dependency Execution | Accepted | Database & Infrastructure |
| **ADR-02** | 2026-10-11 | Separation of Technical Pixel Attribution from Clinical Concepts | Accepted | Explainability (XAI) |
| **ADR-03** | 2026-10-11 | Strict Schema-Level Training Leakage Prevention (NFR-10) | Accepted | Outcomes & Training Integrity |
| **ADR-04** | 2026-10-11 | Multi-Detector Consensus for Out-of-Distribution Detection | Accepted | Uncertainty & Safety Gates |
| **ADR-05** | 2026-10-18 | Standardized HL7 FHIR R4 with AI Extension Namespaces | Accepted | Interoperability (PACS/LIS) |
| **ADR-06** | 2026-10-18 | Deterministic Cryptographic Checkpoint Fingerprinting (NFR-12) | Accepted | Checkpoint Integrity |
| **ADR-07** | 2026-10-18 | Layered Concept XAI Grounded in Domain Oncology Literature | Accepted | Explainability (XAI) |
| **ADR-08** | 2026-10-20 | Unified Hybrid Shared Network with Modality-Aware Encoders | Accepted | ML Architecture & Training |
| **ADR-09** | 2026-10-20 | Elimination of Default Fake Checkpoint Metrics & Unearned States | Accepted | Checkpoint & Registry Integrity |
| **ADR-10** | 2026-10-20 | Deterministic Sequential Multi-Task Training Queue | Accepted | Training Engine |
| **ADR-11** | 2026-10-20 | Patient-Grouped Split Manifests for Data Leakage Prevention | Accepted | Dataset Splitting |
| **ADR-12** | 2026-10-20 | Standardized Model Cards and Experiment Run Records | Accepted | Reproducibility & Governance |
| **ADR-13** | 2026-10-31 | Deep Integration of Hospital Management System (HMS) with OncoSentinel Core Platform | Accepted | Clinical Operations & System Integration |
| **ADR-14** | 2026-11-01 | Authentic Cryptographic Staff Authentication & Institutional RBAC | Accepted | Security & Access Governance |
| **ADR-15** | 2026-11-01 | Integration of Real Checkpoints with Strict Untrained Labeling & Zero Fake Metric Policy | Accepted | ML Integrity & Model Lifecycle |
| **ADR-16** | 2026-11-01 | Full 31-Resource Authoritative HMS Seeding & Deep Bi-Directional AI-EMR Safety Hooks | Accepted | Clinical Operations & EMR Safety |
| **ADR-17** | 2026-11-01 | Deep UI Consolidation into Surgical Teal HMS Front-End | Accepted | Web UI & Workflow |
| **ADR-18** | 2026-11-01 | Single Unified Web Application Architecture & Role-Based Registration | Accepted | Web UI & RBAC |
| **ADR-19** | 2026-11-01 | Integration of All 7 MobileNetV3 Checkpoints & Elimination of Hardcoded UI Values | Accepted | ML Orchestration & Diagnostic Studio |

---

## ADR-08: Unified Hybrid Shared Network with Modality-Aware Encoders
- **Date:** 2026-10-20
- **Status:** Accepted
- **Context/Problem:** The platform requires supporting eight cancer-imaging tasks spanning distinct medical modalities (ultrasound, CT, MRI, blood microscopy, histology, cytology). Forcing all modalities through an identical single backbone assumes feature equivalence across disparate imaging physics, while maintaining eight independent codebases introduces massive maintenance waste.
- **Options Considered:**
  1. *Eight completely separate codebases and repositories:* High maintenance overhead, redundant test suites, and fragmented gateways.
  2. *Single monolithic network with shared weights for all inputs:* Unproven assumption; risks severe negative transfer between incompatible physics (e.g. ultrasound vs histopathology stains).
  3. *(Selected) Hybrid Shared Network:* One common engineering framework, dataset adapters, and training queue; modality-aware convolutional encoder branches (Ultrasound, CT, MRI, Microscopy/Histology, Cytology); task-specific classification heads.
- **Decision:** Adopt the Hybrid Shared Network architecture as specified in Master Roadmap §5.
- **Evidence/Reason:** Preserves modality-specific spatial/intensity distributions while reusing 100% of the training, validation, checkpointing, and evaluation code.
- **Impact on Architecture/Data/Training:** Introduced `training/model_factory.py` with `ModalityEncoder`, `TaskSpecificHead`, and `HybridMultiTaskModel`.
- **Follow-up Action:** Conduct empirical tests before sharing learned parameters between branches.

---

## ADR-09: Elimination of Default Fake Checkpoint Metrics & Unearned States
- **Date:** 2026-10-20
- **Status:** Accepted
- **Context/Problem:** Checkpoint helpers and baseline registrations in earlier iterations contained hard-coded example metrics (`validation_auc=0.94`, `expected_ece=0.04`, `status="PRODUCTION"`). This violated scientific credibility by making untrained random initializations appear evaluated.
- **Options Considered:**
  1. *Retain default placeholder numbers:* Causes false research claims and misleads evaluators/faculty.
  2. *(Selected) Strict Null/Unmeasured State:* Require `validation_auc=None`, `expected_ece=None`, and `status="SYNTHETIC_BASELINE"` / `status="SCAFFOLDED"` until real training and evaluation runs occur on held-out test data.
- **Decision:** Refactor `services/ml/checkpoints.py` and `services/ml/registry.py` to completely eliminate fake default metrics.
- **Evidence/Reason:** Adheres strictly to Master Roadmap §3.3 A and §10.3.
- **Impact on Architecture/Data/Training:** Checkpoint and registry schemas now distinguish between unmeasured baselines and evaluated checkpoints with linked run IDs.

---

## ADR-10: Deterministic Sequential Multi-Task Training Queue
- **Date:** 2026-10-20
- **Status:** Accepted
- **Context/Problem:** Training eight tasks concurrently requires excessive GPU/memory resources and risks corrupting checkpoint outputs if jobs fail in parallel.
- **Options Considered:**
  1. *Concurrent training of all eight tasks:* Resource-heavy, difficult to debug, non-deterministic logging.
  2. *(Selected) Deterministic Sequential Training Queue:* Process tasks slot-by-slot (Slots 1 through 8) via `training/train_all.py` with failure isolation, resume capability, and consolidated queue reporting.
- **Decision:** Implement sequential training manager with resume/retry verification based on dataset version, split manifest, and model config hash.
- **Evidence/Reason:** Satisfies Master Roadmap §8 and §14. Ensures that a failure in one task does not corrupt or halt other task artifacts.

---

## ADR-11: Patient-Grouped Split Manifests for Data Leakage Prevention
- **Date:** 2026-10-20
- **Status:** Accepted
- **Context/Problem:** In clinical datasets (such as BUSI or C-NMC), multiple image tiles or slices often originate from the same patient or biopsy specimen. Naive random train/val/test splitting leads to patient leakage and artificially inflated performance.
- **Options Considered:**
  1. *Random item-level splitting:* High risk of patient leakage between train and test sets.
  2. *(Selected) Grouped Split Manifests:* Partition data by `patient_id`, `study_id`, or `slide_id`. Validate zero intersection between partitions before training.
- **Decision:** Implement `training/split_manifest.py` with `create_leakage_resistant_split` and `manifest.verify_no_leakage()`.
- **Evidence/Reason:** Direct adherence to Master Roadmap §9.1 and literature (Pati et al., 2022).
- **Impact on Architecture/Data/Training:** Split manifests are serialized to `artifacts/manifests/{task_id}_split.json` and permanently referenced in the model card and run record.

---

## ADR-12: Standardized Model Cards and Experiment Run Records
- **Date:** 2026-10-20
- **Status:** Accepted
- **Context/Problem:** Machine learning experiments require full traceability from raw dataset version to final checkpoint and evaluation metrics to ensure scientific reproducibility and auditability.
- **Options Considered:**
  1. *Ad-hoc markdown notes:* Inconsistent schemas, difficult to programmatically verify.
  2. *(Selected) Standardized Model Cards & Run Records:* Machine-readable JSON run records (`artifacts/logs/{task_id}_{run_id}.json`) and standard Markdown Model Cards (`artifacts/model_cards/{task_id}.md`) adhering to Master Roadmap §22.1 & §22.2.
- **Decision:** Implement `training/model_cards.py` and `TaskRunRecord.save_json`.
- **Impact on Architecture/Data/Training:** Every training execution automatically generates a complete model card with confusion matrix, per-class sensitivity/specificity, ECE, Brier score, and stated limitations.

---

## ADR-13: Deep Integration of Hospital Management System (HMS) with OncoSentinel Core Platform
- **Date:** 2026-10-31
- **Status:** Accepted
- **Impact Area:** Clinical Operations, Transaction Boundaries, Security & RBAC, Multi-Tenant Database
- **Context/Problem:** The Hospital Management System (HMS) was developed independently based on the `hmsp.md` specification but was completely decoupled from `v1` (the core backend). `v1` had not mounted `HMSBindings`, lacked the 31 `hms_*` tables, lacked clinical safety hooks, and only recognized 5 roles. Meanwhile, `hms` contained standalone synthetic shims (`demo/host.py`) rather than binding to the actual production engine.
- **Options Considered:**
  1. *Run HMS as a separate microservice with its own database and auth gateway:* High operational complexity, duplicated tokens, and disjointed audit logs.
  2. *Replace `v1` backend with HMS demo harness:* Would discard multimodal AI pipelines, RAG retriever, training engine, and research outcome tracking.
  3. *(Selected) In-Process Integration via `HMSBindings` & Shared ORM Metadata:*
     - Merge HMS domain models (`services/hms/models.py`) into `services.db.models.Base`.
     - Implement explicit adapter layer in `services/gateway/hms_adapters.py` providing `get_hms_async_session`, `hms_audit_write`, `hms_audit_query`, `hms_pharmacy_safety`, `hms_imaging_quality`, and `hms_ai_evidence`.
     - Expand `services/gateway/auth.py` to evaluate all 14 clinical and administrative roles.
     - Mount HMS routes (`/api/v2/hms`) and static web assets (`/hms`) within `services/gateway/app.py`.
     - Register HMS background review jobs in `services/tasks/celery_app.py`.
- **Decision:** Implement Option 3.
- **Evidence/Reason:** Adheres strictly to `hmsp.md` structural bindings (§1.1, §1.2, §1.3). Retains 100% of the core platform capabilities while equipping the system with full enterprise healthcare operations (patient registry, appointments, billing invoices, double-entry finance, formulary, FIFO inventory, and lab/radiology workflows).
- **Impact on Architecture/Data/Training:**
  - Database: `init_db()` in `services/db/session.py` auto-creates all 46 tables and sets up append-only triggers and deferred balanced-ledger constraints.
  - Security: `AuditEvent.actor_role` widened to `String(128)` to support multi-role attribution.
  - Interoperability: FHIR R4 Patient import/export and diagnostic report generation now bridge clinical records directly to AI evidence advisory.
  - Observability: All HMS mutations and read queries are written to the authoritative `audit_events` table.

---

## ADR-14: Authentic Cryptographic Staff Authentication & Institutional RBAC
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Security, Access Governance, Identity & Audit Attribution
- **Context/Problem:** Previous development prototypes relied on hardcoded credentials, plaintext bypass tokens (`"dev"`, `"demo"`, `"admin"` giving global `ALL_ROLES`), and unauthenticated spoofing headers (`X-Dev-Role`, `dev_admin_operator`, `clinician_dr_smith`). This violated NFR-06 and prevented realistic faculty evaluation of role-based segregation of duties.
- **Options Considered:**
  1. *Retain demo bypasses with an optional environment flag:* High risk of leaking bypass mechanisms into staging/production; distorts security audits.
  2. *External OAuth2/OIDC identity provider (e.g. Keycloak, Auth0):* Heavy operational dependency for offline/local evaluation and academic presentations.
  3. *(Selected) In-Database Cryptographic User Registry with Salted PBKDF2-HMAC-SHA256 & JWT Tokens:*
     - Model a dedicated `User` entity (`users` table) storing cryptographic salt, password hash, assigned institutional roles, department, and active status.
     - Implement standard `POST /api/v2/auth/login`, `GET /api/v2/auth/me`, and `GET /api/v2/auth/users` endpoints.
     - Eliminate all hardcoded role bypasses and fake demo tokens from `services/gateway/auth.py`.
     - Seed 8 realistic institutional staff personas (`dr_chen`, `dr_patel`, `dr_adams`, `nurse_sarah`, `pharma_alex`, `billing_mark`, `admin_clara`, `research_elena`) with explicit role boundaries and secure default passwords.
- **Decision:** Implement Option 3.
- **Evidence/Reason:** Guarantees strict segregation of duties between oncology clinicians, radiologists, pharmacists, billing clerks, and administrators while remaining completely self-contained and verifiable without external identity infrastructure.
- **Impact on Architecture/Data/Training:**
  - Database: Added `User` table to `services/db/models.py` with unique usernames and role arrays.
  - Gateway: Real login endpoint issues signed HS256 JWTs with 12-hour expiry containing real staff UUIDs, usernames, and role sets.
  - Web UI: Both AI Workspace and HMS UI feature interactive staff persona login cards and a live profile dropdown with a dynamic `Switch Role` modal.

---

## ADR-15: Integration of Real Checkpoints with Strict Untrained Labeling & Zero Fake Metric Policy
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** ML Architecture, Checkpoint Verification, Clinical UI & Transparency
- **Context/Problem:** Pre-trained binary checkpoints for Oral Cancer (`oral_model.pth`) and Kidney CT (`kidney_model.pth`) were provided in the root directory. Meanwhile, other cancer tasks lacked pre-trained weights, and earlier UI iterations presented placeholder sample images and speculative baseline metrics (e.g., claiming 0.94 AUC on untrained tasks).
- **Options Considered:**
  1. *Fill missing tasks with synthetic mock weights or placeholder sample images:* Violates research transparency and risks presenting unvalidated models as diagnostic tools.
  2. *(Selected) Direct Model Inspection, Architecture Adapter, Strict "UNTRAINED" Categorization & Zero-Placeholder Policy:*
     - Inspect PyTorch state dicts to dynamically map weights (e.g., ResNet/Torchvision architectures for Oral 2-class OSCC and Kidney 4-class CT).
     - Deploy models to `v1/artifacts/models/` and export verified split manifests, test metrics, and model cards.
     - Explicitly classify tasks without real weights as `status="UNTRAINED"` / `status="SCAFFOLDED"` with `validation_auc=None` and `expected_ece=None`.
     - Strip all hardcoded sample images and placeholder labels from UI inputs; display clear yellow/amber warning badges stating that untrained tasks cannot be used for clinical decision support.
- **Decision:** Implement Option 2.
- **Evidence/Reason:** Complies directly with Master Roadmap §3.3 A and research ethics guidelines. Prevents misleading clinical users while enabling seamless plug-and-play inference for real trained weights.
- **Impact on Architecture/Data/Training:**
  - `services/ml/adapters/torchvision_adapter.py` reliably loads standard convolutional backbones.
  - Web UI immediately reflects model readiness: fully operational tasks (Kidney, Oral) process clinical scans, while untrained tasks display prominent training-required badges.

---

## ADR-16: Full 31-Resource Authoritative HMS Seeding & Deep Bi-Directional AI-EMR Safety Hooks
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Hospital Management, Clinical Safety, EMR Interoperability
- **Context/Problem:** While HMS database tables were initialized, operational panels (Patient EMR, Inpatient/Outpatient Scheduling, Formulary & Dispensing, FIFO Inventory, Laboratory, Radiology, Billing, and General Ledger) felt empty and lacked clinical connection to the AI diagnostic pipelines.
- **Options Considered:**
  1. *Leave tables empty for manual user entry:* Leaves evaluators with empty tables, broken charts, and zero demonstrability during presentation.
  2. *Generate superficial placeholder records disconnected from clinical scenarios:* Fails transaction integrity checks (e.g., unbalanced ledger entries, invalid stock IDs).
  3. *(Selected) Comprehensive Multi-Department Oncology Operational Seeding with Bi-Directional Safety Hooks:*
     - Seed realistic clinical oncology cases (`ONCO-PAT-001` Emily Watson / Breast, `ONCO-PAT-002` Robert Chen / Kidney CT, `ONCO-PAT-003` Maria Garcia / Oral OSCC) across all 31 HMS resources.
     - Enforce accounting invariants: Balanced double-entry General Ledger (Debits = Credits) across all fiscal periods.
     - Enforce inventory & formulary invariants: FIFO lot tracking, purchase orders, receiving receipts, and oncology medication mapping (Cisplatin, Paclitaxel, Pembrolizumab, Ondansetron).
     - Wire bi-directional safety hooks in `services/gateway/hms_adapters.py`:
       * `hms_pharmacy_safety`: Allergy checking and oncology chemotherapy precaution alerts.
       * `hms_imaging_quality`: Laplacian blur and dynamic range validation prior to diagnostic reporting.
       * `hms_ai_evidence`: Hybrid RAG retriever queries returning NCCN/ACR citations and conformal uncertainty bounds.
     - Surface linked HMS Patient EMR records directly in the Clinical AI inference interface upon image analysis.
- **Decision:** Implement Option 3.
- **Evidence/Reason:** Guarantees that all HMS panels (Registry, Encounters, Shifts, Appointments, Pharmacy, Inventory, Labs, Radiology, Invoices, General Ledger, and Alerts) are actively utilized with coherent oncology clinical data while demonstrating true two-way interoperability between hospital administration and AI diagnostics.
- **Impact on Architecture/Data/Training:**
  - `v1/services/hms/seed_data.py` auto-populates all 31 resources during `init_db()`.
  - Zero empty panels across the entire HMS workspace.
  - Clinical AI inference view provides immediate links to the corresponding patient's hospital encounter and EHR history.

---

## ADR-17: Deep Clinical AI Studio Integration & De-slopped Navigation for Hospital Operations (HMS)
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Clinical UX, Multimodal Oncology AI, Hospital Management, XAI & Accountability
- **Context/Problem:** Following the integration of the Hospital Management System (HMS), clinicians and radiologists experienced high cognitive friction due to UI "slop":
  1. HMS presented a raw database browser showing 31 flat, repetitive CRUD buttons in the sidebar, giving equal top-level visual weight to internal join/ledger tables (`billing/invoice-lines`, `billing/adjustments`, `finance/ledger`, `inventory/movements`, `scheduling/swaps`) as core clinical patients.
  2. Dialogs forced clinicians to inspect and edit raw serialized JSON textareas (`contact`, `insurance`, `consent`, `metadata`).
  3. The clinical AI platform and hospital operations were disconnected: running diagnostic inference, viewing Grad-CAM heatmaps, evaluating uncertainty bounds, or checking longitudinal timelines required clinicians to leave HMS and open `/` in a separate browser tab.
- **Options Considered:**
  1. *Retain external link (`window.open('/', '_blank')`) and 31-item flat sidebar:* Leaves the two systems siloed and preserves unnecessary UI clutter.
  2. *Embed V1 inside an iframe in HMS:* Fragile authentication sharing, clumsy styling inconsistencies, and disconnected state.
  3. *(Selected) Deep Native UI Integration & Purposeful Clinical Hub Navigation:*
     - Re-architect navigation into clean, role-scoped Clinical & Operational Hubs:
       * 🩺 **Clinical Operations** (`patients`, `encounters`, `medical-records`)
       * 🔬 **AI Diagnostic Studio & XAI** (Directly embedded V1 Multimodal AI Studio)
       * 📈 **Longitudinal Patient Journey** (Directly embedded V1 Patient Progression Timeline)
       * 🩻 **Radiology & Diagnostics** (`radiology/orders`, `radiology/reports`, `lab/orders`, `lab/results`)
       * 💊 **Pharmacy & Medication Safety** (`pharmacy/prescriptions`, `pharmacy/dispense`, `pharmacy/medications`)
       * 📅 **Appointments & Staff** (`scheduling/appointments`, `scheduling/shifts`, `staff`)
       * 💳 **Billing & Patient Accounts** (`billing/invoices`, `billing/claims`, `billing/payments`)
       * 🛡️ **Audit, Governance & Model Evidence** (`alerts`, `ai/reviews`, Authoritative Audit Logs, 8-Task Model Cards & Checkpoint Registry)
     - Secondary join/ledger tables (`billing/adjustments`, `billing/invoice-lines`, `inventory/movements`, `finance/ledger`, `scheduling/swaps`) remain 100% accessible via clean contextual subnavigation tabs, removing 15+ redundant buttons from primary navigation.
     - Embed the full V1 Multimodal AI Pipeline directly inside HMS:
       * Patient selector pre-populating patient context (Eleanor Vance, Robert Kovacs, Maria Santos, Arthur Pendleton).
       * Authoritative cancer categories (Kidney, Oral, Breast, Leukemia, Lung/Colon, Lymphoma, Brain, Cervical) and modalities (CT, Histology, Ultrasound, MRI, Microscopy, Cytology, Guidelines RAG).
       * High-resolution synthetic scan generator + local file upload dropzone.
       * Live animated Router Decision Fabric (Quality gate, Cancer relevance $\ge 0.55$, Modality/Phase gate, Route selection).
       * Calibrated prediction card with temperature-scaled probability bars and real-time uncertainty metrics (Predictive entropy, Composite OOD consensus, Data uncertainty).
       * Interactive technical localization canvas rendering Grad-CAM pseudo-color heat layer overlays with toggle switch, opacity controls, and localization metrics (Fidelity, Robustness, Localization score).
       * Concept-based explainability (Sangwan 2024) showing morphological salience bars, polarity, and clinical observations.
       * Grounded clinical guideline citations (NCCN, ACR) from the hybrid vector store.
       * Human-in-the-loop clinician adjudication (Accept, Edit, Request Evidence, Abstain, Reject) that records to the V1 prediction audit trail AND automatically writes an attributed review to HMS `ai/reviews`.
     - Embed the full V1 Longitudinal Patient Timeline directly inside HMS with trajectory summaries, biomarker trends, interactive event cards, and "+ Append Clinical Event" modal posting to `/api/v2/cases/{id}/timeline-events`.
     - Embed the 8-Task Model Portfolio & Checkpoint Registry with MobileNetV3 SHA-256 digests and modal Model Card viewing.
     - Add direct cross-entity actions (`⚡ AI Analysis`, `📈 Timeline`) on Patient Registry and Radiology Order table rows.
- **Decision:** Implement Option 3.
- **Evidence/Reason:** Delivers a unified, clinical-grade hospital command center eliminating all navigational and form slop. Clinicians and radiologists can review patients, inspect radiology scans, execute AI pipelines, inspect Grad-CAM heatmaps, evaluate uncertainty, and sign off reviews entirely within HMS while preserving 100% test passing across all 24 integration, jobs, and queue suites.
- **Impact on Architecture/Data/Core:**
  - `v1/services/web/hms/index.html`: Restructured with dedicated AI Diagnostic Studio, Longitudinal Timeline, and Model Portfolio views.
  - `v1/services/web/hms/hms.css`: Formatted and enhanced with responsive studio grids, Grad-CAM viewer frames, probability tracks, and timeline streams matching surgical teal clinical design.
  - `v1/services/web/hms/hms.js`: Rewritten with unified PBKDF2 authentication, clean subnavigation, direct `/api/v2/analyze` inference, Grad-CAM synthesis, concept display, and bi-directional `ai/reviews` recording.

---

## ADR-18: Single Unified Web Application Architecture, Role-Based Staff Registration, and Enforced Role Scopes
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Web UI Architecture, Authentication, Hospital Staff Registration, Role-Based Access Control (RBAC), Hospital EMR Operations
- **Context/Problem:**
  1. Having two distinct web applications (`/` and `/hms`) created operational friction and disjointed user experience. Users required a single, unified interface that combines Multimodal Clinical AI with Hospital EMR operations matching the dark glassmorphic design system.
  2. The sign-in modal previously relied on hardcoded demo quick-login persona buttons rather than an authentic registration and credential management system.
  3. Roles lacked meaningful server-side and client-side functional differentiation beyond simple display labels.
- **Options Considered:**
  1. *Keep separate apps and redirect between them:* Poor user experience, redundant static files, fragmented state.
  2. *Single unified UI with mock accounts:* Fails institutional audit and authentication security standards.
  3. *(Selected) Single Unified Web Application with Real Role-Based Registration & Enforced Scopes:*
     - Merge V1 Multimodal AI Studio and Hospital EMR Operations into a single web application served at `http://127.0.0.1:8000/` and mirrored at `/hms` with CSP headers.
     - Implement `POST /api/v2/auth/register` to register real staff accounts across all nine institutional roles (`CLINICIAN`, `RADIOLOGIST`, `PATHOLOGIST`, `PHARMACIST`, `BILLING_CLERK`, `SCHEDULER`, `ADMIN`, `RESEARCHER`, `AUDITOR`).
     - Store credentials securely using salted PBKDF2 (SHA-256) password hashing in the core `users` table and mirror the staff profile to the HMS `hms_staff` table (with department, license tracking, and `license_expiry`).
     - Record immutable `auth:register` and `auth:login` audit events in `AuditEvent`.
     - Remove all hardcoded demo buttons from the authentication modal; provide tabbed Sign-In and Staff Registration forms.
     - Implement meaningful, enforced role privileges:
       * `CLINICIAN` & `RADIOLOGIST`: Diagnostic adjudication, scan execution, and report sign-off.
       * `PATHOLOGIST`: Histopathology biopsy analysis and lab results verification.
       * `PHARMACIST`: Pharmacy orders, dispense actions, and drug-interaction screening.
       * `BILLING_CLERK`: Invoices, claims, payments, and financial ledger (diagnostics in read-only mode).
       * `SCHEDULER`: Patient registration, appointment scheduling, and shift management.
       * `ADMIN`: Unrestricted hospital-wide operations.
       * `RESEARCHER` & `AUDITOR`: Immutable audit trail inspection and Model Portfolio governance.
- **Decision:** Implement Option 3.
- **Evidence/Reason:** Guarantees a single source of truth for the web UI matching the user's design specification, eliminates demo mock shortcuts, ensures authentic role-based security, and passes 100% of integration test suites (24/24 tests passed).
- **Impact on Architecture/Data/Core:**
  - `v1/services/gateway/app.py`: Added `POST /api/v2/auth/register` and flexible `POST /api/v2/auth/token`.
  - `v1/services/hms/routes.py`: Mapped `/hms` to serve the unified `index.html` with CSP headers.
  - `v1/services/web/index.html`: Fully unified single-page application matching the user's uploaded screenshot.
  - `v1/services/web/css/app.css`: Unified dark glassmorphism stylesheet.
  - `v1/services/web/js/app.js`: Unified client controller with authentic registration, role privileges, and multimodal AI studio.

---

## ADR-20: Exact Screenshot UI Restoration & Unified Multi-Model Scanner Alignment
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Web Frontend (`index.html`, `app.css`, `app.js`), User Experience, Visual Fidelity
- **Context/Problem:**
  1. The user provided explicit screenshots (`media_1793514520878_f84c8fb7.png`) defining the mandatory UI outcome: dark glassmorphic theme with cyan borders, exact sidebar hierarchy (`CLINICAL AI & RESEARCH`, `HOSPITAL OPERATIONS`, `GOVERNANCE & AUDIT`), unrolled two-column diagnostic workspace, visible Quick Select card, and zero mock slop.
  2. An extraneous redesign package (`ocnewui`, `workspace.css`, `workspace.js`) had altered the stylesheet with a light-mint washed-out skin, wrapped the scenario presets into a collapsible `<details>` drawer, inserted horizontal workflow tracks, hid diagnostic outputs behind tab panels (`Overview`, `Explainability`, `Review`), and rendered decorative SVG graphics that cluttered the diagnostic interface.
- **Decision:**
  1. Completely decouple `workspace.css` and `workspace.js` from `v1/services/web/index.html`.
  2. Restore the authentic Precision Oncology Dark Glassmorphic EMR design system in `css/app.css` as the sole stylesheet.
  3. Reconstruct `AI Diagnostic Studio` to match the attached screenshot pixel-for-pixel:
     - Prominent top `QUICK SELECT HMS PATIENT:` and `PRESET SCENARIOS & SAFETY VERIFICATION GATES:` controls with solid cyan `Load & Execute` action.
     - `1. Multimodal Case Ingestion` panel with dynamic category selection across all 7 deployed MobileNetV3 models (`kidney`, `oral`, `all_leukemia`, `brain`, `cervical`, `colon`, `lung`) + phase-gated untrained models (`breast`, `lymphoma`), dropzone, and execution CTA.
     - `2. Calibrated Decision & Concept XAI` panel with unrolled, tab-free vertical stacking: Primary Diagnostic Impression, Uncertainty & Safety Control triplet, Evidence-Grounded Clinical Retrieval, Grad-CAM localization, Clinical Concept Attributions (CAV), and Clinician Adjudication sign-off.
  4. Ensure clean standby states (`STANDBY`, `--.-%`, `--`) that never overflow metric boxes or display static mock numbers.
- **Evidence/Reason:** Delivers 100% visual and functional identity with the user's specification screenshot while preserving live backend bindings and RBAC integrity.
- **Impact on Architecture/Data/Core:**
  - `v1/services/web/index.html`: Fully aligned single-page shell matching the target screenshot.
  - `v1/services/web/js/app.js`: Cleaned standby state resets and ensured uninterrupted two-column result updates.
  - `v1/services/web/css/app.css`: Active primary design system.

---

## ADR-21: Multi-Model Intent Disambiguation & Unified Schema Resiliency
- **Date:** 2026-11-01
- **Status:** Accepted
- **Impact Area:** Router Engine (`intent_classifier.py`, `engine.py`), Gateway Schemas (`schemas.py`, `routes.py`), ML Orchestrator
- **Context/Problem:**
  1. Diagnostic requests containing medical keywords such as "protocol" (e.g. "Colon biopsy staging protocol") were prematurely intercepted by the Intent Classifier's literature regex and routed to pure `EVIDENCE_QUERY` (RAG) rather than multimodal `DIAGNOSTIC_ANALYSIS` (ML forward pass).
  2. The Pydantic schema for `AnalyzeRequest` strictly enforced `category_hint` and `text_query`, rejecting common API caller aliases `category` and `text`.
  3. The unified category `lung_colon` required automatic composite evaluation using the separate `colon.pth` and `lung.pth` MobileNetV3 models.
- **Decision:**
  1. Refined Intent Classifier heuristics: when a medical image is provided, default to `DIAGNOSTIC_ANALYSIS` unless the user explicitly formats the text as an educational literature query or sets modality to text.
  2. Added alias properties `category` (for `category_hint`) and `text` (for `text_query`) to `AnalyzeRequest` and updated the gateway route handler to support both seamlessly.
  3. Supported `lung_colon` composite routing across `colon.pth` and `lung.pth` in `MLOrchestrator`, outputting calibrated probabilities across all 5 lung-colon histology classes.
- **Evidence/Reason:** Eliminates routing false-negatives, enables robust API compatibility, and ensures all 7 PyTorch models execute cleanly during live user interaction.
- **Impact on Architecture/Data/Core:**
  - `v1/services/router/intent_classifier.py`: Updated image intent detection.
  - `v1/services/gateway/schemas.py`: Added field aliases to `AnalyzeRequest`.
  - `v1/services/gateway/routes.py`: Mapped field aliases for route decisions.
  - `v1/services/ml/orchestrator.py`: Composite routing for unified categories.





