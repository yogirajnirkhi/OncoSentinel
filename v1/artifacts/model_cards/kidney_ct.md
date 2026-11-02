# Model Card — kidney_ct (KIDNEY)

## 1. Model Details
- **Task ID**: `kidney_ct`
- **Category**: `kidney`
- **Modality**: `ct`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/kidney_model.pth`
- **SHA-256 Digest**: `b0ad31aa209358f9dff0643adcf66a1a387ee1c71dfca1ccb03c5251be28b071`
- **Target Classes (2)**: `normal, tumor`

## 2. Dataset & Provenance
- **Dataset ID**: `CT-Kidney-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `96.4%`
- **Macro F1**: `96.2%`
- **Macro ROC-AUC**: `0.985`
- **Sensitivity**: `96.8%`
- **Specificity**: `96.0%`
- **Expected Calibration Error (ECE)**: `0.028`
- **Brier Score**: `0.041`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

