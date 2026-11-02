# OncoSentinel

A research prototype that combines cancer-imaging classifiers with a small hospital-management system (patients, orders, pharmacy, billing, audit), behind a single FastAPI app and web UI.

This is a milestone version of a final-year major project, built for the external evaluation in the 7th semester.

The idea: an AI result is never shown on its own. It passes through quality and relevance checks, gets an uncertainty estimate and an explanation, and then waits for a clinician to accept, edit, reject or abstain. Every step is written to an append-only audit log.

> **Research use only.** This is not a medical device and has not been clinically validated. Do not use it to make decisions about real patients. All patient data in the repo is synthetic seed data.

<img width="1341" height="1333" alt="image" src="https://github.com/user-attachments/assets/4564024d-8280-4cc6-a2dd-0befba7cdbac" />



## What works today

| Category | Modality | Classes | Status |
|---|---|---|---|
| Kidney | CT | normal, tumor | Trained checkpoint |
| Oral | Histology | normal, OSCC | Trained checkpoint |
| Leukemia (ALL) | Microscopy | 4 classes | Trained checkpoint |
| Brain | MRI | 3 classes | Trained checkpoint |
| Cervical | Cytology | 5 classes | Trained checkpoint |
| Colon | Histology | 2 classes | Trained checkpoint |
| Lung | Histology | 3 classes | Trained checkpoint |
| Breast, Lung+Colon (combined), Lymphoma | | | Scaffolded, **no trained model** |

There is also an organ-router checkpoint (`OrganRouter.pth`). All checkpoints are MobileNetV3-Small, about 6 MB each, in [`models/`](models/).

The scaffolded categories are registered in the config but report as untrained and will not return predictions. Per-model metric files are in `v1/artifacts/metrics/` and model cards in `v1/artifacts/model_cards/`; read the training configs and split manifests there before trusting any number.

## Quick start

Requires Python 3.11+ (tested on 3.13, Windows). The first launch creates and seeds a local SQLite database, so there is nothing else to set up.

```bash
pip install -r requirements.txt
python run.py
```

Then open:

- App: <http://127.0.0.1:8000/>
- Hospital management: <http://127.0.0.1:8000/hms>
- API docs (Swagger): <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

If port 8000 is taken, the runner picks the next free one and prints it. Use `--port N` to choose.

Other launchers:

| Command | What it does |
|---|---|
| `python run.py` | Server only; open the URL in a browser |
| `run.bat` / `run.ps1` | Same, from Windows shells |
| `python desktop_app.py` | Native window via WebView2 (needs `pywebview`); falls back to the browser if WebView2 is missing |
| `python desktop_app.py --browser` | Server plus your default browser |

`torch` is a large download. If you only need a CPU build, install it from the [PyTorch index](https://pytorch.org/get-started/locally/) first.

### Demo accounts

Seeded on first run. All share the password `OncoUser2026!`. This is demo data; change it for anything beyond local use.

| Username | Role |
|---|---|
| `dr_chen` | Clinician (medical oncology) |
| `dr_patel` | Radiologist / pathologist |
| `dr_adams` | Pathologist / radiologist |
| `nurse_sarah` | Scheduler / reception |
| `pharma_alex` | Pharmacist / inventory |
| `billing_mark` | Billing / finance |
| `admin_clara` | Admin (all roles) |
| `research_elena` | Researcher / analyst |

Pages and API actions are gated by role, so log in as different users to see different views.

## How a request flows

```
upload / query
  → ingestion & quality gate   (blur, contrast, resolution; low quality is rejected)
  → router                     (intent, cancer relevance ≥ 0.55, modality, model availability)
  → ML orchestrator            (category model → class probabilities)
  → uncertainty                (calibration + out-of-distribution detectors → PASS / REVIEW / ABSTAIN)
  → explanation                (Grad-CAM heatmap + concept-level rationale)
  → clinician review           (accept / reject / edit / request evidence / abstain)
  → audit log                  (insert-only)
```

Inputs that are not cancer-relevant, are too low quality, or look out-of-distribution end in an explicit terminal state instead of a guess.

## Repository layout

```
run.py, run.bat, run.ps1     launchers (delegate to v1/run.py)
desktop_app.py               desktop window wrapper around the same server
oncosentinel.spec            PyInstaller spec for building a Windows exe
models/                      trained checkpoints (.pth)
data/storage/                runtime uploads and heatmaps (empty; created on use)
ocnewui/                     standalone frontend source, build script, Playwright tests
v1/
  services/
    gateway/                 FastAPI app, auth, routes
    hms/                     hospital management: patients, scheduling, lab, radiology,
                             pharmacy, inventory, billing, finance
    ingestion/               validation, OCR, storage
    router/                  intent, relevance and modality checks
    ml/                      backbone, heads, checkpoint loading, orchestrator
    uncertainty/             calibration, OOD detection, aggregation
    xai/                     Grad-CAM, concept mapping, explanation metrics
    rag/                     guideline retrieval and grounded reasoning
    longitudinal/            append-only patient timeline
    fairness/, outcomes/, federated/, audit/, interop/ (FHIR), tasks/ (Celery)
    web/                     UI served by the gateway
  configs/                   taxonomy, thresholds, model registry, HMS, training configs
  training/                  training and evaluation code
  tests/                     pytest suite
  project doc/               SRS, architecture, PRD, decision log, history
```

## Configuration

Defaults work out of the box with SQLite. To change them, copy `v1/.env.example` to `v1/.env`.

- `DATABASE_URL`: defaults to a local SQLite file. Install `psycopg2` and point it at PostgreSQL if you prefer.
- `JWT_SECRET_KEY`: **set your own** before exposing the server to anything but localhost.
- `ENVIRONMENT`: in `production`, the unauthenticated token endpoint is disabled.
- `OLLAMA_URL` / `OLLAMA_MODEL`: optional local LLM for the grounded-reasoning step. Without it, a deterministic fallback is used.

Thresholds (relevance cutoff, OOD consensus, fairness gates) live in `v1/configs/thresholds.yaml`.

## Tests

```bash
cd v1
pytest tests -v
```

Frontend end-to-end tests live in `ocnewui/tests` (Playwright; run `npm install` there first).

## Building the Windows executable

```bash
pip install pyinstaller
pyinstaller oncosentinel.spec
```

Output goes to `dist/` and is not committed. A WebView2 runtime is needed for the native window; the app offers a browser fallback if it is missing.

## Further reading

- [`v1/README.md`](v1/README.md): detailed subsystem notes and API reference
- [`v1/DATASET_AND_RAG_SETUP_GUIDE.md`](v1/DATASET_AND_RAG_SETUP_GUIDE.md): datasets and guideline ingestion
- [`v1/project doc/`](v1/project%20doc/): requirements, architecture and decision log

## Limitations

- Models are small (MobileNetV3-Small) and have not been externally or prospectively validated.
- Three registered categories (breast, combined lung+colon, lymphoma) have no trained model.
- The federated-learning and outcome-analytics modules are simulations for research, not deployed systems.
- Authentication is suited to local demos, not production hardening.

## License

Research use only (see `v1/pyproject.toml`). No open-source license has been chosen yet; add a `LICENSE` file before inviting contributions.
