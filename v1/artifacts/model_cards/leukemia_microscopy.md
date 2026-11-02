# Model Card — leukemia_microscopy (ALL_LEUKEMIA)

## 1. Model Details
- **Task ID**: `leukemia_microscopy`
- **Category**: `all_leukemia`
- **Modality**: `microscopy`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/ALL.pth`
- **SHA-256 Digest**: `81cbf9c5ff4f3e7c69cf70e5ddde39528c11562c074c6611489ac01d5e12b5be`
- **Target Classes (4)**: `all_benign, all_early, all_pre, all_pro`

## 2. Dataset & Provenance
- **Dataset ID**: `C-NMC-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `95.2%`
- **Macro F1**: `94.8%`
- **Macro ROC-AUC**: `0.981`
- **Sensitivity**: `95.4%`
- **Specificity**: `95.0%`
- **Expected Calibration Error (ECE)**: `0.029`
- **Brier Score**: `0.044`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

