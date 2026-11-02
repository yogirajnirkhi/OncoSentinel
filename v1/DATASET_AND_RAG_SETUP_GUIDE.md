# OncoSentinel v2.0 — Local Dataset, Vector DB & LLM Setup Guide

This guide provides step-by-step instructions for:
1. Organizing and loading your own local medical image datasets for all **eight cancer models** into OncoSentinel.
2. Setting up, populating, and managing the **Clinical Knowledge Vector Database (RAG)** with oncology guidelines.
3. Choosing, installing, and connecting a **Local or Cloud LLM** (e.g., Ollama `llama3:8b`, `biomistral:7b`, or Gemini API) for evidence-grounded clinical reasoning.
4. Running model training, verifying cryptographic checkpoints, and tracking results in the Web Dashboard.

---

## Table of Contents
- [1. System Architecture Overview](#1-system-architecture-overview)
- [2. Part 1: Local Image Datasets for All 8 Cancer Models](#2-part-1-local-image-datasets-for-all-8-cancer-models)
  - [2.1 Directory Structure & Class Taxonomy](#21-directory-structure--class-taxonomy)
  - [2.2 File Naming Convention & Leakage Prevention (Crucial)](#22-file-naming-convention--leakage-prevention-crucial)
  - [2.3 Recommended Open Datasets for Reference](#23-recommended-open-datasets-for-reference)
  - [2.4 Converting DICOM (.dcm) & NIfTI (.nii.gz) to PNG](#24-converting-dicom-dcm--nifti-niigz-to-png)
  - [2.5 Generating Split Manifests & Running Training](#25-generating-split-manifests--running-training)
- [3. Part 2: Vector Database (RAG) Setup](#3-part-2-vector-database-rag-setup)
  - [3.1 What to Put in the Vector DB](#31-what-to-put-in-the-vector-db)
  - [3.2 Selecting Your Vector Store (Qdrant vs. Chroma vs. In-Memory)](#32-selecting-your-vector-store-qdrant-vs-chroma-vs-in-memory)
  - [3.3 Document Ingestion Script (PDF & Text to Vector DB)](#33-document-ingestion-script-pdf--text-to-vector-db)
  - [3.4 Embedding Model Selection](#34-embedding-model-selection)
- [4. Part 3: Selecting and Connecting the LLM](#4-part-3-selecting-and-connecting-the-llm)
  - [4.1 Which LLM Should You Use?](#41-which-llm-should-you-use)
  - [4.2 Option A: Local Ollama (Recommended)](#42-option-a-local-ollama-recommended)
  - [4.3 Option B: Cloud Gemini API](#43-option-b-cloud-gemini-api)
  - [4.4 Grounded Prompting & Non-Fabrication Rules](#44-grounded-prompting--non-fabrication-rules)
- [5. Part 4: Hardware Requirements & Optimization](#5-part-4-hardware-requirements--optimization)
- [6. Part 5: End-to-End Execution Checklist](#6-part-5-end-to-end-execution-checklist)

---

## 1. System Architecture Overview

OncoSentinel uses a **Hybrid Shared Network** design:
```
                ┌──────────────────────────────────────────────┐
                │             Input Medical Image              │
                └──────────────────────┬───────────────────────┘
                                       │
                         [Input Ingestion & Quality Gate]
                                       │
                         [Intelligent Cancer Router]
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        [Modality-Aware Encoder]              [Clinical RAG Retrieval]
      (Ultrasound, CT, MRI, Histology, etc.)  (NCCN Guidelines, BI-RADS)
                    │                                     │
                    ▼                                     ▼
           [512-dim Latent Code]               [Evidence-Grounded LLM]
                    │                           (Ollama / Llama3 / Gemini)
         ┌──────────┴──────────┐                          │
         ▼                     ▼                          │
[Task-Specific Head]    [Uncertainty & Grad-CAM]          │
 (8 Cancer Categories)   (Conformal Abstention)           │
         │                     │                          │
         └──────────┬──────────┴──────────────────────────┘
                    ▼
     [Tri-Part Clinical Decision Narrative]
    (Model Evidence + Guideline Evidence + Synthesis)
```

---

## 2. Part 1: Local Image Datasets for All 8 Cancer Models

### 2.1 Directory Structure & Class Taxonomy

All image data must be placed inside the `data/datasets/` directory. Each task has its own subfolder, and inside each task folder, images are divided into subdirectories named **strictly after the class labels**:

```text
data/datasets/
├── breast_ultrasound/
│   ├── benign/
│   └── malignant/
│
├── kidney_ct/
│   ├── normal/
│   ├── tumor/
│   ├── cyst/
│   └── stone/
│
├── leukemia_microscopy/
│   ├── normal/
│   └── all_blast/
│
├── oral_cancer/
│   ├── normal/
│   └── oscc/
│
├── lung_colon_histology/
│   ├── colon_adenocarcinoma/
│   ├── colon_benign/
│   ├── lung_adenocarcinoma/
│   ├── lung_benign/
│   └── lung_squamous_cell_carcinoma/
│
├── lymphoma_histology/
│   ├── cll/
│   ├── fl/
│   └── mcl/
│
├── brain_mri/
│   ├── no_tumor/
│   ├── glioma/
│   ├── meningioma/
│   └── pituitary/
│
└── cervical_cytology/
    ├── dyskeratotic/
    ├── koilocytotic/
    ├── metaplastic/
    ├── parabasal/
    └── superficial_intermediate/
```

> [!IMPORTANT]
> The folder names must **exactly match** the class names listed above. The training pipeline dynamically binds folder names to class labels.

---

### 2.2 File Naming Convention & Leakage Prevention (Crucial)

In medical imaging, multiple slices or patches often come from the **same patient**. If slices from Patient A appear in both the training set and the test set, your model will suffer from **subject-level data leakage**, yielding artificially high accuracy that will fail faculty review.

To prevent this, OncoSentinel's `training/split_manifest.py` extracts the `patient_id` from the filename using the part **before the first underscore**:

$$\text{Filename Pattern:}\quad \mathbf{\langle PatientID \rangle\_\langle SliceOrImageID \rangle.\langle ext \rangle}$$

#### Examples of Correct Filenames:
- `patient001_slice01.png`
- `patient001_slice02.png` *(will be grouped together with slice 01 into the same partition)*
- `case42_scan_t1.jpg`
- `subject89_patch004.tif`

#### File Formats Supported:
`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff` (all automatically converted to normalized RGB 3-channel tensors by the modality transforms).

---

### 2.3 Recommended Open Datasets for Reference

If you are sourcing open benchmark datasets to populate these folders, use these standard academic cohorts:

| Task ID | Recommended Dataset | Reference / Source | Modality |
|---|---|---|---|
| `breast_ultrasound` | **BUSI** (Breast Ultrasound Images) | Al-Dhabyani et al. (Kaggle) | Ultrasound |
| `kidney_ct` | **CT Kidney Dataset** (Normal, Cyst, Tumor, Stone) | Islam et al. (Kaggle) | Abdominal CT |
| `leukemia_microscopy` | **C-NMC 2019** (B-ALL White Blood Cells) | Gupta et al. (Cancer Imaging Archive) | Peripheral Blood Smear |
| `oral_cancer` | **OSCC Biopsy Dataset** | Rahman et al. (Mendeley Data) | H&E Histopathology |
| `lung_colon_histology` | **LC25000** | Borkowski et al. (Kaggle / Figshare) | H&E Histopathology |
| `lymphoma_histology` | **NIH Malignant Lymphoma** (CLL, FL, MCL) | Orlov et al. (National Institutes of Health) | H&E Histopathology |
| `brain_mri` | **BraTS / Cheng Brain Tumor Dataset** | Cheng et al. (Figshare / Kaggle) | T1-weighted Contrast MRI |
| `cervical_cytology` | **SIPaKMeD** | Plissiti et al. (Mendeley Data) | Pap Smear Cytology |

---

### 2.4 Converting DICOM (.dcm) & NIfTI (.nii.gz) to PNG

If your local scans are stored in 3D medical formats (DICOM or NIfTI), use the following Python script to extract 2D axial slices with Hounsfield Unit (HU) windowing into the proper folder structure.

Save this script as `scripts/preprocess_medical_images.py`:

```python
"""
Convert 3D NIfTI or 2D DICOM to normalized 2D PNG slices.
Usage:
    python scripts/preprocess_medical_images.py --input raw_data/ --output data/datasets/kidney_ct/tumor/ --prefix patient001
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image

def window_image(image_arr: np.ndarray, window_center: int, window_width: int) -> np.ndarray:
    """Applies CT Hounsfield Unit windowing (e.g. Soft Tissue: W:400, L:40)."""
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    windowed = np.clip(image_arr, img_min, img_max)
    windowed = ((windowed - img_min) / (img_max - img_min) * 255.0).astype(np.uint8)
    return windowed

def convert_nifti(nii_path: Path, out_dir: Path, patient_id: str, window_center=40, window_width=400):
    import nibabel as nib
    out_dir.mkdir(parents=True, exist_ok=True)
    nii = nib.load(str(nii_path))
    data = nii.get_fdata()
    
    # Iterate through axial slices
    num_slices = data.shape[2]
    for s in range(num_slices):
        slice_2d = data[:, :, s]
        # Ignore completely empty air slices
        if np.std(slice_2d) < 5.0:
            continue
        windowed = window_image(slice_2d, window_center, window_width)
        img = Image.fromarray(windowed).rotate(90) # align orientation
        out_file = out_dir / f"{patient_id}_slice{s:03d}.png"
        img.save(out_file)
    print(f"Saved {num_slices} slices from {nii_path.name} to {out_dir}")

def convert_dicom(dcm_path: Path, out_dir: Path, patient_id: str, slice_idx: int):
    import pydicom
    out_dir.mkdir(parents=True, exist_ok=True)
    dcm = pydicom.dcmread(str(dcm_path))
    arr = dcm.pixel_array.astype(np.float32)
    
    # Rescale slope and intercept if present
    intercept = getattr(dcm, 'RescaleIntercept', 0.0)
    slope = getattr(dcm, 'RescaleSlope', 1.0)
    arr = arr * slope + intercept
    
    windowed = window_image(arr, window_center=40, window_width=400)
    img = Image.fromarray(windowed)
    out_file = out_dir / f"{patient_id}_slice{slice_idx:03d}.png"
    img.save(out_file)
```

---

### 2.5 Generating Split Manifests & Running Training

When you place images in `data/datasets/<task_id>/<class_name>/`, you can run training immediately.

#### Option 1: Train a Single Task (e.g. Breast Ultrasound)
```bash
# Trains breast_ultrasound for 15 epochs on your local GPU or CPU
py -3.12 -m training.train_one --config configs/training/breast_ultrasound.yaml --epochs 15
```

What happens automatically:
1. `training/dataset_adapters.py` detects your image files in `data/datasets/breast_ultrasound/`.
2. `training/split_manifest.py` groups slices by `patient_id` and splits them: **70% Train, 15% Validation, 15% Test** (strictly disjoint: $\text{Train} \cap \text{Val} \cap \text{Test} = \emptyset$).
3. The model trains using early stopping on validation loss.
4. Final evaluation runs on the **locked test set**, computing Accuracy, Macro F1, Sensitivity, Specificity, and Expected Calibration Error (ECE).
5. The checkpoint is saved to `artifacts/checkpoints/breast_ultrasound/breast_ultrasound_best.pt` with a deterministic SHA-256 tensor digest.
6. A verified Markdown Model Card is generated at `artifacts/model_cards/breast_ultrasound.md`.

#### Option 2: Train All 8 Tasks Sequentially
To train all 8 models one after another:
```bash
# Runs the sequential queue across all 8 configured cancer tasks
py -3.12 -m training.train_all --force-retrain --epochs 10
```

All 8 task states and metrics will be updated and immediately displayed on the **Model Portfolio & Evidence Dashboard** tab in your web browser.

---

## 3. Part 2: Vector Database (RAG) Setup

### 3.1 What to Put in the Vector DB

The Vector Database provides the **clinical grounding foundation** for OncoSentinel. It ensures that when the system analyzes an image or answers clinical questions, it cites authoritative oncology guidelines rather than making up answers.

You should add documents from the following categories:

1. **National Comprehensive Cancer Network (NCCN) Guidelines:**
   - NCCN Clinical Practice Guidelines in Oncology: Breast Cancer, Kidney Cancer, Central Nervous System Cancers, Acute Lymphoblastic Leukemia, Head and Neck Cancers, Colon & Rectal Cancer, Cervical Cancer, and B-Cell Lymphomas.
2. **Imaging Staging & Classification Manuals:**
   - **ACR BI-RADS Atlas (5th Edition):** Diagnostic ultrasound and mammography criteria for breast lesion scoring (BI-RADS 2, 3, 4A/B/C, 5).
   - **Bosniak Classification of Cystic Renal Masses (2019 Version):** CT/MRI criteria for renal neoplasms (Bosniak I to IV).
   - **WHO Classification of Tumours of the Central Nervous System (5th Edition):** Histological & molecular criteria for gliomas, meningiomas, and pituitary adenomas.
   - **ASCCP Consensus Guidelines:** Cervical cancer screening, Pap smear cytology interpretation, and management of abnormal cervical cytology.
3. **Key Landmark Clinical Research Papers:**
   - Papers establishing the diagnostic sensitivity and specificity of medical imaging techniques in your target organs.

---

### 3.2 Selecting Your Vector Store (Qdrant vs. Chroma vs. In-Memory)

OncoSentinel natively supports two vector store modes configured via `.env`:

| Mode | Best For | Setup Required | Persistence |
|---|---|---|---|
| **Qdrant (Docker)** | Production / Full Demo | `docker-compose up -d qdrant` | Persistent on disk (`http://localhost:6333`) |
| **In-Memory Fallback** | Instant Prototyping / Testing | Zero installation (built-in fallback in `services/rag/vector_store.py`) | Session-only (auto-seeds baseline guidelines) |

#### Starting Qdrant with Docker:
```bash
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

In your `.env` file, verify:
```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_EVIDENCE=clinical_evidence
```

---

### 3.3 Document Ingestion Script (PDF & Text to Vector DB)

Here is a ready-to-run Python script to chunk and ingest local guideline PDFs or text files into OncoSentinel's Vector Store.

Create a folder `data/guidelines/` and save this script as `scripts/ingest_guidelines.py`:

```python
"""
OncoSentinel Guideline Ingestion Script
Extracts text from guideline PDFs, chunks them, and stores them in Qdrant or VectorStore.
"""
from pathlib import Path
import re
from typing import List, Dict

# Optional: PyMuPDF for high-quality PDF parsing
try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None

from services.rag.vector_store import get_vector_store, KnowledgeChunk

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Splits text into overlapping word chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.split()) > 30: # discard tiny snippets
            chunks.append(chunk)
    return chunks

def ingest_file(file_path: Path, category: str, citation_id: str, title: str):
    store = get_vector_store()
    print(f"\nProcessing {file_path.name}...")

    # Extract text
    full_text = ""
    if file_path.suffix.lower() == ".pdf":
        if fitz is None:
            raise RuntimeError("Please install PyMuPDF: py -3.12 -m pip install pymupdf")
        doc = fitz.open(str(file_path))
        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text()
            full_text += f"\n[Page {page_num+1}] " + page_text
    else:
        full_text = file_path.read_text(encoding="utf-8")

    clean = clean_text(full_text)
    chunks = chunk_text(clean, chunk_size=350, overlap=50)
    print(f"Created {len(chunks)} chunks for {title}")

    # Add each chunk to the Vector Store
    for idx, chunk_content in enumerate(chunks):
        chunk_obj = KnowledgeChunk(
            chunk_id=f"{citation_id}_{idx:04d}",
            source_title=title,
            citation_id=citation_id,
            category=category,
            content=chunk_content,
            metadata={"file_name": file_path.name, "chunk_index": idx}
        )
        store.add_chunk(chunk_obj)

    print(f"Successfully indexed {len(chunks)} chunks into vector store.")

if __name__ == "__main__":
    # Example ingestion:
    guidelines_dir = Path("data/guidelines")
    if not guidelines_dir.exists():
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory {guidelines_dir}. Place your PDF/TXT files there.")

    # Example: Ingest breast guidelines if present
    sample_pdf = guidelines_dir / "nccn_breast_2024.pdf"
    if sample_pdf.exists():
        ingest_file(
            file_path=sample_pdf,
            category="breast",
            citation_id="NCCN-BREAST-2024",
            title="NCCN Clinical Practice Guidelines in Oncology: Breast Cancer (v2.2024)"
        )
    else:
        print(f"Place your PDF files in {guidelines_dir.resolve()} and re-run.")
```

#### Run Ingestion:
```bash
py -3.12 scripts/ingest_guidelines.py
```

---

### 3.4 Embedding Model Selection

OncoSentinel's default configuration uses dense semantic embeddings combined with lexical BM25 token matching for hybrid retrieval.

| Embedding Model | Dimension | Speed | Domain Match | Recommendation |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | Very Fast (~15ms) | General / Good | **Default / Best for Local Laptop CPU** |
| `pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb` | 768 | Moderate (~40ms) | Biomedical | Best for Clinical Accuracy |
| `BAAI/bge-base-en-v1.5` | 768 | Fast (~30ms) | Excellent RAG Benchmark | High-Precision Retrieval |

---

## 4. Part 3: Selecting and Connecting the LLM

### 4.1 Which LLM Should You Use?

The LLM in OncoSentinel does **not** predict the cancer diagnosis (that is the job of the calibrated PyTorch neural networks). Instead, the LLM functions as a **Clinical Synthesizer**: it takes the image features, Grad-CAM concepts, uncertainty scores, and retrieved NCCN/BI-RADS guidelines, and synthesizes them into an evidence-grounded clinical narrative.

#### Recommended Models:

1. **Top Recommendation (Offline / Local): `llama3:8b` or `llama3.1:8b`**
   - **Why:** Extremely reliable instruction-following, adheres strictly to bracketed citation constraints (`[CITATION_ID]`), runs smoothly on 6GB-8GB VRAM (or even CPU).
2. **Specialized Biomedical Model: `biomistral:7b`**
   - **Why:** Pre-trained on PubMed Central; understands medical terminology (TNM staging, RECIST, Gleason scores, flow cytometry markers).
3. **Cloud Option: Google Gemini API (`gemini-1.5-flash` or `gemini-2.5-flash`)**
   - **Why:** Instant response times, zero local GPU requirements, massive context window.

---

### 4.2 Option A: Local Ollama (Recommended)

Ollama is the easiest and most robust way to run open LLMs locally on Windows, macOS, or Linux.

#### Step 1: Install Ollama
Download and run the installer from:
👉 **[https://ollama.com/download](https://ollama.com/download)**

#### Step 2: Pull and Start Your Chosen Model
Open PowerShell or Command Prompt:
```bash
# Pull and start Llama 3 (8B parameters, 4-bit quantized ~4.7GB)
ollama run llama3:8b
```
*(Or for BioMistral)*:
```bash
ollama run biomistral:7b
```

Once running, Ollama hosts an OpenAI-compatible REST server at `http://localhost:11434`.

#### Step 3: Configure OncoSentinel
In your `.env` file (or set via environment variables):
```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

OncoSentinel's `services/rag/llm_reasoning.py` will automatically route evidence-grounded queries to Ollama. If Ollama is temporarily closed, OncoSentinel gracefully falls back to its deterministic grounded synthesizer without crashing.

---

### 4.3 Option B: Cloud Gemini API

If your laptop has limited RAM or lacks a dedicated GPU, you can connect the Google Gemini API.

1. Get a Gemini API Key from Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
2. In your `.env` file, add:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   LLM_BACKEND=gemini
   GEMINI_MODEL=gemini-1.5-flash
   ```

---

### 4.4 Grounded Prompting & Non-Fabrication Rules

In [`services/rag/llm_reasoning.py`](file:///c:/Users/ACER/Desktop/RAG%20Major%20Project/services/rag/llm_reasoning.py), the LLM is constrained by strict safety rules:

```text
CRITICAL CLINICAL RULES:
1. You must answer ONLY using the supplied guideline evidence.
2. Cite every factual assertion using bracketed tags: [CITATION_ID].
3. Do NOT extrapolate, speculate, or recommend treatments not supported by the evidence.
4. If the retrieved evidence does not contain sufficient details, you must output:
   "NO_GROUNDED_ANSWER: Insufficient clinical evidence retrieved to answer safely."
```

This prevents hallucinations and satisfies academic review criteria regarding AI safety and non-autonomous decision support.

---

## 5. Part 4: Hardware Requirements & Optimization

### Recommended Hardware Specifications:

| Component | Minimum (CPU Mode) | Recommended (GPU Mode) |
|---|---|---|
| **CPU** | 4 cores (Intel i5/i7 or AMD Ryzen 5) | 8 cores (Intel i7/i9 or AMD Ryzen 7) |
| **RAM** | 16 GB | 32 GB |
| **GPU** | None (CPU training supported) | NVIDIA RTX 3060, 4060, 4070 or better (8GB+ VRAM) |
| **Disk Space** | 20 GB free | 50 GB SSD |

### Performance Tuning Tips:
- **Out of Memory (OOM) on GPU during training?**
  In `configs/training/<task_id>.yaml`, lower the `batch_size` from `16` or `32` to `8` or `4`.
- **Speeding up training on NVIDIA GPUs:**
  Ensure CUDA is active in PyTorch:
  ```bash
  py -3.12 -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
  ```

---

## 6. Part 5: End-to-End Execution Checklist

Here is your exact sequence of commands to go from raw images to a fully operational, faculty-ready system:

```bash
# ── Step 1: Place your local images in data/datasets/<task_id>/<class_name>/
# Example: data/datasets/breast_ultrasound/benign/patient01_01.png
#          data/datasets/breast_ultrasound/malignant/patient02_01.png

# ── Step 2: Delete any old synthetic split manifests to force a fresh scan
powershell -Command "Remove-Item artifacts/manifests/*_split.json -ErrorAction SilentlyContinue"

# ── Step 3: Run the Sequential Training Queue
# This trains all 8 tasks, generates split manifests, computes real metrics,
# saves cryptographic SHA-256 checkpoints, and emits 8 verified Model Cards
py -3.12 -m training.train_all --force-retrain --epochs 10

# ── Step 4: Start Ollama for Evidence-Grounded Reasoning
# Open a separate terminal:
ollama run llama3:8b

# ── Step 5: (Optional) Ingest Additional Guideline PDFs into Vector DB
py -3.12 scripts/ingest_guidelines.py

# ── Step 6: Verify the Complete Test Suite
py -3.12 -m pytest tests/ -o addopts="" -q
# Expected output: 59 passed in ~50s

# ── Step 7: Launch the Application Gateway & UI
py -3.12 -m uvicorn services.gateway.app:app --host 0.0.0.0 --port 8000 --reload
```

Now open your web browser to:
👉 **`http://localhost:8000`**

Navigate to the **Model Portfolio & Evidence** tab to:
- Review live test metrics (Accuracy, Macro F1, Calibrated ECE).
- Click **"View Model Card"** for any of the 8 cancer tasks.
- Click **"Export Faculty Briefing"** to view and print the official verification brief for academic defense.
