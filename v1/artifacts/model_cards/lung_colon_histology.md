# Model Card — lung_colon_histology (LUNG_COLON)

## 1. Model Details
- **Task ID**: `lung_colon_histology`
- **Category**: `lung_colon`
- **Modality**: `histology`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/lung.pth`
- **SHA-256 Digest**: `32551a1e0a4af46d1c58b51742477dacee555ca7927515eb27a36369646e171e`
- **Target Classes (5)**: `colon_aca, colon_bnt, lung_aca, lung_bnt, lung_scc`

## 2. Dataset & Provenance
- **Dataset ID**: `LC25000-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `96.8%`
- **Macro F1**: `96.6%`
- **Macro ROC-AUC**: `0.989`
- **Sensitivity**: `97.0%`
- **Specificity**: `96.5%`
- **Expected Calibration Error (ECE)**: `0.024`
- **Brier Score**: `0.034`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

