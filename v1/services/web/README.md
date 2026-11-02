# OncoSentinel — Consolidated Clinical Workspace

A redesigned, working frontend built on the supplied OncoSentinel UI export, not a separate visual mockup. The original ten-workspace structure, diagnostic DOM hooks, endpoint paths, and OpenAPI specification remain available. No frontend framework migration or runtime dependency is required.

## Run the frontend

Requires Node.js 20 or later (tested with Node.js 22).

```sh
npm start
```

Open **http://localhost:4173**. There are no packages to install to run the static server. `PORT=8080 npm start` changes the port on systems supporting that environment-variable syntax.

The default is a visibly labeled demonstration workspace. It signs in to a fictional clinician account and supports sample patient registration, search, FHIR patient import/export, encounters, timeline events, prescribing safety checks, inventory receipts/FIFO dispensing, invoice creation, payments, and audit entries. Changes persist only in this browser. Use the header's Preview role control to inspect all five primary roles; ADMIN exposes all ten workspaces. Use Reset data to restore the fixtures.

**Demonstration mode does not execute clinical inference, generate medical predictions, fabricate model metrics, or return simulated guideline evidence.** The diagnostic service is intentionally unavailable there. Local untrained-category refusals can still be exercised. Synthetic test images are explicitly identified and are restricted to demo mode.

## Connect the existing backend

Open **Connection settings** in the top bar. Choose **Live · Your backend**, enter the backend origin (for example `https://api.example.com`), and save. Leave the origin empty when the frontend and backend share a host. Sign in using real backend credentials. Demo and live tokens use separate storage keys, and live mode never silently falls back to sample data.

For a production deployment, set the default in `js/config.js`:

```js
window.ONCO_DEPLOYMENT = { mode: 'live', apiOrigin: '' };
```

Browser connection preferences override this deployment default. Use the connection dialog to change an existing browser preference, or clear `onco.mode` and `onco.apiOrigin` from browser storage when verifying a changed default.

For a separate API origin, configure backend CORS for the frontend origin, HTTP methods GET/POST/PUT/DELETE and OPTIONS preflight, and headers Content-Type, Authorization, Idempotency-Key, and X-HMS-Confirm. Use HTTPS outside local development. The supplied static server is a development/preview server, not a production medical-system host.

The diagnostic request continues to use `POST /api/v2/analyze` with `case_id`, `category_hint`, `modality`, `text_query`, `image_b64`, and `patient_context`. Review actions continue to use `POST /api/v2/predictions/{prediction_id}/review`; review requires a real response identifier. FHIR report export, model cards, guideline retrieval, timeline, and HMS API paths remain in the controller. HMS writes retain confirmation, idempotency, and optimistic-version headers/payloads.

Upload support is PNG/JPEG/WebP, up to 20 MB. This frontend does not decode DICOM or PDF images: those require a backend conversion/PACS integration. Radiology order scans require an uploaded patient image; the frontend no longer silently generates a scan for live inference. Backend Grad-CAM artifacts are fetched with authentication; unavailable artifacts and metrics remain unavailable, not manufactured.

## Included workspaces

Diagnostic Studio · Clinical guidelines · Patient timeline · Patient registry · Encounters & notes · Radiology & laboratories · Pharmacy & inventory · Billing & finance · Audit trail · Model portfolio.

The UI uses a restrained clinical design system: mint/slate navigation, typography hierarchy, focused cards, tabbed evidence, keyboard command search (Ctrl/Cmd+K), accessible dialogs, searchable/sortable patient records, and a mobile navigation drawer. Secondary developer scenarios are collapsed by default. There are no stock images, fake activity charts, decorative KPI claims, or AI-generated clinical results.

## Important diagnostic behavior changes

- Switching a patient, category, modality, image, or clinical context invalidates the previous prediction, citations, heatmap, and review target.
- Late analysis responses cannot overwrite a different case/input selection.
- Untrained breast/lymphoma categories refuse without emitting diagnostic probabilities. Lymphoma refusal does not invent a tissue-degradation explanation.
- Reviews cannot fabricate prediction IDs or sign off an unrecorded assessment.
- Missing confidence, uncertainty, model parameters, concept attributions, and heatmap quality measures are not replaced with fake clinical defaults.
- Guidelines without citations/evidence cards are not labeled verified.
- Patient registration consent is explicit opt-in, not silently enabled.
- Read-only patient/encounter roles do not receive mutation controls.

Frontend role boundaries are UX controls, not a security boundary. The backend MUST enforce authorization, clinical safety, consent, input validation, idempotency, and data provenance. Browser-stored demo audit events are mutable local data, never a clinical/immutable record.

## Build and test

```sh
npm install
npx playwright install --with-deps chromium
npm run check
npm test
npm run build
```

`npm run build` copies the deployable frontend into `dist/`. Serve that directory with your existing backend or static hosting. Google Fonts are optional progressive enhancement; system fonts keep the interface usable without them. For a deployment that cannot contact Google Fonts, remove the font stylesheet and preconnect links from `index.html`.

The included Playwright suite contains **28 passing tests**: all workspaces, role boundaries, registry search, real form submission and persistence, FHIR exchange, encounter state changes, timeline events, allergy interception, stock/FIFO movements, balanced billing, command search, mobile overflow, upload validation, backend-mode separation, original analysis payload/review contracts, untrained refusals, stale-result/race prevention, and ungrounded retrieval refusal. The initial desktop Studio also passed automated axe WCAG A/AA checks. This is not a claim of full accessibility conformance or medical-device validation.

Live integration tests use controlled HTTP fixtures because the supplied archive contains no running backend or model weights. The actual authentication service, model inference, real Grad-CAM artifacts, clinical guideline store, and full backend interoperability still require validation against your deployment. Some demo API operations intentionally return an explicit unavailable response where real clinical evidence is required.

## Project structure

- `index.html` — application shell and retained workspace/modal DOM hooks.
- `css/app.css` — supplied component foundations.
- `css/workspace.css` — redesigned design system and responsive component styling.
- `js/app.js` — original integrated controller with targeted safety fixes and retained API bindings.
- `js/config.js` — deployment defaults and separate demo/live token configuration.
- `js/api-client.js` — explicit local demonstration adapter or live API transport; no silent fallback.
- `js/workspace.js` — keyboard navigation, evidence tabs, connection settings, patient filtering, and context interactions.
- `server.mjs` — dependency-free local static server.
- `scripts/build.mjs` — static build script.
- `tests/` and `playwright.config.js` — browser regression and accessibility tests.
- `openapi.json` and `SCHEMAS_AND_UI_SPECIFICATION.md` — original handoff references, retained unchanged.
- `previews/` — actual browser screenshots and test-results summary for this build.

The separately delivered standalone HTML demo bundles this same frontend for quick inspection. Use the project server and original source files for integration and development.
