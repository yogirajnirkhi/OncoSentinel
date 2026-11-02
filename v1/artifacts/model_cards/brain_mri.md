# Model Card — brain_mri (BRAIN)

## 1. Model Details
- **Task ID**: `brain_mri`
- **Category**: `brain`
- **Modality**: `mri`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/brain_tumor.pth`
- **SHA-256 Digest**: `d73579f6d4ac5cda67f816ce2a15c8a2b47435b46541d2ee48f252282e71edf5`
- **Target Classes (3)**: `brain_glioma, brain_menin, brain_tumor`

## 2. Dataset & Provenance
- **Dataset ID**: `BraTS2023-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `94.7%`
- **Macro F1**: `94.5%`
- **Macro ROC-AUC**: `0.979`
- **Sensitivity**: `94.9%`
- **Specificity**: `94.4%`
- **Expected Calibration Error (ECE)**: `0.031`
- **Brier Score**: `0.048`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

