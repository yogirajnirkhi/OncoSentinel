# Model Card — breast_ultrasound (BREAST)

## 1. Model Details
- **Task ID**: `breast_ultrasound`
- **Category**: `breast`
- **Modality**: `ultrasound`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `UNTRAINED`
- **Checkpoint Path**: `None (Untrained — Refuses Inference Safely)`
- **SHA-256 Digest**: `N/A`
- **Target Classes (2)**: `benign, malignant`

## 2. Dataset & Provenance
- **Dataset ID**: `BUSI-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Status**: `UNTRAINED` — Model weights are not yet deployed. Any inference request to this category safely raises `UntrainedModelError`.

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

