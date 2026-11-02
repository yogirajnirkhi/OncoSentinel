# Model Card — oral_cancer (ORAL)

## 1. Model Details
- **Task ID**: `oral_cancer`
- **Category**: `oral`
- **Modality**: `histology`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/oral_model.pth`
- **SHA-256 Digest**: `4446d83fc235780206619ed5a037ac0b9e8bfe18eadb07660c86e8cb5d7074b0`
- **Target Classes (2)**: `normal, oscc`

## 2. Dataset & Provenance
- **Dataset ID**: `OralHisto-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `94.1%`
- **Macro F1**: `93.9%`
- **Macro ROC-AUC**: `0.972`
- **Sensitivity**: `94.5%`
- **Specificity**: `93.7%`
- **Expected Calibration Error (ECE)**: `0.032`
- **Brier Score**: `0.052`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

