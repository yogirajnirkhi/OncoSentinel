# OncoSentinel v2.0 + Hospital Management System (HMS)
## Complete Frontend Architecture, UI Specification & Schema Mapping

> **Target Audience:** AI or Frontend Engineers tasked with designing and implementing a modern, world-class Clinical AI & Hospital Management Web Application.
> **Source:** Generated directly from the OncoSentinel v2.0 OpenAPI 3.1.0 engine and production codebase.

---

## Table of Contents
1. [System Architecture & The 'One Spine' Clinical Workflow](#1-system-architecture--the-one-spine-clinical-workflow)
2. [Role-Based Access Control (RBAC) Matrix](#2-role-based-access-control-rbac-matrix)
3. [Clinical Safety & Truthful UI Principles](#3-clinical-safety--truthful-ui-principles)
4. [Complete Screen & Page Specifications (10 Views)](#4-complete-screen--page-specifications-10-views)
5. [API Endpoints Directory](#5-api-endpoints-directory)
6. [Complete Schema Reference Dictionary](#6-complete-schema-reference-dictionary)
7. [Seeded Clinical Data & Test Scenarios](#7-seeded-clinical-data--test-scenarios)

---

## 1. System Architecture & The 'One Spine' Clinical Workflow
OncoSentinel v2.0 unites an advanced deep learning oncology diagnosis engine (MobileNetV3 multi-task vision backbone + Grounded RAG + Conformal Uncertainty + Grad-CAM XAI) with a rigorous Hospital Management System (HMS).

### The 'One Spine' Principle
All clinical operations must flow continuously across the unified backbone:
```
Registered Patient (MRN)
       │
       ▼
Clinical Encounter (ENC-xxxx)
       │
       ▼
Diagnostic Study / Order (Radiology CT/MRI or Pathology Lab)
       │
       ▼
AI Studio Inference (Category routing, Conformal Calibration, Grad-CAM Heatmap)
       │
       ▼
Clinician Adjudication (ACCEPT / OVERRIDE / SECOND_READ)
       │
       ├───────────────────────────────┐
       ▼                               ▼
Patient Timeline Event        Immutable Audit Provenance Trail
  (CLINICIAN_SIGN_OFF)          (Actor, Role, Action, Patient MRN)
```

## 2. Role-Based Access Control (RBAC) Matrix
The application supports 5 primary clinical and operational roles. Navigation tabs, screen sections, and mutating buttons MUST be conditionally visible and strictly enforced on both frontend and backend:

| Page / Feature | CLINICIAN | RADIOLOGIST | PHARMACIST | BILLING_CLERK | ADMIN |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **AI Diagnostic Studio** | Full (Run & Sign-off) | Full (Run & Sign-off) | Hidden | Hidden | Full |
| **Clinical Guidelines (RAG)** | Full | Full | Read-only | Hidden | Full |
| **Patient Timeline** | Full (View & Export) | Full (View) | Read-only | Hidden | Full |
| **Patient Registry** | Full (View & Add) | Read-only | Read-only | Read-only | Full |
| **Encounters & Notes** | Full (Create & Progress) | View-only | Hidden | Hidden | Full |
| **Radiology & Lab** | Order & View | Sign Reports & Run Scans | Hidden | Hidden | Full |
| **Pharmacy & Stock** | Prescribe Only | Hidden | Full (Dispense FIFO & Stock) | Hidden | Full |
| **Billing & Finance** | Hidden | Hidden | Hidden | Full (Invoices & Payments) | Full |
| **Audit Trail** | View Own Actions | View Own Actions | View Own Actions | View Own Actions | Full (All Records) |
| **Model Portfolio** | Read Cards & Metrics | Read Cards | Hidden | Hidden | Full (System Metrics) |

### Dev Role Switcher (`POST /api/v2/auth/dev-switch`)
The UI top navigation bar includes an instant Dev Role Switcher allowing immediate switching between test clinical accounts:
- `CLINICIAN`: Dr. Sarah Chen, MD (Medical Oncology)
- `RADIOLOGIST`: Dr. Rajesh Patel, MD (Diagnostic Radiology)
- `PHARMACIST`: Alex Rivera, PharmD, BCOP (Oncology Pharmacy)
- `BILLING_CLERK`: Mark Davis, CRCR (Patient Financial Services)
- `ADMIN`: Clara Vance, MHA (Hospital Administration)

## 3. Clinical Safety & Truthful UI Principles
1. **Never Claim What Data Does Not Support:**
   - If a model category is untrained (`breast_ultrasound`, `lymphoma_histology`), the UI **MUST** display `REFUSED - Untrained Modality` and clear reasoning. **NEVER** render dummy or placeholder tumor percentages (such as `--%`, `0.0%`, or simulated confidence).
2. **No Fake Grounded Verifications:**
   - In Guidelines RAG, when semantic similarity is low or no citations exist, the UI must say `"No matching guideline found for this query"`. It must **NEVER** display a green `(VERIFIED)` badge without genuine citations.
3. **EHR Pre-Prescribing Allergy Guard:**
   - Before submitting a new prescription in Pharmacy, the UI/backend cross-references patient allergy records. Eleanor Vance (`MRN-2026-KD-001`) has a documented `PENICILLIN` allergy; Arthur Pendleton has a `SULFA` allergy. Prescriptions for matching allergen classes must be intercepted with an alert modal.
4. **Balanced Accounting Badge:**
   - In Billing & Finance, the summary card must verify the double-entry accounting equation (`Total Debits = Total Credits`). Display a verified status chip: `DR = CR ($2,175.00 - Balanced)`. Do not display `$0.00 / --%` placeholders when invoices are not selected.
5. **Clean Presentation:**
   - Remove all internal test markers (`FR-xx`, `NFR-xx`, `SRS`) from the user-facing UI.

## 4. Complete Screen & Page Specifications (10 Views)

### View 1: Global App Shell & Header
- **Components:** Top app bar with OncoSentinel branding, active environment pill, status chip ('6 of 8 Models Active'), critical alert notification bell with unread badge counter, Dev Role Switcher select (`#devRoleSelect`), and active user profile avatar with name and department.
- **Sidebar Navigation:** Vertical navigation containing icons and labels for all 10 views, dynamically showing/hiding items based on active role permissions.
- **Critical Alerts Dropdown:** Lists active critical findings (e.g., 'Large renal mass with vascular invasion', 'Hyperkalemia 6.8 mEq/L'). Each alert features an '✓ Acknowledge' button calling `DELETE /api/v2/hms/alerts/{id}`.

### View 2: AI Diagnostic Studio (`#viewAiStudio`)
- **Purpose:** Central diagnostic workspace for running multi-task AI scans and recording clinician adjudications.
- **Components:**
- - Case Selector: Unified dropdown (`#caseIdSelect`) populated with registered patients from `/api/v2/hms/patients/query` + Custom Upload option.
- - Modality & Body Site Selector: CT, MRI, Histopathology, Cytology, Microscopy, Ultrasound.
- - Image Dropzone & DICOM Preview: Supports drag-and-drop or file upload. Shows thumbnail and Laplacian blur variance indicator (`PASS ✓ Blur Variance > 100`).
- - Inference Trigger: 'Run Diagnostic Analysis' button (`POST /api/v2/analyze`).
- - Results Display:
-   * Top-1 Diagnosis with Calibrated Confidence & Probability distribution bar chart.
-   * Safety & Risk Tier: High Risk (Red), Moderate (Amber), Low (Green), or Refused (Gray).
-   * Conformal Uncertainty Breakdown: Epistemic, Aleatoric, Shannon Entropy, Conformal p-value, OOD Mahalanobis distance.
-   * Explainable AI (Grad-CAM): Interactive overlay heatmap slider toggling between raw scan and Grad-CAM activation map.
-   * Clinician Adjudication Action Bar: Three primary action buttons: `ACCEPT`, `OVERRIDE`, and `SECOND_READ` with clinical notes textarea (`POST /api/v2/predictions/{id}/review`).

### View 3: Clinical Guidelines Grounded RAG (`#viewRag`)
- **Purpose:** Evidence-grounded oncology guideline retrieval (NCCN, ASCO, ESMO, WHO).
- **Components:**
- - Category Topic Chips: 'All', 'Kidney', 'Oral', 'Leukemia', 'Brain', 'Cervical', 'Lung/Colon' to narrow semantic vector search.
- - Search Input: Clinical query bar with auto-suggestions.
- - Grounded Synthesis Panel: Synthesized answer with inline citation tags [1], [2].
- - Evidence Cards: Cards listing Guideline Source, Edition/Version, Section, Similarity Score, and verbatim excerpt.
- - Verification State Chip: 'VERIFIED GROUNDED' (green) or 'UNVERIFIED / INSUFFICIENT EVIDENCE' (gray/amber).

### View 4: Patient Longitudinal Timeline (`#viewTimeline`)
- **Purpose:** Complete chronological patient journey across encounters, scans, treatments, and decisions.
- **Components:**
- - Patient Selector Dropdown (`#timelinePatientSelect`): Switches timeline between registered patients.
- - Dynamic Summary Metrics:
-   * Total Milestones count.
-   * Prior Cancer Treatments count.
-   * Missingness Flags count.
-   * Longitudinal Time Span (e.g. 'Nov 2025 - Mar 2026').
- - Interactive Vertical Timeline: Event nodes categorized by event type (`CLINICIAN_SIGN_OFF`, `ENCOUNTER`, `RADIOLOGY_SCAN`, `LAB_RESULT`, `CHEMOTHERAPY_DISPENSED`).
- - Export FHIR Bundle Button: Exports patient history as a validated FHIR R4 Bundle (`GET /api/v2/interop/fhir/timeline/{case_id}`).

### View 5: Patient Registry (`#viewRegistry`)
- **Purpose:** Hospital master patient index (MPI) and demographic management.
- **Components:**
- - Search & Filter Bar: Search by MRN, given name, family name, gender.
- - 'Register New Patient' Modal & Button (`POST /api/v2/hms/patients`).
- - Patient Table: Columns for MRN, Full Name, Birth Date, Age, Gender, Consent Tier Badge (`FULL_CLINICAL`, `ANONYMIZED_RESEARCH`, `OPT_OUT`), Last Visit, and Action Menu.
- - Row Actions: 'View Timeline', 'Open in AI Studio', 'New Encounter'.

### View 6: Encounters & Clinical Notes (`#viewEncounters`)
- **Purpose:** Inpatient and outpatient clinical encounters, appointments, and oncology progress notes.
- **Components:**
- - Filter Bar: Filter by Patient (`#encPatientFilter`) and search by Encounter ID / Reason (`#encSearchInput`).
- - Encounter Cards / Table: Encounter ID (`ENC-2026-0001`), Class (Ambulatory, Inpatient, Emergency), Status badge (`scheduled`, `in_progress`, `completed`), Attending Physician, Start/End times.
- - Action: 'Mark Arrived' button to advance scheduled appointments to in-progress.
- - Clinical Notes Drawer: Displays physician consultation notes, physical findings, and assessment plans.

### View 7: Radiology & Laboratory Services (`#viewRadiology`)
- **Purpose:** Diagnostic imaging orders, DICOM study review, and lab pathology reports.
- **Components:**
- - Split Tabs: 'Radiology Imaging' and 'Laboratory Pathology'.
- - Critical Findings Alert Banner: Prominently highlights critical panic values.
- - Radiology Orders Table: Order ID (`RAD-2026-0001`), Modality, Body Site, Priority (STAT, Routine), Image Quality Gate (`PASS ✓`), and Report Status.
- - Report Signing Modal: Exclusive to `RADIOLOGIST` and `ADMIN` (`POST /api/v2/hms/radiology/reports`).
- - Lab Orders & Results Table: Order ID (`LAB-2026-0001`), Test Name (e.g. CBC, Renal Function, Ki-67), Result Value, Reference Range, and Abnormal Flag.

### View 8: Pharmacy & Medication Inventory (`#viewPharmacy`)
- **Purpose:** Clinical chemotherapy ordering, FIFO batch dispensing, and real-time inventory management.
- **Components:**
- - 'New Prescription' Button & Modal: Restricted to `CLINICIAN` and `ADMIN`. Includes automated EHR allergy guard checking for Penicillin/Sulfa conflicts.
- - Active Prescriptions Queue: Prescription ID, Patient MRN, Medication Name, Dosage, Schedule, Status (`pending`, `dispensed`).
- - Dispense Action: Restricted to `PHARMACIST` and `ADMIN` with automated FIFO lot matching (`POST /api/v2/hms/pharmacy/dispense`).
- - Medication Stock Grid: Item code, Brand name, Generic name, Form, Quantity on hand, Reorder threshold.
- - Low-Stock Warning Banner: Highlights items below reorder point (e.g., Oxaliplatin - 3 vials remaining).

### View 9: Billing & Financial Ledger (`#viewBilling`)
- **Purpose:** Hospital revenue cycle management, claims processing, and double-entry accounting ledger.
- **Components:**
- - Balanced Ledger Status Chip: Displays verified `DR = CR ($2,175.00 - Balanced)`. Replaces empty `$0.00 / --%` placeholders.
- - Invoices Table: Invoice number, Patient MRN, Total amount, Insurance coverage, Patient copay, Status (`draft`, `issued`, `paid`, `disputed`).
- - 'Create Invoice' Modal: Itemized charge capture (consultation, scan, chemotherapy infusion).
- - Payments & Claims Tab: Insurance claim submission and payment receipt history.
- - Double-Entry General Ledger: Transaction date, Account Name, Debit, Credit, Running Balance.

### View 10: Audit Provenance Trail (`#viewAudit`)
- **Purpose:** Immutable regulatory compliance audit log tracking every data mutation across the platform.
- **Components:**
- - Filter Bar: Filter by Actor ID, Role (`CLINICIAN`, `ADMIN`, etc.), Patient MRN, and Date Range.
- - Audit Records Table: Columns for Timestamp (ISO UTC), Trace / Request ID, Actor ID, Active Role, Action (`CLINICIAN_REVIEW:ACCEPT`, `patients:create`, etc.), Service Domain, and Patient MRN.
- - Provenance Detail Modal: Inspect full JSON request payload, user-agent, IP address, and mutation delta.
- - Role Boundary: `ADMIN` views all hospital transactions; staff roles view only their own records.

### View 11: Model Portfolio & Technical Cards (`#viewModelPortfolio`)
- **Purpose:** Governance registry of deployed deep learning checkpoints, performance metrics, and model cards.
- **Components:**
- - Header Status Chip: Dynamically displays active count: '6 of 8 Models Active'.
- - Portfolio Grid / Table: 8 Tasks:
-   1. `kidney_ct`: ACTIVE (MobileNetV3-Small, 96.4% Acc, 0.962 Macro F1, SHA-256)
-   2. `oral_cancer`: ACTIVE (MobileNetV3-Small, 94.1% Acc, 0.938 Macro F1, SHA-256)
-   3. `leukemia_microscopy`: ACTIVE (MobileNetV3-Small, 95.8% Acc, 0.955 Macro F1, SHA-256)
-   4. `brain_mri`: ACTIVE (MobileNetV3-Small, 97.1% Acc, 0.969 Macro F1, SHA-256)
-   5. `cervical_cytology`: ACTIVE (MobileNetV3-Small, 93.6% Acc, 0.931 Macro F1, SHA-256)
-   6. `lung_colon_histology`: ACTIVE (MobileNetV3-Small, 98.2% Acc, 0.980 Macro F1, SHA-256)
-   7. `breast_ultrasound`: UNTRAINED (Roadmap Phase 3 - Ingestion Refusal Enabled)
-   8. `lymphoma_histology`: UNTRAINED (Roadmap Phase 3 - Ingestion Refusal Enabled)
- - Model Card Drawer / Modal: Formatted Markdown viewer rendering §22.2 model card documentation (Intended Use, Training Set, Out-of-Distribution Caveats, Performance Tables).
- - Export Button: 'Export Model Report' button generating full technical report.

## 5. API Endpoints Directory
Summary of primary API endpoints for frontend consumption:

| Category | HTTP Method | Endpoint Path | Description | Access Roles |
| :--- | :---: | :--- | :--- | :--- |
| Auth | `POST` | `/api/v2/auth/dev-switch` | Quick role switch for dev and test | All |
| Auth | `GET` | `/api/v2/auth/users` | Directory of seeded staff accounts | All |
| AI Studio | `POST` | `/api/v2/analyze` | Submit image/query for oncology inference | CLINICIAN, RADIOLOGIST, ADMIN |
| AI Studio | `POST` | `/api/v2/predictions/{id}/review` | Record clinician adjudication decision | CLINICIAN, RADIOLOGIST, ADMIN |
| AI Studio | `GET` | `/api/v2/predictions/{id}/uncertainty` | Retrieve conformal uncertainty metrics | CLINICIAN, RADIOLOGIST, ADMIN |
| AI Studio | `GET` | `/api/v2/predictions/{id}/explanation` | Retrieve Grad-CAM heatmap & XAI attributions | CLINICIAN, RADIOLOGIST, ADMIN |
| Guidelines RAG | `POST` | `/api/v2/rag/query` | Semantic search across clinical guidelines | CLINICIAN, RADIOLOGIST, PHARMACIST, ADMIN |
| Timeline | `GET` | `/api/v2/cases/{id}/timeline` | Get chronological longitudinal timeline | CLINICIAN, RADIOLOGIST, PHARMACIST, ADMIN |
| Timeline | `POST` | `/api/v2/cases/{id}/timeline-events` | Append manual timeline event | CLINICIAN, ADMIN |
| Timeline | `GET` | `/api/v2/interop/fhir/timeline/{case_id}` | Export patient timeline as FHIR R4 Bundle | CLINICIAN, ADMIN |
| HMS Patients | `POST` | `/api/v2/hms/patients/query` | Query/filter patient directory | CLINICIAN, RADIOLOGIST, PHARMACIST, BILLING, ADMIN |
| HMS Patients | `POST` | `/api/v2/hms/patients` | Register new patient | CLINICIAN, ADMIN |
| HMS Encounters | `POST` | `/api/v2/hms/encounters/query` | Query hospital encounters | CLINICIAN, RADIOLOGIST, ADMIN |
| HMS Encounters | `POST` | `/api/v2/hms/encounters` | Create encounter | CLINICIAN, ADMIN |
| HMS Encounters | `PUT` | `/api/v2/hms/encounters/{id}` | Update encounter status (e.g. mark arrived) | CLINICIAN, ADMIN |
| HMS Radiology | `POST` | `/api/v2/hms/radiology/orders/query` | List radiology orders | CLINICIAN, RADIOLOGIST, ADMIN |
| HMS Radiology | `POST` | `/api/v2/hms/radiology/orders` | Order diagnostic imaging scan | CLINICIAN, ADMIN |
| HMS Radiology | `POST` | `/api/v2/hms/radiology/reports` | Sign diagnostic radiology report | RADIOLOGIST, ADMIN |
| HMS Lab | `POST` | `/api/v2/hms/lab/orders/query` | List laboratory orders | CLINICIAN, RADIOLOGIST, ADMIN |
| HMS Lab | `POST` | `/api/v2/hms/lab/orders` | Order lab pathology / blood test | CLINICIAN, ADMIN |
| HMS Pharmacy | `POST` | `/api/v2/hms/pharmacy/prescriptions/query` | List active prescriptions | CLINICIAN, PHARMACIST, ADMIN |
| HMS Pharmacy | `POST` | `/api/v2/hms/pharmacy/prescriptions` | Prescribe oncology medications (Allergy Checked) | CLINICIAN, ADMIN |
| HMS Pharmacy | `POST` | `/api/v2/hms/pharmacy/dispense` | Dispense medication via FIFO batching | PHARMACIST, ADMIN |
| HMS Inventory | `GET` | `/api/v2/hms/inventory/low-stock` | Get stock items below reorder threshold | PHARMACIST, ADMIN |
| HMS Billing | `POST` | `/api/v2/hms/billing/invoices/query` | Query patient invoices | BILLING_CLERK, ADMIN |
| HMS Billing | `POST` | `/api/v2/hms/billing/invoices` | Create new patient invoice | BILLING_CLERK, ADMIN |
| HMS Finance | `GET` | `/api/v2/hms/finance/ledger` | Get balanced double-entry ledger entries | BILLING_CLERK, ADMIN |
| Alerts | `GET` | `/api/v2/hms/alerts` | Get unread critical clinical alerts | All Roles |
| Alerts | `DELETE` | `/api/v2/hms/alerts/{id}` | Acknowledge critical alert | All Roles |
| Audit | `GET` | `/api/v2/audit` | Query immutable audit provenance logs | All Roles (Role-Scoped) |
| Models | `GET` | `/api/v2/training/queue` | Get 8-task portfolio metrics and statuses | All Roles |
| Models | `GET` | `/api/v2/model-cards/{task_id}` | Get Markdown Model Card documentation | All Roles |

## 6. Complete Schema Reference Dictionary
All request and response data models defined in OpenAPI 3.1.0:

### Schema: `AiReviewsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `evidence_id` | `string` | ✓ Yes | Evidence Id |
| `decision` | `string` | ✓ Yes | Decision |
| `comment` | `string` | ✓ Yes | Comment |

---

### Schema: `AiReviewsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `evidence_id` | `string` | ✓ Yes | Evidence Id |
| `decision` | `string` | ✓ Yes | Decision |
| `comment` | `string` | ✓ Yes | Comment |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `AlertsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `kind` | `string` | ✓ Yes | Kind |
| `resource_id` | `string` | ✓ Yes | [format: uuid] Resource id |
| `severity` | `string` | ✓ Yes | Severity |
| `message` | `string` | ✓ Yes | Message |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `AnalyzeRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `case_id` | `string \| null` | Optional | Case Id |
| `category_hint` | `string \| null` | Optional | breast, kidney, etc. |
| `modality` | `string \| null` | Optional | Modality |
| `text_query` | `string \| null` | Optional | Text Query |
| `image_b64` | `string \| null` | Optional | Image B64 |
| `patient_context` | `object \| null` | Optional | Patient Context |

---

### Schema: `AnalyzeResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `request_id` | `string` | ✓ Yes | Request Id |
| `prediction_id` | `string \| null` | Optional | Prediction Id |
| `case_id` | `string` | ✓ Yes | Case Id |
| `route` | `string` | ✓ Yes | Route |
| `category` | `string \| null` | Optional | Category |
| `top1_class` | `string \| null` | Optional | Top1 Class |
| `top1_confidence` | `number \| null` | Optional | Top1 Confidence |
| `calibrated_probabilities` | `object \| null` | Optional | Calibrated Probabilities |
| `raw_probabilities` | `object \| null` | Optional | Raw Probabilities |
| `uncertainty` | `[`UncertaintyDTO`](#schema-uncertaintydto) \| null` | Optional |  |
| `explanation` | `[`ExplanationDTO`](#schema-explanationdto) \| null` | Optional |  |
| `rag_response` | `string \| null` | Optional | Rag Response |
| `cited_sources` | `array` | Optional | Cited Sources |
| `evidence_cards` | `array` | Optional | Evidence Cards |
| `safety_state` | `string` | ✓ Yes | Safety State |
| `status_message` | `string` | ✓ Yes | Status Message |

---

### Schema: `BillingAdjustmentsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `amount` | `number \| string` | ✓ Yes | Amount |
| `reason` | `string` | ✓ Yes | Reason |
| `reverses_id` | `string \| null` | Optional | Reverses Id |

---

### Schema: `BillingAdjustmentsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `amount` | `string` | ✓ Yes | Amount |
| `reason` | `string` | ✓ Yes | Reason |
| `reverses_id` | `string \| null` | Optional | Reverses Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `BillingChargeItemsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `amount` | `number \| string` | ✓ Yes | Amount |
| `coding_system` | `string` | ✓ Yes | Coding System |
| `active` | `boolean \| null` | Optional | Active |

---

### Schema: `BillingChargeItemsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `amount` | `string` | ✓ Yes | Amount |
| `coding_system` | `string` | ✓ Yes | Coding System |
| `active` | `boolean \| null` | Optional | Active |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `BillingChargeItemsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `code` | `string \| null` | Optional | Code |
| `name` | `string \| null` | Optional | Name |
| `amount` | `number \| string \| null` | Optional | Amount |
| `coding_system` | `string \| null` | Optional | Coding System |
| `active` | `boolean \| null` | Optional | Active |

---

### Schema: `BillingClaimsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `payer` | `string` | ✓ Yes | Payer |
| `reference` | `string` | ✓ Yes | Reference |
| `evidence_uri` | `string` | ✓ Yes | Evidence Uri |
| `status` | `string` | Optional | Status |

---

### Schema: `BillingClaimsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `payer` | `string` | ✓ Yes | Payer |
| `reference` | `string` | ✓ Yes | Reference |
| `evidence_uri` | `string` | ✓ Yes | Evidence Uri |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `BillingInvoiceLinesResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `charge_item_id` | `string` | ✓ Yes | [format: uuid] Charge item id |
| `code` | `string` | ✓ Yes | Code |
| `quantity` | `string` | ✓ Yes | Quantity |
| `unit_price` | `string` | ✓ Yes | Unit Price |
| `amount` | `string` | ✓ Yes | Amount |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `BillingInvoicesCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `lines` | `any` | ✓ Yes | Lines |
| `due_date` | `string` | ✓ Yes | [format: date] Due date |
| `currency` | `string` | Optional | Currency |

---

### Schema: `BillingInvoicesResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `lines` | `any` | ✓ Yes | Lines |
| `due_date` | `string` | ✓ Yes | [format: date] Due date |
| `currency` | `string` | Optional | Currency |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |
| `total` | `string` | ✓ Yes | Total |
| `number` | `string` | ✓ Yes | Number |

---

### Schema: `BillingPaymentsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `amount` | `number \| string` | ✓ Yes | Amount |
| `method` | `string` | ✓ Yes | Method |
| `reference` | `string` | ✓ Yes | Reference |

---

### Schema: `BillingPaymentsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `invoice_id` | `string` | ✓ Yes | [format: uuid] Invoice id |
| `amount` | `string` | ✓ Yes | Amount |
| `method` | `string` | ✓ Yes | Method |
| `reference` | `string` | ✓ Yes | Reference |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `ClinicianReviewRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `action` | `string` | ✓ Yes | ACCEPT | REJECT | EDIT | REQUEST_EVIDENCE | ABSTAIN |
| `notes` | `string \| null` | Optional | Notes |
| `edited_diagnosis` | `string \| null` | Optional | Edited Diagnosis |

---

### Schema: `ClinicianReviewResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `prediction_id` | `string` | ✓ Yes | Prediction Id |
| `clinician_action` | `string` | ✓ Yes | Clinician Action |
| `status` | `string` | ✓ Yes | Status |
| `timestamp` | `string` | ✓ Yes | [format: date-time]  |

---

### Schema: `DevRoleSwitchRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `role` | `string \| null` | Optional | Role |

---

### Schema: `EncountersCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `department` | `string` | ✓ Yes | Department |
| `attending_id` | `string` | ✓ Yes | Attending Id |
| `started_at` | `string` | ✓ Yes | [format: date-time] Started at |
| `ended_at` | `string \| null` | Optional | Ended At |
| `status` | `string` | Optional | Status |

---

### Schema: `EncountersResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `department` | `string` | ✓ Yes | Department |
| `attending_id` | `string` | ✓ Yes | Attending Id |
| `started_at` | `string` | ✓ Yes | [format: date-time] Started at |
| `ended_at` | `string \| null` | Optional | Ended At |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `EncountersUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `patient_id` | `string \| null` | Optional | Patient Id |
| `department` | `string \| null` | Optional | Department |
| `attending_id` | `string \| null` | Optional | Attending Id |
| `started_at` | `string \| null` | Optional | Started At |
| `ended_at` | `string \| null` | Optional | Ended At |
| `status` | `string \| null` | Optional | Status |

---

### Schema: `ExplanationDTO`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `what` | `string` | ✓ Yes | What |
| `where_region` | `string` | ✓ Yes | Where Region |
| `why` | `array` | ✓ Yes | Why |
| `supporting_evidence` | `array` | ✓ Yes | Supporting Evidence |
| `contradicting_evidence` | `array` | ✓ Yes | Contradicting Evidence |
| `confidence_narrative` | `string` | ✓ Yes | Confidence Narrative |
| `model_evidence_section` | `string` | ✓ Yes | Model Evidence Section |
| `guideline_evidence_section` | `string` | ✓ Yes | Guideline Evidence Section |
| `generated_synthesis_section` | `string` | ✓ Yes | Generated Synthesis Section |
| `fidelity_score` | `number` | ✓ Yes | Fidelity Score |
| `robustness_score` | `number` | ✓ Yes | Robustness Score |
| `localization_score` | `number` | ✓ Yes | Localization Score |
| `audit_heatmap_uri` | `string \| null` | Optional | Audit Heatmap Uri |

---

### Schema: `FederatedRoundRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `category` | `string` | Optional | Category |
| `participating_sites` | `integer` | Optional | Participating Sites |

---

### Schema: `FederatedRoundResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `round_id` | `integer` | ✓ Yes | Round Id |
| `participating_sites` | `array` | ✓ Yes | Participating Sites |
| `total_local_samples` | `integer` | ✓ Yes | Total Local Samples |
| `global_model_version` | `string` | ✓ Yes | Global Model Version |
| `pre_round_loss` | `number` | ✓ Yes | Pre Round Loss |
| `post_round_loss` | `number` | ✓ Yes | Post Round Loss |
| `unseen_site_auc` | `number` | ✓ Yes | Unseen Site Auc |
| `out_of_site_improvement_pct` | `number` | ✓ Yes | Out Of Site Improvement Pct |
| `status` | `string` | ✓ Yes | Status |

---

### Schema: `FinanceLedgerResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `transaction_id` | `string` | ✓ Yes | [format: uuid] Transaction id |
| `account` | `string` | ✓ Yes | Account |
| `debit` | `string` | ✓ Yes | Debit |
| `credit` | `string` | ✓ Yes | Credit |
| `source_id` | `string` | ✓ Yes | [format: uuid] Source id |
| `period` | `string` | ✓ Yes | Period |
| `reverses_id` | `string \| null` | Optional | Reverses Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `FinancePeriodsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `period` | `string` | ✓ Yes | Period |
| `reason` | `string` | ✓ Yes | Reason |

---

### Schema: `FinancePeriodsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `period` | `string` | ✓ Yes | Period |
| `reason` | `string` | ✓ Yes | Reason |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `HMSImagingScanRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `case_id` | `string \| null` | Optional | Case Id |
| `category_hint` | `string \| null` | Optional | breast, kidney, etc. |
| `modality` | `string` | ✓ Yes | Modality |
| `text_query` | `string \| null` | Optional | Text Query |
| `image_b64` | `string` | ✓ Yes | Image B64 |
| `patient_context` | `object \| null` | Optional | Patient Context |
| `patient_id` | `string` | ✓ Yes | Patient Id |
| `encounter_id` | `string` | ✓ Yes | Encounter Id |
| `radiology_order_id` | `string \| null` | Optional | Radiology Order Id |
| `category` | `string` | ✓ Yes | Category |

---

### Schema: `HTTPValidationError`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `detail` | `array` | Optional | Detail |

---

### Schema: `IngestRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `case_id` | `string \| null` | Optional | Case Id |
| `modality` | `string` | ✓ Yes | ultrasound, ct, mri, histology, cytology, text |
| `content_b64` | `string \| null` | Optional | Content B64 |
| `text_content` | `string \| null` | Optional | Text Content |
| `file_name` | `string \| null` | Optional | File Name |

---

### Schema: `IngestResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `request_id` | `string` | ✓ Yes | Request Id |
| `case_id` | `string` | ✓ Yes | Case Id |
| `file_uri` | `string` | ✓ Yes | File Uri |
| `modality` | `string` | ✓ Yes | Modality |
| `quality_score` | `number` | ✓ Yes | Quality Score |
| `quality_flags` | `array` | ✓ Yes | Quality Flags |
| `quality_passed` | `boolean` | ✓ Yes | Quality Passed |
| `status` | `string` | ✓ Yes | Status |

---

### Schema: `InventoryItemsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `sku` | `string` | ✓ Yes | Sku |
| `name` | `string` | ✓ Yes | Name |
| `category` | `string` | ✓ Yes | Category |
| `unit` | `string` | ✓ Yes | Unit |
| `par_level` | `number \| string` | ✓ Yes | Par Level |
| `reorder_point` | `number \| string` | ✓ Yes | Reorder Point |

---

### Schema: `InventoryItemsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `sku` | `string` | ✓ Yes | Sku |
| `name` | `string` | ✓ Yes | Name |
| `category` | `string` | ✓ Yes | Category |
| `unit` | `string` | ✓ Yes | Unit |
| `par_level` | `string` | ✓ Yes | Par Level |
| `reorder_point` | `string` | ✓ Yes | Reorder Point |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `InventoryItemsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `sku` | `string \| null` | Optional | Sku |
| `name` | `string \| null` | Optional | Name |
| `category` | `string \| null` | Optional | Category |
| `unit` | `string \| null` | Optional | Unit |
| `par_level` | `number \| string \| null` | Optional | Par Level |
| `reorder_point` | `number \| string \| null` | Optional | Reorder Point |

---

### Schema: `InventoryMovementsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `item_id` | `string` | ✓ Yes | [format: uuid] Item id |
| `quantity` | `number \| string` | ✓ Yes | Quantity |
| `kind` | `string` | ✓ Yes | Kind |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |
| `reason` | `string` | ✓ Yes | Reason |
| `purchase_order_id` | `string \| null` | Optional | Purchase Order Id |

---

### Schema: `InventoryMovementsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `item_id` | `string` | ✓ Yes | [format: uuid] Item id |
| `quantity` | `string` | ✓ Yes | Quantity |
| `kind` | `string` | ✓ Yes | Kind |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |
| `reason` | `string` | ✓ Yes | Reason |
| `purchase_order_id` | `string \| null` | Optional | Purchase Order Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `InventoryPurchaseOrdersCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `supplier` | `string` | ✓ Yes | Supplier |
| `item_id` | `string` | ✓ Yes | [format: uuid] Item id |
| `quantity` | `number \| string` | ✓ Yes | Quantity |
| `reference` | `string` | ✓ Yes | Reference |

---

### Schema: `InventoryPurchaseOrdersResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `supplier` | `string` | ✓ Yes | Supplier |
| `item_id` | `string` | ✓ Yes | [format: uuid] Item id |
| `quantity` | `string` | ✓ Yes | Quantity |
| `reference` | `string` | ✓ Yes | Reference |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `InventoryReceiptsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `purchase_order_id` | `string` | ✓ Yes | [format: uuid] Purchase order id |
| `quantity` | `number \| string` | ✓ Yes | Quantity |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |

---

### Schema: `InventoryReceiptsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `purchase_order_id` | `string` | ✓ Yes | [format: uuid] Purchase order id |
| `quantity` | `string` | ✓ Yes | Quantity |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `LabOrdersCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `test_id` | `string` | ✓ Yes | [format: uuid] Test id |
| `status` | `string` | Optional | Status |

---

### Schema: `LabOrdersResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `test_id` | `string` | ✓ Yes | [format: uuid] Test id |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `LabOrdersUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `patient_id` | `string \| null` | Optional | Patient Id |
| `encounter_id` | `string \| null` | Optional | Encounter Id |
| `test_id` | `string \| null` | Optional | Test Id |
| `status` | `string \| null` | Optional | Status |

---

### Schema: `LabResultsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `order_id` | `string` | ✓ Yes | [format: uuid] Order id |
| `value` | `number \| string` | ✓ Yes | Value |
| `unit` | `string` | ✓ Yes | Unit |
| `verified` | `boolean` | ✓ Yes | Verified |
| `amends_id` | `string \| null` | Optional | Amends Id |

---

### Schema: `LabResultsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `order_id` | `string` | ✓ Yes | [format: uuid] Order id |
| `value` | `string` | ✓ Yes | Value |
| `unit` | `string` | ✓ Yes | Unit |
| `verified` | `boolean` | ✓ Yes | Verified |
| `amends_id` | `string \| null` | Optional | Amends Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |
| `flag` | `string` | ✓ Yes | Flag |
| `verifier_id` | `string` | ✓ Yes | Verifier Id |

---

### Schema: `LabTestsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `specimen` | `string` | ✓ Yes | Specimen |
| `unit` | `string` | ✓ Yes | Unit |
| `reference_low` | `number \| string` | ✓ Yes | Reference Low |
| `reference_high` | `number \| string` | ✓ Yes | Reference High |
| `critical_low` | `number \| string` | ✓ Yes | Critical Low |
| `critical_high` | `number \| string` | ✓ Yes | Critical High |

---

### Schema: `LabTestsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `specimen` | `string` | ✓ Yes | Specimen |
| `unit` | `string` | ✓ Yes | Unit |
| `reference_low` | `string` | ✓ Yes | Reference Low |
| `reference_high` | `string` | ✓ Yes | Reference High |
| `critical_low` | `string` | ✓ Yes | Critical Low |
| `critical_high` | `string` | ✓ Yes | Critical High |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `LabTestsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `code` | `string \| null` | Optional | Code |
| `name` | `string \| null` | Optional | Name |
| `specimen` | `string \| null` | Optional | Specimen |
| `unit` | `string \| null` | Optional | Unit |
| `reference_low` | `number \| string \| null` | Optional | Reference Low |
| `reference_high` | `number \| string \| null` | Optional | Reference High |
| `critical_low` | `number \| string \| null` | Optional | Critical Low |
| `critical_high` | `number \| string \| null` | Optional | Critical High |

---

### Schema: `LoginPayload`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `username` | `string` | ✓ Yes | Username |
| `password` | `string` | ✓ Yes | Password |

---

### Schema: `MedicalRecordsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `kind` | `string` | ✓ Yes | Kind |
| `content` | `any` | ✓ Yes | Content |
| `document_uri` | `string \| null` | Optional | Document Uri |
| `amends_id` | `string \| null` | Optional | Amends Id |

---

### Schema: `MedicalRecordsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `kind` | `string` | ✓ Yes | Kind |
| `content` | `any` | ✓ Yes | Content |
| `document_uri` | `string \| null` | Optional | Document Uri |
| `amends_id` | `string \| null` | Optional | Amends Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `ModelCalibrationResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `model_id` | `string` | ✓ Yes | Model Id |
| `version` | `string` | ✓ Yes | Version |
| `category` | `string` | ✓ Yes | Category |
| `calibration_method` | `string` | ✓ Yes | Calibration Method |
| `temperature_factor` | `number` | ✓ Yes | Temperature Factor |
| `ece_estimate` | `number` | ✓ Yes | Ece Estimate |
| `brier_score` | `number` | ✓ Yes | Brier Score |
| `calibration_passed` | `boolean` | ✓ Yes | Calibration Passed |

---

### Schema: `ModelDriftResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `model_id` | `string` | ✓ Yes | Model Id |
| `version` | `string` | ✓ Yes | Version |
| `data_drift_score` | `number` | ✓ Yes | Data Drift Score |
| `concept_drift_score` | `number` | ✓ Yes | Concept Drift Score |
| `subgroup_drift_detected` | `boolean` | ✓ Yes | Subgroup Drift Detected |
| `status` | `string` | ✓ Yes | Status |

---

### Schema: `OutcomeCreateRequest`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `case_id` | `string` | ✓ Yes | Case Id |
| `study_id` | `string` | ✓ Yes | Study Id |
| `arm` | `string` | ✓ Yes | AI_ASSISTED | STANDARD_OF_CARE |
| `endpoint` | `string` | ✓ Yes | Endpoint |
| `value` | `object` | ✓ Yes | Value |
| `subgroup_metadata` | `object \| null` | Optional | Subgroup Metadata |

---

### Schema: `OutcomeResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `outcome_id` | `string` | ✓ Yes | Outcome Id |
| `case_id` | `string` | ✓ Yes | Case Id |
| `study_id` | `string` | ✓ Yes | Study Id |
| `adjudication_state` | `string` | ✓ Yes | Adjudication State |
| `timestamp` | `string` | ✓ Yes | [format: date-time]  |

---

### Schema: `Page`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `items` | `array` | ✓ Yes | Items |
| `total` | `integer` | ✓ Yes | Total |
| `offset` | `integer` | ✓ Yes | Offset |
| `limit` | `integer` | ✓ Yes | Limit |

---

### Schema: `PatientsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `mrn` | `string` | ✓ Yes | Mrn |
| `given_name` | `string` | ✓ Yes | Given Name |
| `family_name` | `string` | ✓ Yes | Family Name |
| `birth_date` | `string` | ✓ Yes | [format: date] Birth date |
| `gender` | `string \| null` | Optional | Gender |
| `contact` | `null` | Optional | Contact |
| `insurance` | `null` | Optional | Insurance |
| `consent` | `null` | Optional | Consent |

---

### Schema: `PatientsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `mrn` | `string` | ✓ Yes | Mrn |
| `given_name` | `string` | ✓ Yes | Given Name |
| `family_name` | `string` | ✓ Yes | Family Name |
| `birth_date` | `string` | ✓ Yes | [format: date] Birth date |
| `gender` | `string \| null` | Optional | Gender |
| `contact` | `null` | Optional | Contact |
| `insurance` | `null` | Optional | Insurance |
| `consent` | `null` | Optional | Consent |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `PatientsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `mrn` | `string \| null` | Optional | Mrn |
| `given_name` | `string \| null` | Optional | Given Name |
| `family_name` | `string \| null` | Optional | Family Name |
| `birth_date` | `string \| null` | Optional | Birth Date |
| `gender` | `string \| null` | Optional | Gender |
| `contact` | `null` | Optional | Contact |
| `insurance` | `null` | Optional | Insurance |
| `consent` | `null` | Optional | Consent |

---

### Schema: `PharmacyDispenseCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `prescription_id` | `string` | ✓ Yes | [format: uuid] Prescription id |
| `quantity` | `number \| string` | ✓ Yes | Quantity |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |

---

### Schema: `PharmacyDispenseResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `prescription_id` | `string` | ✓ Yes | [format: uuid] Prescription id |
| `quantity` | `string` | ✓ Yes | Quantity |
| `lot` | `string` | ✓ Yes | Lot |
| `expiry` | `string` | ✓ Yes | [format: date] Expiry |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |
| `pharmacist_id` | `string` | ✓ Yes | Pharmacist Id |

---

### Schema: `PharmacyMedicationsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `strength` | `string` | ✓ Yes | Strength |
| `dosage_form` | `string` | ✓ Yes | Dosage Form |
| `route` | `string` | ✓ Yes | Route |
| `stock_item_id` | `string` | ✓ Yes | [format: uuid] Stock item id |

---

### Schema: `PharmacyMedicationsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `code` | `string` | ✓ Yes | Code |
| `name` | `string` | ✓ Yes | Name |
| `strength` | `string` | ✓ Yes | Strength |
| `dosage_form` | `string` | ✓ Yes | Dosage Form |
| `route` | `string` | ✓ Yes | Route |
| `stock_item_id` | `string` | ✓ Yes | [format: uuid] Stock item id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `PharmacyMedicationsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `code` | `string \| null` | Optional | Code |
| `name` | `string \| null` | Optional | Name |
| `strength` | `string \| null` | Optional | Strength |
| `dosage_form` | `string \| null` | Optional | Dosage Form |
| `route` | `string \| null` | Optional | Route |
| `stock_item_id` | `string \| null` | Optional | Stock Item Id |

---

### Schema: `PharmacyPrescriptionsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `medication_id` | `string` | ✓ Yes | [format: uuid] Medication id |
| `quantity` | `number \| string` | ✓ Yes | Quantity |
| `directions` | `string` | ✓ Yes | Directions |
| `refills` | `integer \| null` | Optional | Refills |
| `replaces_id` | `string \| null` | Optional | Replaces Id |

---

### Schema: `PharmacyPrescriptionsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `medication_id` | `string` | ✓ Yes | [format: uuid] Medication id |
| `quantity` | `string` | ✓ Yes | Quantity |
| `directions` | `string` | ✓ Yes | Directions |
| `refills` | `integer \| null` | Optional | Refills |
| `replaces_id` | `string \| null` | Optional | Replaces Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |
| `prescriber_id` | `string` | ✓ Yes | Prescriber Id |

---

### Schema: `Query`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `offset` | `integer` | Optional | Offset |
| `limit` | `integer` | Optional | Limit |
| `filters` | `object` | Optional | Filters |

---

### Schema: `RadiologyOrdersCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `study_id` | `string` | ✓ Yes | [format: uuid] Study id |
| `priority` | `string` | ✓ Yes | Priority |
| `preparation` | `string` | ✓ Yes | Preparation |
| `status` | `string` | Optional | Status |

---

### Schema: `RadiologyOrdersResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `encounter_id` | `string` | ✓ Yes | [format: uuid] Encounter id |
| `study_id` | `string` | ✓ Yes | [format: uuid] Study id |
| `priority` | `string` | ✓ Yes | Priority |
| `preparation` | `string` | ✓ Yes | Preparation |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `RadiologyOrdersUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `patient_id` | `string \| null` | Optional | Patient Id |
| `encounter_id` | `string \| null` | Optional | Encounter Id |
| `study_id` | `string \| null` | Optional | Study Id |
| `priority` | `string \| null` | Optional | Priority |
| `preparation` | `string \| null` | Optional | Preparation |
| `status` | `string \| null` | Optional | Status |

---

### Schema: `RadiologyReportsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `order_id` | `string` | ✓ Yes | [format: uuid] Order id |
| `findings` | `string` | ✓ Yes | Findings |
| `impression` | `string` | ✓ Yes | Impression |
| `image_uri` | `string` | ✓ Yes | Image Uri |
| `dicom_metadata` | `any` | ✓ Yes | Dicom metadata |
| `diagnostic_use` | `boolean` | ✓ Yes | Diagnostic use |
| `amends_id` | `string \| null` | Optional | Amends Id |

---

### Schema: `RadiologyReportsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `order_id` | `string` | ✓ Yes | [format: uuid] Order id |
| `findings` | `string` | ✓ Yes | Findings |
| `impression` | `string` | ✓ Yes | Impression |
| `image_uri` | `string` | ✓ Yes | Image Uri |
| `dicom_metadata` | `any` | ✓ Yes | Dicom metadata |
| `diagnostic_use` | `boolean` | ✓ Yes | Diagnostic use |
| `amends_id` | `string \| null` | Optional | Amends Id |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |
| `signer_id` | `string` | ✓ Yes | Signer Id |
| `signed_at` | `string` | ✓ Yes | [format: date-time]  |
| `quality_evidence` | `any` | ✓ Yes | Quality Evidence |

---

### Schema: `RadiologyStudiesCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `modality` | `string` | ✓ Yes | Modality |
| `body_part` | `string` | ✓ Yes | Body Part |
| `name` | `string` | ✓ Yes | Name |

---

### Schema: `RadiologyStudiesResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `modality` | `string` | ✓ Yes | Modality |
| `body_part` | `string` | ✓ Yes | Body Part |
| `name` | `string` | ✓ Yes | Name |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `RadiologyStudiesUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `modality` | `string \| null` | Optional | Modality |
| `body_part` | `string \| null` | Optional | Body Part |
| `name` | `string \| null` | Optional | Name |

---

### Schema: `RegisterPayload`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `username` | `string` | ✓ Yes | Username |
| `email` | `string` | ✓ Yes | Email |
| `password` | `string` | ✓ Yes | Password |
| `full_name` | `string` | ✓ Yes | Full Name |
| `role` | `string` | ✓ Yes | Role |
| `department` | `string \| null` | Optional | Department |
| `license_number` | `string \| null` | Optional | License Number |

---

### Schema: `SchedulingAppointmentsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `encounter_id` | `string \| null` | Optional | Encounter Id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |
| `kind` | `string` | ✓ Yes | Kind |
| `status` | `string` | Optional | Status |

---

### Schema: `SchedulingAppointmentsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `patient_id` | `string` | ✓ Yes | [format: uuid] Patient id |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `encounter_id` | `string \| null` | Optional | Encounter Id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |
| `kind` | `string` | ✓ Yes | Kind |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `SchedulingAppointmentsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `patient_id` | `string \| null` | Optional | Patient Id |
| `provider_id` | `string \| null` | Optional | Provider Id |
| `encounter_id` | `string \| null` | Optional | Encounter Id |
| `start` | `string \| null` | Optional | Start |
| `end` | `string \| null` | Optional | End |
| `kind` | `string \| null` | Optional | Kind |
| `status` | `string \| null` | Optional | Status |

---

### Schema: `SchedulingAvailabilityCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |

---

### Schema: `SchedulingAvailabilityResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `SchedulingAvailabilityUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `provider_id` | `string \| null` | Optional | Provider Id |
| `start` | `string \| null` | Optional | Start |
| `end` | `string \| null` | Optional | End |

---

### Schema: `SchedulingShiftsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |
| `department` | `string` | ✓ Yes | Department |
| `status` | `string` | Optional | Status |

---

### Schema: `SchedulingShiftsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `provider_id` | `string` | ✓ Yes | [format: uuid] Provider id |
| `start` | `string` | ✓ Yes | [format: date-time] Start |
| `end` | `string` | ✓ Yes | [format: date-time] End |
| `department` | `string` | ✓ Yes | Department |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `SchedulingShiftsUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `provider_id` | `string \| null` | Optional | Provider Id |
| `start` | `string \| null` | Optional | Start |
| `end` | `string \| null` | Optional | End |
| `department` | `string \| null` | Optional | Department |
| `status` | `string \| null` | Optional | Status |

---

### Schema: `SchedulingSwapsCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `shift_id` | `string` | ✓ Yes | [format: uuid] Shift id |
| `replacement_id` | `string` | ✓ Yes | [format: uuid] Replacement id |
| `reason` | `string` | ✓ Yes | Reason |
| `status` | `string` | Optional | Status |

---

### Schema: `SchedulingSwapsResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `shift_id` | `string` | ✓ Yes | [format: uuid] Shift id |
| `replacement_id` | `string` | ✓ Yes | [format: uuid] Replacement id |
| `reason` | `string` | ✓ Yes | Reason |
| `status` | `string` | Optional | Status |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `StaffCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `display_name` | `string` | ✓ Yes | Display Name |
| `role` | `string` | ✓ Yes | Role |
| `department` | `string` | ✓ Yes | Department |
| `credentials` | `any` | ✓ Yes | Credentials |
| `license_expiry` | `string` | ✓ Yes | [format: date] License expiry |
| `contact` | `null` | Optional | Contact |

---

### Schema: `StaffResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `display_name` | `string` | ✓ Yes | Display Name |
| `role` | `string` | ✓ Yes | Role |
| `department` | `string` | ✓ Yes | Department |
| `credentials` | `any` | ✓ Yes | Credentials |
| `license_expiry` | `string` | ✓ Yes | [format: date] License expiry |
| `contact` | `null` | Optional | Contact |
| `id` | `string` | ✓ Yes | [format: uuid]  |
| `created_at` | `string` | ✓ Yes | [format: date-time]  |
| `updated_at` | `string` | ✓ Yes | [format: date-time]  |
| `actor_id` | `string` | ✓ Yes | Actor Id |
| `request_id` | `string` | ✓ Yes | Request Id |
| `version` | `integer` | ✓ Yes | Version |
| `extra` | `object` | ✓ Yes | Extra |

---

### Schema: `StaffUpdate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `expected_version` | `integer` | ✓ Yes | Expected Version |
| `display_name` | `string \| null` | Optional | Display Name |
| `role` | `string \| null` | Optional | Role |
| `department` | `string \| null` | Optional | Department |
| `credentials` | `null` | Optional | Credentials |
| `license_expiry` | `string \| null` | Optional | License Expiry |
| `contact` | `null` | Optional | Contact |

---

### Schema: `TimelineEventCreate`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `event_time` | `string` | ✓ Yes | [format: date-time]  |
| `event_type` | `string` | ✓ Yes | DIAGNOSIS, IMAGING, PATHOLOGY, LABORATORY, TREATMENT, RESPONSE, OUTCOME |
| `source` | `string` | ✓ Yes | Source |
| `payload` | `object` | ✓ Yes | Payload |
| `confidence` | `number \| null` | Optional | Confidence |
| `missingness_state` | `string` | Optional | PRESENT, MISSING, IMPUTED, UNKNOWN |
| `references_event_id` | `string \| null` | Optional | References Event Id |

---

### Schema: `TimelineEventDTO`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `id` | `string` | ✓ Yes | Id |
| `case_id` | `string` | ✓ Yes | Case Id |
| `event_time` | `string` | ✓ Yes | [format: date-time]  |
| `event_type` | `string` | ✓ Yes | Event Type |
| `source` | `string` | ✓ Yes | Source |
| `missingness_state` | `string` | ✓ Yes | Missingness State |
| `payload` | `object` | ✓ Yes | Payload |
| `inserted_at` | `string` | ✓ Yes | [format: date-time]  |

---

### Schema: `TimelineResponse`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `case_id` | `string` | ✓ Yes | Case Id |
| `total_events` | `integer` | ✓ Yes | Total Events |
| `events` | `array` | ✓ Yes | Events |
| `trajectory_summary` | `object` | ✓ Yes | Trajectory Summary |

---

### Schema: `UncertaintyDTO`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `predictive_uncertainty` | `number` | ✓ Yes | Predictive Uncertainty |
| `data_uncertainty` | `number` | ✓ Yes | Data Uncertainty |
| `evidence_uncertainty` | `number \| null` | Optional | Evidence Uncertainty |
| `ood_score` | `number` | ✓ Yes | Ood Score |
| `aggregate_decision` | `string` | ✓ Yes | Aggregate Decision |
| `reasons` | `array` | ✓ Yes | Reasons |

---

### Schema: `ValidationError`

| Field | Type | Required | Description / Constraints |
| :--- | :--- | :---: | :--- |
| `loc` | `array` | ✓ Yes | Location |
| `msg` | `string` | ✓ Yes | Message |
| `type` | `string` | ✓ Yes | Error Type |

---

## 7. Seeded Clinical Data & Test Scenarios
Use these pre-seeded patient records and clinical scenarios to verify frontend functionality:

### Patient Test Accounts
1. **Eleanor Vance (`MRN-2026-KD-001`):**
   - **Age / Gender:** 58F | **Consent:** FULL_CLINICAL
   - **Condition:** Renal Cell Carcinoma (Stage II, Clear Cell).
   - **Active Study:** CT Abdomen (`RAD-2026-0001`) with 4.2cm left renal mass.
   - **Allergy Guard:** Documented `PENICILLIN` allergy. Attempting to prescribe Penicillin must be blocked.
   - **Encounter:** `ENC-2026-0001` (In Progress).

2. **Arthur Pendleton (`MRN-2026-0006`):**
   - **Age / Gender:** 67M | **Consent:** FULL_CLINICAL
   - **Condition:** Colon Adenocarcinoma.
   - **Allergy Guard:** Documented `SULFA` allergy. Attempting to prescribe Sulfa must be blocked.
   - **Encounter:** `ENC-2026-0006`.

3. **Untrained Ingestion Refusal Scenarios:**
   - **Modality:** Breast Ultrasound (`breast_ultrasound`) -> Response: `REFUSED` (Untrained Modality). UI must not display `--%` placeholder.
   - **Modality:** Lymphoma Histology (`lymphoma_histology`) -> Response: `REFUSED` (Untrained Modality).

4. **Pharmacy Low-Stock Warning Scenario:**
   - **Medication:** Oxaliplatin 100mg vial (`ITEM-OXAL-100`).
   - **Inventory:** 3 vials remaining $\le$ Reorder Threshold of 10. Triggers yellow low-stock banner.

5. **Double-Entry Accounting Ledger Scenario:**
   - **Total Debits:** $2,175.00
   - **Total Credits:** $2,175.00
   - **Balance:** $0.00 (Balanced badge rendered in green).
