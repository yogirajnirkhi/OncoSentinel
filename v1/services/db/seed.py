"""
OncoSentinel v2.0 — Database Seeding Script
Initializes authentic staff users, registered datasets, models, studies, cases,
and full authoritative Hospital Management System (HMS) operational records.
Satisfies: FR-01, FR-16, FR-26, FR-27, FR-28, FR-29, SRS §1.4, SRS §11
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from services.core.logging import get_logger
from services.db.models import Case, Dataset, ModelVersion, Study, User
from services.db.session import SyncSessionLocal
from services.gateway.auth import ALL_ROLES, hash_password
from services.hms.seed_data import seed_hms_data

logger = get_logger(__name__)

DEFAULT_PASSWORD = "OncoUser2026!"


def seed_database(session: Session | None = None) -> None:
    """Seed users, datasets, models, cases, and HMS operational records."""
    db: Session = session if session is not None else SyncSessionLocal()
    should_close = session is None
    try:
        # Remove obsolete / corrupted demo accounts if present
        bad_users = db.query(User).filter(User.username.in_(["s", "s1"])).all()
        for bu in bad_users:
            db.delete(bu)
        db.flush()

        # 1. Seed Authentic Staff Users with salted PBKDF2 hashes
        if not db.query(User).first():
            staff_users = [
                ("dr_chen", "sarah.chen@oncosentinel.hospital.org", "Dr. Sarah Chen, MD", "CLINICIAN", ["CLINICIAN"], "Medical Oncology"),
                ("dr_patel", "rajesh.patel@oncosentinel.hospital.org", "Dr. Rajesh Patel, MD", "RADIOLOGIST", ["RADIOLOGIST", "PATHOLOGIST"], "Diagnostic Radiology"),
                ("dr_adams", "marcus.adams@oncosentinel.hospital.org", "Dr. Marcus Adams, MD, PhD", "PATHOLOGIST", ["PATHOLOGIST", "RADIOLOGIST"], "Surgical Pathology"),
                ("nurse_sarah", "sarah.jenkins@oncosentinel.hospital.org", "Sarah Jenkins, BSN, RN", "SCHEDULER", ["SCHEDULER", "RECEPTION"], "Ambulatory Oncology Clinic"),
                ("pharma_alex", "alex.rivera@oncosentinel.hospital.org", "Alex Rivera, PharmD, BCOP", "PHARMACIST", ["PHARMACIST", "INVENTORY_MANAGER"], "Clinical Oncology Pharmacy"),
                ("billing_mark", "mark.davis@oncosentinel.hospital.org", "Mark Davis, CRCR", "BILLING_CLERK", ["BILLING_CLERK", "FINANCE"], "Patient Financial Services"),
                ("admin_clara", "clara.vance@oncosentinel.hospital.org", "Clara Vance, MHA", "ADMIN", list(ALL_ROLES), "Hospital Administration"),
                ("research_elena", "elena.rostova@oncosentinel.hospital.org", "Dr. Elena Rostova, MD, PhD", "RESEARCHER", ["RESEARCHER", "ANALYST"], "Translational Cancer Research"),
            ]
            for uname, email, fname, primary_role, roles, dept in staff_users:
                pwd_hash, salt = hash_password(DEFAULT_PASSWORD)
                u = User(
                    username=uname,
                    email=email,
                    hashed_password=pwd_hash,
                    salt=salt,
                    full_name=fname,
                    role=primary_role,
                    roles=roles,
                    department=dept,
                    is_active=True,
                )
                db.add(u)
            db.flush()
            logger.info("authentic_staff_users_seeded", count=len(staff_users))

        # 2. Seed Initial Clinical Cases
        if not db.query(Case).first():
            case1 = Case(
                id="CASE-BR-2024-8841",
                metadata_json={"age": 52, "biopsy_site": "retroareolar", "scanner": "Siemens"},
                status="active",
            )
            case2 = Case(
                id="CASE-KD-2024-5512",
                metadata_json={"age": 61, "sex": "female", "protocol": "contrast_enhanced", "anatomy": "left_kidney"},
                status="active",
            )
            case3 = Case(
                id="CASE-OR-2024-1102",
                metadata_json={"age": 58, "sex": "male", "protocol": "mucosal_biopsy", "anatomy": "oral_tongue"},
                status="active",
            )
            db.add_all([case1, case2, case3])
            db.flush()
            logger.info("cases_seeded")

        # 3. Seed Registered Datasets (FR-27)
        if not db.query(Dataset).first():
            ds_busi = Dataset(
                id=str(uuid.uuid4()),
                dataset_id="BUSI-v1",
                version="1.0.0",
                category="breast",
                source="Breast Ultrasound Images Dataset (Al-Dhabyani et al.)",
                license="CC-BY-4.0",
                n_train=600,
                n_val=90,
                n_test=90,
                n_external_val=120,
                split_hash="sha256_busi_split_hash",
                patient_ids_hash="sha256_patient_busi_hash",
                site_ids=["Site-01-Cairo", "Site-02-Alexandria"],
            )
            ds_kits = Dataset(
                id=str(uuid.uuid4()),
                dataset_id="KiTS23-v1",
                version="1.0.0",
                category="kidney",
                source="Kidney Tumor Segmentation Challenge 2023 (Heller et al.)",
                license="CC-BY-NC-SA-4.0",
                n_train=400,
                n_val=50,
                n_test=50,
                n_external_val=100,
                split_hash="sha256_kits_split_hash",
                patient_ids_hash="sha256_patient_kits_hash",
                site_ids=["Site-03-Minnesota", "Site-04-Cleveland"],
            )
            ds_oral = Dataset(
                id=str(uuid.uuid4()),
                dataset_id="Oral-SCC-v1",
                version="1.0.0",
                category="oral",
                source="Oral Cavity Squamous Cell Histopathology Dataset (Rahman et al.)",
                license="CC-BY-4.0",
                n_train=450,
                n_val=60,
                n_test=60,
                n_external_val=80,
                split_hash="sha256_oral_split_hash",
                patient_ids_hash="sha256_patient_oral_hash",
                site_ids=["Site-05-London", "Site-06-Toronto"],
            )
            db.add_all([ds_busi, ds_kits, ds_oral])
            db.flush()
            logger.info("datasets_seeded")

        # 4. Seed Registered Model Versions (FR-26)
        if not db.query(ModelVersion).first():
            seeded_models = [
                ("onco_kidney_classifier", "2.0.0-mobilenet", "kidney", ["ct"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_oral_classifier", "2.0.0-mobilenet", "oral", ["histology"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_all_leukemia_classifier", "2.0.0-mobilenet", "all_leukemia", ["microscopy"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_brain_classifier", "2.0.0-mobilenet", "brain", ["mri"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_cervical_classifier", "2.0.0-mobilenet", "cervical", ["cytology"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_colon_classifier", "2.0.0-mobilenet", "colon", ["histology"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_lung_classifier", "2.0.0-mobilenet", "lung", ["histology"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_lung_colon_classifier", "2.0.0-mobilenet", "lung_colon", ["histology"], "MobileNetV3-Small", "PRODUCTION", True),
                ("onco_breast_classifier", "2.0.0", "breast", ["ultrasound"], "unassigned", "CANDIDATE", False),
                ("onco_lymphoma_classifier", "2.0.0", "lymphoma", ["histology"], "unassigned", "CANDIDATE", False),
            ]
            for mid, ver, cat, mods, bb, st, passed in seeded_models:
                db.add(
                    ModelVersion(
                        id=str(uuid.uuid4()),
                        model_id=mid,
                        version=ver,
                        category=cat,
                        modality=mods,
                        backbone_version=bb,
                        status=st,
                        uncertainty_policy_version="policy_v2.0.0",
                        promotion_gate_results={"fairness_passed": passed, "calibration_passed": passed},
                    )
                )
            db.flush()
            logger.info("models_seeded", count=len(seeded_models))

        # 5. Seed Clinical Study Protocol (FR-21)
        if not db.query(Study).first():
            study = Study(
                id=str(uuid.uuid4()),
                protocol_version="ONCO-PILOT-2024-v2",
                name="Multimodal Decision-Support Workflow & Usability Pilot",
                arms=["AI_ASSISTED", "STANDARD_OF_CARE"],
                primary_endpoint="time_to_diagnosis",
                secondary_endpoints=["clinician_agreement", "override_rate", "unsafe_misses"],
                status="ACTIVE",
            )
            db.add(study)
            db.flush()
            logger.info("study_seeded")

        # 6. Seed All 31 Authoritative HMS Resources
        seed_hms_data(db)

        db.commit()
        logger.info("database_seeding_complete")
    except Exception as exc:
        db.rollback()
        logger.warning("database_seed_warning", error=str(exc))
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_database()
