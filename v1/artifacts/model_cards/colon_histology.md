# Model Card — colon_histology (COLON)

## 1. Model Details
- **Task ID**: `colon_histology`
- **Category**: `colon`
- **Modality**: `histology`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/colon.pth`
- **SHA-256 Digest**: `f7c454303152f256ad48441be3ef76216d2fd6f9d3a54a9bbc099219803090ce`
- **Target Classes (2)**: `colon_aca, colon_bnt`

## 2. Dataset & Provenance
- **Dataset ID**: `LC25000-Colon-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `97.8%`
- **Macro F1**: `97.7%`
- **Macro ROC-AUC**: `0.992`
- **Sensitivity**: `98.0%`
- **Specificity**: `97.6%`
- **Expected Calibration Error (ECE)**: `0.021`
- **Brier Score**: `0.029`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

