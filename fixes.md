\# TASK: Make OncoSentinel v2.0 coherent, role-aware and honest



Stack: FastAPI backend at 127.0.0.1:8000 plus the existing web frontend.

First, inspect the repo and map every nav page to its API endpoints. Then

make the changes below. Do not add new feature areas. The goal is

coherence, correct permissions, and truthful UI.



\## 0. Principles

\- One spine: Patient -> Encounter -> Study/Order -> AI Result -> Clinician

&#x20; sign-off -> Timeline + Audit. Every page must read or write part of it.

\- UI must never claim something the data does not support (no "VERIFIED"

&#x20; on an empty result, no "Unmeasured" next to a model card with metrics).

\- Every mutating action writes an audit entry.

\- Anything not wired is hidden or clearly marked "Roadmap", never faked.



\## 1. Roles and auth (root cause of most breakage)

\- Roles: CLINICIAN, RADIOLOGIST (also covers pathologist), PHARMACIST,

&#x20; BILLING\_CLERK, ADMIN (auditor).

\- Add a dev-only role switcher / seeded demo users, one per role, shown in

&#x20; the header dropdown. The header must display the real current user and

&#x20; role. Currently it shows user "s" while reviews are attributed to

&#x20; dr\_chen and dr\_adams. Fix the typo "onlcology".

\- Central permission map (role -> pages and actions), enforced server-side

&#x20; (403) and client-side (nav hiding).

\- Nav visibility by role:

&#x20; - CLINICIAN: AI Studio, Guidelines, Timeline, Registry, Encounters,

&#x20;   Radiology \& Lab (view/order), Pharmacy (PRESCRIBE only), Audit (own

&#x20;   actions), Model Cards (read).

&#x20; - RADIOLOGIST: AI Studio, Radiology (Sign Report), Registry (read), Timeline.

&#x20; - PHARMACIST: Pharmacy (dispense, inventory), Registry (read).

&#x20; - BILLING\_CLERK: Billing only.

&#x20; - ADMIN: Audit, Model Portfolio, Billing, inventory, user list.

\- Remove the raw error strings ("Action requires one of roles...") from

&#x20; pages. Hidden nav for unauthorized roles, or a friendly "Your role

&#x20; can't access this" empty state if reached by URL.

\- Only RADIOLOGIST can "Sign Report"; only CLINICIAN can prescribe and

&#x20; record AI sign-off.



\## 2. Data integrity and seed data

\- Replace repeated placeholder IDs (encounters all "33333333", radiology

&#x20; orders "44444444", lab orders "55555555") with unique readable IDs

&#x20; (ENC-2026-0001, RAD-..., LAB-...).

\- Seed one complete story per patient (9 patients, or cut to 5-6 that are

&#x20; fully worked): registration -> encounter -> order -> study -> AI run ->

&#x20; sign-off -> timeline events -> (where relevant) prescription -> invoice.

&#x20; Include one REFUSED/ABSTAIN case and one untrained-category case.

\- Make counts consistent: the Registry badge has shown 4, 1, then 9. Drive

&#x20; all sidebar badges from the API.

\- Encounter statuses should vary (active, discharged, scheduled). Not all

&#x20; 9 "ACTIVE".

\- Department must match the patient's cancer type (already mostly true; keep).

\- Fix lab flags: "2.0000 grade" with ref 0-1 is not a meaningful lab value.

&#x20; Model histopathology as a text/grade result, not a numeric range.

\- Explain or remove the unlabeled "QUALITY: 218.4 / 194.8" (it is the

&#x20; Laplacian variance gate). Label it "Image quality (Laplacian var.)"

&#x20; with pass/fail.



\## 3. Page-by-page fixes

\*\*AI Diagnostic Studio\*\*

\- Entry from Registry/Radiology ("AI Studio", "Run AI Scan") prefills MRN,

&#x20; category, modality, study and query. Remove free-typed MRN. Keep a

&#x20; clearly labeled "Demo / custom upload" mode.

\- Category, modality and model must be validated together. If the model

&#x20; is UNTRAINED or modality mismatches, return REFUSED with a reason. Never

&#x20; show a tumor percentage in that case.

\- Remove the "VERIFIED" badge unless a real check passed.

\- After a result: Accept / Override (reason required) / Second read.

&#x20; Persist to ai/reviews, Timeline and Audit.

\- Retrieval in the evidence panel must be filtered by case category (a

&#x20; colon case must not cite NSCLC or breast text).



\*\*Oncology Guidelines (RAG)\*\*

\- Searching "cancer" returns "No verified guideline recommendation found"

&#x20; under a "(VERIFIED)" header. Fix retrieval (lower threshold, keyword

&#x20; fallback, cancer-type facets) and show source cards (guideline, version,

&#x20; section). For no result: "No matching guideline", with no VERIFIED label.

\- Add category filter chips seeded from the model portfolio.

\- Optionally prefill from the current patient's category.



\*\*Patient Timeline\*\*

\- It shows 4 events yet the summary says "No prior longitudinal records",

&#x20; "Prior Treatments: 1" and "Missingness 0". Compute the summary from the

&#x20; events. Show which patient is displayed (name and MRN in the header) and

&#x20; add a patient selector.

\- Auto-append events from: encounter, imaging, pathology, AI run, sign-off,

&#x20; prescription. "Append Clinical Event" remains for manual entries.



\*\*Patient Registry\*\*

\- Keep the existing action buttons, but each must navigate with the patient

&#x20; context preserved. Show the logged-in role's allowed actions only.

\- Unify consent labels (all show "RESEARCH \& AI"; vary or explain).

\- The reviews table must show the actual reviewing user, linked to the

&#x20; audit entry.



\*\*Encounters \& Notes\*\*

\- Only 3 of 9 patients have notes. Seed notes for all, or filter. Add

&#x20; patient filter and search. Appointment "Mark Arrived" must update the

&#x20; encounter and write to the audit.



\*\*Radiology \& Lab\*\*

\- Alerts are hardcoded text. Generate them from AI results and critical

&#x20; labs, with Acknowledge. An alert saying "AI detection 94.2%" must match

&#x20; the stored result.

\- "Run AI Scan" on breast ultrasound must show "Model untrained: manual

&#x20; read only", not run.

\- Sign Report is radiologist-only. Signing writes audit, timeline and

&#x20; clears the alert.



\*\*Pharmacy \& Inventory\*\*

\- Clinician: prescribe and see own prescriptions (with allergy guard

&#x20; actually checking the EHR allergies). Pharmacist: dispense (FIFO) and

&#x20; stock. Seed 6-10 oncology drugs (FOLFOX components etc.), lots, and a

&#x20; low-stock item. Empty tables need real empty states.



\*\*Billing \& Finance\*\*

\- Visible to BILLING\_CLERK and ADMIN only. Auto-create invoice lines from

&#x20; signed radiology, labs, and encounters (CPT codes). Seed a few

&#x20; invoices and payments so the KPIs and ledger are nonzero and balanced

&#x20; (DR = CR). Remove "$0.00 / --%" placeholders. Show "No data yet" instead.



\*\*Audit Provenance Trail\*\*

\- Currently empty. Wire middleware so every mutating request logs

&#x20; timestamp, trace ID, actor, role, action, service, patient MRN.

&#x20; Filters by actor, role, patient and date. ADMIN sees all; others

&#x20; see their own.



\*\*Model Portfolio \& Cards\*\*

\- Table says "Unmeasured / None" for accuracy, F1 and SHA while the

&#x20; oral\_cancer card shows 94.1% accuracy and a SHA digest. Make the table

&#x20; read from the same model-card source.

\- Header "Eight-Task" and "7 Deep MobileNetV3 Checkpoints" disagree with

&#x20; the table (6 active, 2 untrained). Compute both from data, e.g.

&#x20; "6 of 8 models active".

\- Render model-card markdown properly (headings, tables), not raw text.

\- Compute metrics and SHA for every active model, or mark "Not evaluated"

&#x20; and block that model from showing confident outputs.

\- Rename "Export Faculty Briefing" to "Export Model Report".



\## 4. Global UI

\- The top banner must reflect real deployed models and stop being a

&#x20; truncated string; make it a compact status chip with a tooltip.

\- Remove FR-xx / NFR / SRS tags from the UI (keep in docs).

\- Consistent empty, loading and error states on every table.



\## 5. Acceptance checklist

1\. Switch to each role: nav, buttons and API responses match the

&#x20;  permission map. No raw role errors anywhere.

2\. Pick patient -> run AI -> sign off: a new entry appears in Timeline,

&#x20;  Audit, Reviews, and (where applicable) Alerts and Billing.

3\. Untrained or mismatched category always returns REFUSED, with no

&#x20;  percentage.

4\. No duplicate IDs, no 0-value KPI placeholders, no contradictory counts.

5\. RAG search for "cancer", "colon", "oral" returns sources.

6\. All sidebar items open a functional page or are hidden.

Run the app and tests. Summarize what changed per page.

