# Model Card — cervical_cytology (CERVICAL)

## 1. Model Details
- **Task ID**: `cervical_cytology`
- **Category**: `cervical`
- **Modality**: `cytology`
- **Architecture**: `MobileNetV3-Small` (576-dim feature backbone)
- **Status**: `ACTIVE`
- **Checkpoint Path**: `../models/Cervical.pth`
- **SHA-256 Digest**: `3d60f22fd8f9ba57660a5556f0b9c70162131b21795ee2eb58d917f1458e7d82`
- **Target Classes (5)**: `cervix_dyk, cervix_koc, cervix_mep, cervix_pab, cervix_sfi`

## 2. Dataset & Provenance
- **Dataset ID**: `SIPaKMeD-v1`
- **Input Resolution**: `224x224 RGB` (ImageNet normalized)

## 3. Evaluation Metrics
- **Accuracy**: `93.8%`
- **Macro F1**: `93.5%`
- **Macro ROC-AUC**: `0.974`
- **Sensitivity**: `94.0%`
- **Specificity**: `93.6%`
- **Expected Calibration Error (ECE)**: `0.035`
- **Brier Score**: `0.056`

## 4. Intended Use, Safety, Explainability & Governance
- **Explainability**: Class-discriminative Grad-CAM (`GradCAMGenerator`) computed from spatial gradients of the final MobileNetV3 convolutional block (`576x7x7`).
- **Uncertainty & OOD Gate**: Temperature-scaled softmax entropy, energy-based OOD scoring, and feature norm distance with 3-state routing (`PASS`, `REVIEW`, `ABSTAIN`).
- **Intended Use**: Advisory decision support only; requires attributed clinician review in HMS.

