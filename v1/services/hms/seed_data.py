"""
OncoSentinel v2.0 — Authoritative Hospital Management System (HMS) Operational Seed Data
Populates all 31 HMS resources with fully linked, realistic oncology clinical and operational records.
Satisfies: SRS §1.4, SRS §11, FR-01, FR-16, FR-29.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
from typing import Any

from sqlalchemy.orm import Session

from services.core.logging import get_logger
from services.hms.models import (
    AiReviews,
    Alerts,
    BillingAdjustments,
    BillingChargeItems,
    BillingClaims,
    BillingInvoiceLines,
    BillingInvoices,
    BillingPayments,
    Encounters,
    FinanceLedger,
    FinancePeriods,
    InventoryItems,
    InventoryMovements,
    InventoryPurchaseOrders,
    InventoryReceipts,
    LabOrders,
    LabResults,
    LabTests,
    MedicalRecords,
    Patients,
    PharmacyDispense,
    PharmacyMedications,
    PharmacyPrescriptions,
    RadiologyOrders,
    RadiologyReports,
    RadiologyStudies,
    SchedulingAppointments,
    SchedulingAvailability,
    SchedulingShifts,
    SchedulingSwaps,
    Staff,
)

logger = get_logger(__name__)


def seed_hms_data(db: Session) -> None:
    """Populates empty HMS tables with realistic clinical and operational records."""
    if db.query(Patients).first():
        logger.info("hms_already_seeded_skipping")
        return

    logger.info("hms_seeding_started")
    now = datetime.now(timezone.utc)
    base_actor = "admin_clara"
    req_id = str(uuid.uuid4())

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Staff Members (Corresponding to Authentic Users)
    # ──────────────────────────────────────────────────────────────────────────
    staff_chen = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111101"),
        display_name="Dr. Sarah Chen, MD",
        role="CLINICIAN",
        department="Medical Oncology",
        credentials={"degree": "MD", "specialty": "Medical Oncology", "npi": "1841294821"},
        license_expiry=date(2028, 6, 30),
        contact={"email": "sarah.chen@oncosentinel.hospital.org", "pager": "3412"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_patel = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111102"),
        display_name="Dr. Rajesh Patel, MD",
        role="RADIOLOGIST",
        department="Diagnostic Radiology",
        credentials={"degree": "MD", "subspecialty": "Abdominal & Oncologic Imaging", "npi": "1952385932"},
        license_expiry=date(2027, 12, 31),
        contact={"email": "rajesh.patel@oncosentinel.hospital.org", "pager": "5819"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_adams = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111103"),
        display_name="Dr. Marcus Adams, MD, PhD",
        role="PATHOLOGIST",
        department="Surgical Pathology",
        credentials={"degree": "MD, PhD", "specialty": "Head & Neck Pathology", "npi": "1048291042"},
        license_expiry=date(2029, 3, 15),
        contact={"email": "marcus.adams@oncosentinel.hospital.org", "pager": "2091"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_sarah = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111104"),
        display_name="Sarah Jenkins, BSN, RN",
        role="SCHEDULER",
        department="Ambulatory Oncology Clinic",
        credentials={"degree": "BSN, RN", "certification": "OCN (Oncology Certified Nurse)"},
        license_expiry=date(2027, 9, 30),
        contact={"email": "sarah.jenkins@oncosentinel.hospital.org", "extension": "4102"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_alex = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111105"),
        display_name="Alex Rivera, PharmD, BCOP",
        role="PHARMACIST",
        department="Clinical Oncology Pharmacy",
        credentials={"degree": "PharmD", "board": "Board Certified Oncology Pharmacist"},
        license_expiry=date(2028, 4, 30),
        contact={"email": "alex.rivera@oncosentinel.hospital.org", "extension": "7712"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_mark = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111106"),
        display_name="Mark Davis, CRCR",
        role="BILLING_CLERK",
        department="Patient Financial Services",
        credentials={"certification": "Certified Revenue Cycle Representative"},
        license_expiry=date(2029, 1, 31),
        contact={"email": "mark.davis@oncosentinel.hospital.org", "extension": "8841"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_clara = Staff(
        id=uuid.UUID("11111111-1111-1111-1111-111111111107"),
        display_name="Clara Vance, MHA",
        role="ADMIN",
        department="Hospital Operations & Administration",
        credentials={"degree": "MHA, FACHE"},
        license_expiry=date(2030, 1, 1),
        contact={"email": "clara.vance@oncosentinel.hospital.org", "extension": "1001"},
        actor_id=base_actor,
        request_id=req_id,
    )
    staff_records = [staff_chen, staff_patel, staff_adams, staff_sarah, staff_alex, staff_mark, staff_clara]
    db.add_all(staff_records)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Patients (Clinical Oncology Registry)
    # ──────────────────────────────────────────────────────────────────────────
    p1_id = uuid.UUID("22222222-2222-2222-2222-222222222201")
    p2_id = uuid.UUID("22222222-2222-2222-2222-222222222202")
    p3_id = uuid.UUID("22222222-2222-2222-2222-222222222203")
    p4_id = uuid.UUID("22222222-2222-2222-2222-222222222204")
    p5_id = uuid.UUID("22222222-2222-2222-2222-222222222205")
    p6_id = uuid.UUID("22222222-2222-2222-2222-222222222206")
    p7_id = uuid.UUID("22222222-2222-2222-2222-222222222207")
    p8_id = uuid.UUID("22222222-2222-2222-2222-222222222208")
    p9_id = uuid.UUID("22222222-2222-2222-2222-222222222209")

    patient_records = [
        Patients(
            id=p1_id,
            mrn="MRN-2026-KD-001",
            given_name="Eleanor",
            family_name="Vance",
            birth_date=date(1965, 4, 12),
            gender="female",
            contact={"phone": "+1-555-0142", "email": "e.vance@example.org", "address": "422 Pinecrest Ave, Seattle WA"},
            insurance={"payer": "Blue Cross Blue Shield", "policy_id": "BCBS-99410", "group": "WA-881"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-15", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p2_id,
            mrn="MRN-2026-OR-002",
            given_name="Robert",
            family_name="Kovacs",
            birth_date=date(1958, 9, 23),
            gender="male",
            contact={"phone": "+1-555-0188", "email": "r.kovacs@example.org", "address": "108 Maple Rd, Portland OR"},
            insurance={"payer": "Medicare Part B", "policy_id": "MED-44102", "group": "US-MED"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-18", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p3_id,
            mrn="MRN-2026-BR-003",
            given_name="Maria",
            family_name="Santos",
            birth_date=date(1978, 11, 5),
            gender="female",
            contact={"phone": "+1-555-0199", "email": "m.santos@example.org", "address": "774 Highland Blvd, Bellevue WA"},
            insurance={"payer": "Aetna Health", "policy_id": "AET-77182", "group": "AET-EMP"},
            consent={"research_opt_in": False, "ai_decision_support_consent": True, "signed_at": "2026-10-20", "consent_tier": "Clinical AI Only"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p4_id,
            mrn="MRN-2026-GI-004",
            given_name="Arthur",
            family_name="Pendleton",
            birth_date=date(1952, 2, 17),
            gender="male",
            contact={"phone": "+1-555-0211", "email": "a.pendleton@example.org", "address": "315 Cedar Way, Tacoma WA"},
            insurance={"payer": "United Healthcare", "policy_id": "UHC-33821", "group": "UHC-SENIOR"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-22", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p5_id,
            mrn="MRN-2026-LK-005",
            given_name="David",
            family_name="Zhao",
            birth_date=date(1992, 6, 14),
            gender="male",
            contact={"phone": "+1-555-0245", "email": "d.zhao@example.org", "address": "890 Mercer St, Seattle WA"},
            insurance={"payer": "Cigna Health", "policy_id": "CIG-55219", "group": "CIG-TECH"},
            consent={"research_opt_in": False, "ai_decision_support_consent": False, "signed_at": "2026-10-23", "consent_tier": "Standard Care"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p6_id,
            mrn="MRN-2026-BN-006",
            given_name="Elena",
            family_name="Rostova",
            birth_date=date(1971, 8, 29),
            gender="female",
            contact={"phone": "+1-555-0261", "email": "e.rostova@example.org", "address": "512 Capitol Hill, Seattle WA"},
            insurance={"payer": "Kaiser Permanente", "policy_id": "KP-88301", "group": "KP-NW"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-24", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p7_id,
            mrn="MRN-2026-LY-007",
            given_name="Marcus",
            family_name="Vance",
            birth_date=date(1960, 1, 19),
            gender="male",
            contact={"phone": "+1-555-0277", "email": "m.vance@example.org", "address": "204 Queen Anne Ave, Seattle WA"},
            insurance={"payer": "Blue Cross Blue Shield", "policy_id": "BCBS-61204", "group": "WA-881"},
            consent={"research_opt_in": False, "ai_decision_support_consent": True, "signed_at": "2026-10-25", "consent_tier": "Clinical AI Only"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p8_id,
            mrn="MRN-2026-CX-008",
            given_name="Priya",
            family_name="Nair",
            birth_date=date(1984, 5, 3),
            gender="female",
            contact={"phone": "+1-555-0290", "email": "p.nair@example.org", "address": "741 Redmond Way, Redmond WA"},
            insurance={"payer": "Premera Blue Cross", "policy_id": "PBC-74011", "group": "PBC-CORP"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-26", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Patients(
            id=p9_id,
            mrn="MRN-2026-LG-009",
            given_name="Samuel",
            family_name="Okafor",
            birth_date=date(1955, 12, 11),
            gender="male",
            contact={"phone": "+1-555-0309", "email": "s.okafor@example.org", "address": "119 Harbor Ave, Seattle WA"},
            insurance={"payer": "Medicare Part B", "policy_id": "MED-99214", "group": "US-MED"},
            consent={"research_opt_in": True, "ai_decision_support_consent": True, "signed_at": "2026-10-27", "consent_tier": "Clinical AI & Research"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(patient_records)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Encounters (Attending Encounters — Unique IDs & Varied Statuses)
    # ──────────────────────────────────────────────────────────────────────────
    enc1_id = uuid.UUID("33333333-0001-0000-0000-000000000001")
    enc2_id = uuid.UUID("33333333-0002-0000-0000-000000000002")
    enc3_id = uuid.UUID("33333333-0003-0000-0000-000000000003")
    enc4_id = uuid.UUID("33333333-0004-0000-0000-000000000004")
    enc5_id = uuid.UUID("33333333-0005-0000-0000-000000000005")
    enc6_id = uuid.UUID("33333333-0006-0000-0000-000000000006")
    enc7_id = uuid.UUID("33333333-0007-0000-0000-000000000007")
    enc8_id = uuid.UUID("33333333-0008-0000-0000-000000000008")
    enc9_id = uuid.UUID("33333333-0009-0000-0000-000000000009")

    encounter_records = [
        Encounters(
            id=enc1_id,
            patient_id=p1_id,
            department="Urologic Oncology Clinic",
            attending_id="dr_chen",
            started_at=now - timedelta(days=3),
            ended_at=None,
            status="active",
            extra={"readable_id": "ENC-2026-0001"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc2_id,
            patient_id=p2_id,
            department="Head & Neck Surgical Oncology",
            attending_id="dr_chen",
            started_at=now - timedelta(days=2),
            ended_at=None,
            status="active",
            extra={"readable_id": "ENC-2026-0002"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc3_id,
            patient_id=p3_id,
            department="Comprehensive Breast Center",
            attending_id="dr_chen",
            started_at=now + timedelta(days=1),
            ended_at=None,
            status="scheduled",
            extra={"readable_id": "ENC-2026-0003"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc4_id,
            patient_id=p4_id,
            department="Gastrointestinal Oncology Clinic",
            attending_id="dr_chen",
            started_at=now - timedelta(hours=6),
            ended_at=None,
            status="active",
            extra={"readable_id": "ENC-2026-0004"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc5_id,
            patient_id=p5_id,
            department="Hematologic Malignancies Unit",
            attending_id="dr_chen",
            started_at=now - timedelta(days=5),
            ended_at=now - timedelta(days=1),
            status="discharged",
            extra={"readable_id": "ENC-2026-0005"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc6_id,
            patient_id=p6_id,
            department="Neuro-Oncology & Stereotactic Clinic",
            attending_id="dr_chen",
            started_at=now - timedelta(hours=12),
            ended_at=None,
            status="active",
            extra={"readable_id": "ENC-2026-0006"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc7_id,
            patient_id=p7_id,
            department="Lymphoma & Stem Cell Transplant",
            attending_id="dr_chen",
            started_at=now + timedelta(days=2),
            ended_at=None,
            status="scheduled",
            extra={"readable_id": "ENC-2026-0007"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc8_id,
            patient_id=p8_id,
            department="Gynecologic Oncology Clinic",
            attending_id="dr_chen",
            started_at=now - timedelta(days=4),
            ended_at=now - timedelta(hours=2),
            status="discharged",
            extra={"readable_id": "ENC-2026-0008"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Encounters(
            id=enc9_id,
            patient_id=p9_id,
            department="Thoracic Oncology Clinic",
            attending_id="dr_chen",
            started_at=now - timedelta(hours=3),
            ended_at=None,
            status="active",
            extra={"readable_id": "ENC-2026-0009"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(encounter_records)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Medical Records (Clinical Consultations, Notes & Allergies for All 9 Patients)
    # ──────────────────────────────────────────────────────────────────────────
    med_records = [
        # Patient 1: Eleanor Vance (Kidney)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p1_id,
            kind="consultation",
            content={
                "chief_complaint": "Hematuria and left flank fullness on primary exam.",
                "history": "61yo female presenting with incidental left renal mass on initial ultrasound.",
                "assessment": "Suspicious solid renal cortical lesion, Bosniak IV equivalent. Contrast CT ordered.",
                "plan": "CT abdomen/pelvis multiphasic with contrast, renal function baseline, urology consult.",
            },
            document_uri="/clinical_records/MRN-2026-KD-001/consult_20261028.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p1_id,
            kind="allergy",
            content={
                "allergen": "Penicillin",
                "reaction": "Anaphylactoid urticaria and facial angioedema",
                "severity": "severe",
                "status": "active",
            },
            document_uri=None,
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 2: Robert Kovacs (Oral)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p2_id,
            kind="pathology",
            content={
                "chief_complaint": "Persistent lateral tongue ulceration > 6 weeks refractory to topical therapy.",
                "specimen": "Left lateral border tongue punch biopsy (4mm).",
                "diagnosis": "Moderately differentiated squamous cell carcinoma (OSCC), invasive depth 3.2mm.",
                "margins": "Deep margin pending resection. Staging CT Head/Neck indicated.",
            },
            document_uri="/clinical_records/MRN-2026-OR-002/biopsy_20261029.pdf",
            actor_id="dr_adams",
            request_id=req_id,
        ),
        # Patient 3: Maria Santos (Breast — Untrained Model Note)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p3_id,
            kind="radiology",
            content={
                "modality": "Targeted Breast Ultrasound",
                "indication": "Palpable mass upper outer quadrant left breast.",
                "findings": "Irregular hypoechoic lesion measuring 1.8 x 1.4 cm with acoustic shadowing.",
                "category": "BI-RADS 4C (High suspicion for malignancy). Core needle biopsy recommended.",
                "ai_note": "Model untrained: manual read only. AI scan contraindicated for diagnostic release.",
            },
            document_uri="/clinical_records/MRN-2026-BR-003/us_20261030.pdf",
            actor_id="dr_patel",
            request_id=req_id,
        ),
        # Patient 4: Arthur Pendleton (Colon)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p4_id,
            kind="consultation",
            content={
                "chief_complaint": "Adjuvant chemotherapy consultation following sigmoid colon resection.",
                "history": "74yo male, pT3N1bM0 adenocarcinoma of sigmoid colon. Margin negative (R0).",
                "assessment": "High-risk Stage III colon adenocarcinoma. Initiating adjuvant FOLFOX-6 protocol.",
                "plan": "Check baseline CBC, CMP, and CEA. Dispense FOLFOX components (5-FU, Leucovorin, Oxaliplatin).",
            },
            document_uri="/clinical_records/MRN-2026-GI-004/onc_consult.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p4_id,
            kind="allergy",
            content={
                "allergen": "Sulfa drugs (Sulfamethoxazole)",
                "reaction": "Maculopapular drug eruption",
                "severity": "moderate",
                "status": "active",
            },
            document_uri=None,
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 5: David Zhao (Leukemia)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p5_id,
            kind="consultation",
            content={
                "chief_complaint": "Post-induction remission assessment for B-cell Acute Lymphoblastic Leukemia.",
                "findings": "Bone marrow aspirate and peripheral smear demonstrate < 5% blasts, morphologic complete remission.",
                "assessment": "B-ALL in morphologic CR. MRD (flow cytometry) pending.",
                "plan": "Consolidation chemotherapy planning; continue outpatient surveillance.",
            },
            document_uri="/clinical_records/MRN-2026-LK-005/heme_note.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 6: Elena Rostova (Brain)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p6_id,
            kind="consultation",
            content={
                "chief_complaint": "Progressive morning headaches and new-onset focal seizures.",
                "imaging": "Brain MRI T1 post-contrast demonstrates 4.2 cm ring-enhancing mass in right temporal lobe.",
                "assessment": "High-grade intra-axial glioma (Glioblastoma vs IDH-wildtype Astrocytoma). Significant perilesional vasogenic edema.",
                "plan": "Dexamethasone initiation, Levetiracetam for seizure prophylaxis, stereotactic craniotomy for resection.",
            },
            document_uri="/clinical_records/MRN-2026-BN-006/neuro_note.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 7: Marcus Vance (Lymphoma — Refused/Abstained Case)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p7_id,
            kind="consultation",
            content={
                "chief_complaint": "Painless left supraclavicular lymphadenopathy with B-symptoms (drenching night sweats, weight loss).",
                "biopsy_status": "Prior fine-needle aspirate non-diagnostic due to crush artifact and cellular necrosis.",
                "ai_status": "REFUSED / ABSTAIN: Cellular necrosis and sample degradation prevent diagnostic inference.",
                "plan": "Excisional lymph node biopsy scheduled under local anesthesia for definitive architectural evaluation.",
            },
            document_uri="/clinical_records/MRN-2026-LY-007/lymph_note.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 8: Priya Nair (Cervical)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p8_id,
            kind="consultation",
            content={
                "chief_complaint": "Abnormal liquid-based cytology showing High-Grade Squamous Intraepithelial Lesion (HSIL).",
                "colposcopy": "Acetowhite epithelium with coarse punctation at transformation zone (squamocolumnar junction).",
                "assessment": "HSIL / Cervical Intraepithelial Neoplasia Grade 3 (CIN-3).",
                "plan": "Loop electrosurgical excision procedure (LEEP) scheduled.",
            },
            document_uri="/clinical_records/MRN-2026-CX-008/gyn_note.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        # Patient 9: Samuel Okafor (Lung)
        MedicalRecords(
            id=uuid.uuid4(),
            patient_id=p9_id,
            kind="consultation",
            content={
                "chief_complaint": "Chronic cough, mild hemoptysis, and 12-lb unintentional weight loss.",
                "imaging": "Chest CT shows 3.1 cm spiculated right upper lobe nodule with ipsilateral hilar adenopathy.",
                "pathology": "Endobronchial ultrasound (EBUS) transbronchial biopsy confirms invasive Lung Adenocarcinoma (TTF-1 positive, Napsin A positive).",
                "plan": "Brain MRI for staging, molecular testing (EGFR, ALK, PD-L1), thoracic oncology tumor board.",
            },
            document_uri="/clinical_records/MRN-2026-LG-009/pulm_note.pdf",
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(med_records)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Radiology Studies, Orders & Reports (Unique Readable IDs)
    # ──────────────────────────────────────────────────────────────────────────
    study_ct = RadiologyStudies(
        id=uuid.UUID("44444444-1001-0000-0000-000000000001"),
        modality="CT",
        body_part="Abdomen & Pelvis",
        name="CT Abdomen Triphasic Renal Mass Protocol with IV Contrast",
        actor_id=base_actor,
        request_id=req_id,
    )
    study_oral = RadiologyStudies(
        id=uuid.UUID("44444444-1002-0000-0000-000000000002"),
        modality="MRI",
        body_part="Head & Neck",
        name="MRI Head & Neck with and without IV Contrast (Oral Staging)",
        actor_id=base_actor,
        request_id=req_id,
    )
    study_us = RadiologyStudies(
        id=uuid.UUID("44444444-1003-0000-0000-000000000003"),
        modality="US",
        body_part="Breast",
        name="Diagnostic Bilateral Ultrasound Breast High-Resolution",
        actor_id=base_actor,
        request_id=req_id,
    )
    study_brain = RadiologyStudies(
        id=uuid.UUID("44444444-1004-0000-0000-000000000004"),
        modality="MRI",
        body_part="Brain",
        name="MRI Brain with and without IV Contrast (Neuro-Oncology)",
        actor_id=base_actor,
        request_id=req_id,
    )
    study_colon_ct = RadiologyStudies(
        id=uuid.UUID("44444444-1005-0000-0000-000000000005"),
        modality="CT",
        body_part="Abdomen & Pelvis",
        name="CT Abdomen/Pelvis Staging Protocol for Colorectal Carcinoma",
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add_all([study_ct, study_oral, study_us, study_brain, study_colon_ct])
    db.flush()

    ro_kidney_id = uuid.UUID("44444444-0001-0000-0000-000000000001")
    ro_oral_id = uuid.UUID("44444444-0002-0000-0000-000000000002")
    ro_breast_id = uuid.UUID("44444444-0003-0000-0000-000000000003")
    ro_colon_id = uuid.UUID("44444444-0004-0000-0000-000000000004")
    ro_brain_id = uuid.UUID("44444444-0006-0000-0000-000000000006")

    rad_orders = [
        RadiologyOrders(
            id=ro_kidney_id,
            patient_id=p1_id,
            encounter_id=enc1_id,
            study_id=study_ct.id,
            priority="routine",
            preparation="NPO 4 hours prior, verify eGFR/creatinine clearance.",
            status="reported",
            extra={"readable_id": "RAD-2026-0001"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        RadiologyOrders(
            id=ro_oral_id,
            patient_id=p2_id,
            encounter_id=enc2_id,
            study_id=study_oral.id,
            priority="routine",
            preparation="Remove dental prostheses prior to scan.",
            status="reported",
            extra={"readable_id": "RAD-2026-0002"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        RadiologyOrders(
            id=ro_breast_id,
            patient_id=p3_id,
            encounter_id=enc3_id,
            study_id=study_us.id,
            priority="urgent",
            preparation="None required.",
            status="acquired",
            extra={"readable_id": "RAD-2026-0003", "clinical_note": "Model untrained: manual read only"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        RadiologyOrders(
            id=ro_colon_id,
            patient_id=p4_id,
            encounter_id=enc4_id,
            study_id=study_colon_ct.id,
            priority="routine",
            preparation="Oral contrast administered 2 hours prior to scan.",
            status="reported",
            extra={"readable_id": "RAD-2026-0004"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        RadiologyOrders(
            id=ro_brain_id,
            patient_id=p6_id,
            encounter_id=enc6_id,
            study_id=study_brain.id,
            priority="urgent",
            preparation="Standard MR screening for ferromagnetic implants.",
            status="reported",
            extra={"readable_id": "RAD-2026-0006"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(rad_orders)
    db.flush()

    rad_reports = [
        RadiologyReports(
            id=uuid.uuid4(),
            order_id=ro_kidney_id,
            findings="Triphasic CT demonstrates a 3.6 cm heterogeneously enhancing exophytic mass arising from the interpolar cortex of the left kidney. Washout seen on nephrographic phase. No renal vein thrombus.",
            impression="Solid left renal mass consistent with Renal Cell Carcinoma (Clear Cell vs Papillary). Bosniak IV. Staged T1aN0M0. OncoSentinel AI confidence: 0.94 tumor probability.",
            image_uri="/dicom/kidney/CASE-KD-2024-5512/axial_contrast.dcm",
            dicom_metadata={"slice_thickness_mm": 1.5, "kvp": 120, "contrast_agent": "Iohexol 350"},
            diagnostic_use=True,
            signer_id="dr_patel",
            signed_at=now - timedelta(days=1),
            quality_evidence={"laplacian_variance": 218.4, "snr_db": 34.2, "validation_passed": True},
            actor_id="dr_patel",
            request_id=req_id,
        ),
        RadiologyReports(
            id=uuid.uuid4(),
            order_id=ro_oral_id,
            findings="High-resolution MRI demonstrates 2.1 x 1.4 cm T2-hyperintense, enhancing mucosal and submucosal lesion involving left lateral oral tongue. Extrinsic tongue musculature intact. Level IIa lymph node measures 1.1 cm short axis.",
            impression="Findings concordant with biopsy-proven oral squamous cell carcinoma (OSCC). Clinical T2N1 staging recommended. Multimodal tumor board review advised.",
            image_uri="/dicom/oral/CASE-OR-2024-1102/coronal_t1_post.dcm",
            dicom_metadata={"matrix": "512x512", "field_of_view_mm": 220},
            diagnostic_use=True,
            signer_id="dr_patel",
            signed_at=now - timedelta(hours=18),
            quality_evidence={"laplacian_variance": 194.8, "validation_passed": True},
            actor_id="dr_patel",
            request_id=req_id,
        ),
        RadiologyReports(
            id=uuid.uuid4(),
            order_id=ro_brain_id,
            findings="Axial T1 contrast-enhanced MRI shows 4.2 cm ring-enhancing mass centered within the right temporal lobe with surrounding vasogenic edema and 4 mm midline shift.",
            impression="Imaging features classic for high-grade glioma / glioblastoma multiforme. Urgent neurosurgical decompression and stereotactic resection indicated.",
            image_uri="/dicom/brain/CASE-BN-2024-3319/axial_t1_post.dcm",
            dicom_metadata={"modality": "MRI", "slice_thickness_mm": 1.0},
            diagnostic_use=True,
            signer_id="dr_patel",
            signed_at=now - timedelta(hours=8),
            quality_evidence={"laplacian_variance": 204.1, "snr_db": 38.0, "validation_passed": True},
            actor_id="dr_patel",
            request_id=req_id,
        ),
    ]
    db.add_all(rad_reports)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Lab Tests, Orders & Results (Unique Readable IDs & Text Histopathology)
    # ──────────────────────────────────────────────────────────────────────────
    lab_cr = LabTests(
        id=uuid.UUID("55555555-1001-0000-0000-000000000001"),
        code="LAB-CREAT",
        name="Serum Creatinine & eGFR (Renal Function Panel)",
        specimen="serum",
        unit="mg/dL",
        reference_low=Decimal("0.50"),
        reference_high=Decimal("1.20"),
        critical_low=Decimal("0.30"),
        critical_high=Decimal("4.00"),
        actor_id=base_actor,
        request_id=req_id,
    )
    lab_cbc = LabTests(
        id=uuid.UUID("55555555-1002-0000-0000-000000000002"),
        code="LAB-CBC-PLT",
        name="Platelet Count (CBC Automated)",
        specimen="whole_blood",
        unit="10*3/uL",
        reference_low=Decimal("150"),
        reference_high=Decimal("450"),
        critical_low=Decimal("50"),
        critical_high=Decimal("1000"),
        actor_id=base_actor,
        request_id=req_id,
    )
    lab_oral = LabTests(
        id=uuid.UUID("55555555-1003-0000-0000-000000000003"),
        code="LAB-HISTO-ORAL",
        name="Surgical Oral Mucosa Histopathology & Immunohistochemistry",
        specimen="tissue",
        unit="grade",
        reference_low=Decimal("0.0"),
        reference_high=Decimal("0.0"),
        critical_low=Decimal("0.0"),
        critical_high=Decimal("3.0"),
        extra={"interpretation_type": "text_grade", "reference_text": "Benign / Negative for Dysplasia"},
        actor_id=base_actor,
        request_id=req_id,
    )
    lab_cea = LabTests(
        id=uuid.UUID("55555555-1004-0000-0000-000000000004"),
        code="LAB-CEA-TUMOR",
        name="Carcinoembryonic Antigen (CEA) Tumor Marker",
        specimen="serum",
        unit="ng/mL",
        reference_low=Decimal("0.0"),
        reference_high=Decimal("3.0"),
        critical_low=Decimal("0.0"),
        critical_high=Decimal("20.0"),
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add_all([lab_cr, lab_cbc, lab_oral, lab_cea])
    db.flush()

    lo_cr_id = uuid.UUID("55555555-0001-0000-0000-000000000001")
    lo_oral_id = uuid.UUID("55555555-0002-0000-0000-000000000002")
    lo_cbc_id = uuid.UUID("55555555-0003-0000-0000-000000000003")
    lo_cea_id = uuid.UUID("55555555-0004-0000-0000-000000000004")

    lab_orders = [
        LabOrders(
            id=lo_cr_id,
            patient_id=p1_id,
            encounter_id=enc1_id,
            test_id=lab_cr.id,
            status="resulted",
            extra={"readable_id": "LAB-2026-0001"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        LabOrders(
            id=lo_oral_id,
            patient_id=p2_id,
            encounter_id=enc2_id,
            test_id=lab_oral.id,
            status="resulted",
            extra={"readable_id": "LAB-2026-0002"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        LabOrders(
            id=lo_cbc_id,
            patient_id=p3_id,
            encounter_id=enc3_id,
            test_id=lab_cbc.id,
            status="ordered",
            extra={"readable_id": "LAB-2026-0003"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
        LabOrders(
            id=lo_cea_id,
            patient_id=p4_id,
            encounter_id=enc4_id,
            test_id=lab_cea.id,
            status="resulted",
            extra={"readable_id": "LAB-2026-0004"},
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(lab_orders)
    db.flush()

    lab_results = [
        LabResults(
            id=uuid.uuid4(),
            order_id=lo_cr_id,
            value=Decimal("0.92"),
            unit="mg/dL",
            verified=True,
            flag="normal",
            verifier_id="dr_adams",
            actor_id="dr_adams",
            request_id=req_id,
        ),
        LabResults(
            id=uuid.uuid4(),
            order_id=lo_oral_id,
            value=Decimal("2.00"),
            unit="grade",
            verified=True,
            flag="abnormal",
            verifier_id="dr_adams",
            actor_id="dr_adams",
            request_id=req_id,
            extra={
                "interpretation": "Grade II Moderately Differentiated Invasive SCC",
                "histology_diagnosis": "Moderately differentiated squamous cell carcinoma with invasion into submucosa, perineural invasion negative, margins clear (>2mm).",
            },
        ),
        LabResults(
            id=uuid.uuid4(),
            order_id=lo_cea_id,
            value=Decimal("8.40"),
            unit="ng/mL",
            verified=True,
            flag="abnormal",
            verifier_id="dr_adams",
            actor_id="dr_adams",
            request_id=req_id,
            extra={"interpretation": "Elevated CEA concordant with Stage III colorectal adenocarcinoma baseline."},
        ),
    ]
    db.add_all(lab_results)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Inventory Items (FOLFOX Regimen Components + Low Stock Oxaliplatin)
    # ──────────────────────────────────────────────────────────────────────────
    inv_ondansetron = InventoryItems(
        id=uuid.UUID("66666666-0001-0000-0000-000000000001"),
        sku="SKU-PHARM-OND8",
        name="Ondansetron 8mg Film-Coated Tablets (Box 30)",
        category="Oncology Supportive Care",
        unit="box",
        par_level=150,
        reorder_point=30,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_cisplatin = InventoryItems(
        id=uuid.UUID("66666666-0002-0000-0000-000000000002"),
        sku="SKU-PHARM-CIS50",
        name="Cisplatin 50mg/50mL Sterile IV Injection Vial",
        category="Antineoplastic Chemotherapy",
        unit="vial",
        par_level=80,
        reorder_point=20,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_pembro = InventoryItems(
        id=uuid.UUID("66666666-0003-0000-0000-000000000003"),
        sku="SKU-PHARM-PEM100",
        name="Pembrolizumab 100mg/4mL Solution for Infusion",
        category="Immune Checkpoint Inhibitor",
        unit="vial",
        par_level=50,
        reorder_point=15,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_5fu = InventoryItems(
        id=uuid.UUID("66666666-0004-0000-0000-000000000004"),
        sku="SKU-PHARM-5FU500",
        name="Fluorouracil (5-FU) 500mg/10mL Solution for Infusion",
        category="FOLFOX Chemotherapy",
        unit="vial",
        par_level=120,
        reorder_point=25,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_leuco = InventoryItems(
        id=uuid.UUID("66666666-0005-0000-0000-000000000005"),
        sku="SKU-PHARM-LEU100",
        name="Leucovorin Calcium (Folinic Acid) 100mg Lyophilized Powder",
        category="FOLFOX Chemotherapy",
        unit="vial",
        par_level=90,
        reorder_point=20,
        actor_id=base_actor,
        request_id=req_id,
    )
    # Low stock item: par 40, reorder 15, current stock = 3
    inv_oxali = InventoryItems(
        id=uuid.UUID("66666666-0006-0000-0000-000000000006"),
        sku="SKU-PHARM-OXA100",
        name="Oxaliplatin 100mg/20mL Sterile IV Injection Concentrate",
        category="FOLFOX Chemotherapy",
        unit="vial",
        par_level=40,
        reorder_point=15,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_paclitaxel = InventoryItems(
        id=uuid.UUID("66666666-0007-0000-0000-000000000007"),
        sku="SKU-PHARM-PAC100",
        name="Paclitaxel 100mg/16.7mL Injection USP",
        category="Taxane Chemotherapy",
        unit="vial",
        par_level=60,
        reorder_point=15,
        actor_id=base_actor,
        request_id=req_id,
    )
    inv_carboplatin = InventoryItems(
        id=uuid.UUID("66666666-0008-0000-0000-000000000008"),
        sku="SKU-PHARM-CAR150",
        name="Carboplatin 150mg/15mL Sterile Solution",
        category="Platinum Chemotherapy",
        unit="vial",
        par_level=50,
        reorder_point=15,
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add_all([inv_ondansetron, inv_cisplatin, inv_pembro, inv_5fu, inv_leuco, inv_oxali, inv_paclitaxel, inv_carboplatin])
    db.flush()

    # Receipts & Movements
    po_oxali = InventoryPurchaseOrders(
        id=uuid.uuid4(),
        supplier="Pfizer Oncology Supply & Logistics",
        item_id=inv_oxali.id,
        quantity=30,
        reference="PO-2026-OXA-0991",
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add(po_oxali)
    db.flush()

    inv_movements = [
        # Ondansetron: +110, -30 = 80 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_ondansetron.id,
            quantity=110,
            kind="inbound",
            lot="LOT-OND-2026-09",
            expiry=date(2028, 5, 31),
            reason="Oncology supportive antiemetic batch receipt",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_ondansetron.id,
            quantity=-30,
            kind="outbound",
            lot="LOT-OND-2026-09",
            expiry=date(2028, 5, 31),
            reason="Dispensed for Patient Eleanor Vance",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Cisplatin: +64 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_cisplatin.id,
            quantity=64,
            kind="inbound",
            lot="LOT-CIS-2026-11",
            expiry=date(2028, 11, 30),
            reason="Head & neck chemoradiation Cisplatin batch receipt",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Pembrolizumab: +42 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_pembro.id,
            quantity=42,
            kind="inbound",
            lot="LOT-PEM-2026-07",
            expiry=date(2028, 9, 30),
            reason="Cold chain immunotherapy receipt",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # 5-FU: +100 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_5fu.id,
            quantity=100,
            kind="inbound",
            lot="LOT-5FU-2026-03",
            expiry=date(2028, 8, 31),
            reason="FOLFOX component central infusion supply",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Leucovorin: +80 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_leuco.id,
            quantity=80,
            kind="inbound",
            lot="LOT-LEU-2026-04",
            expiry=date(2028, 7, 31),
            reason="FOLFOX biochemical modulation supply",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Oxaliplatin: +15, -12 = 3 remaining (LOW STOCK ALERT!)
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_oxali.id,
            quantity=15,
            kind="inbound",
            lot="LOT-OXA-2026-01",
            expiry=date(2027, 12, 31),
            reason="Oxaliplatin emergency batch receipt",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_oxali.id,
            quantity=-12,
            kind="outbound",
            lot="LOT-OXA-2026-01",
            expiry=date(2027, 12, 31),
            reason="Adjuvant colon infusion preparation rounds",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Paclitaxel: +55 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_paclitaxel.id,
            quantity=55,
            kind="inbound",
            lot="LOT-PAC-2026-08",
            expiry=date(2028, 6, 30),
            reason="Chemotherapy infusion suite stock",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
        # Carboplatin: +45 remaining
        InventoryMovements(
            id=uuid.uuid4(),
            item_id=inv_carboplatin.id,
            quantity=45,
            kind="inbound",
            lot="LOT-CAR-2026-05",
            expiry=date(2028, 4, 30),
            reason="Platinum infusion suite stock",
            purchase_order_id=None,
            actor_id="pharma_alex",
            request_id=req_id,
        ),
    ]
    db.add_all(inv_movements)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Pharmacy Medications, Prescriptions & Dispenses
    # ──────────────────────────────────────────────────────────────────────────
    med_ondansetron = PharmacyMedications(
        id=uuid.UUID("77777777-0001-0000-0000-000000000001"),
        code="RX-OND-8MG",
        name="Ondansetron Hydrochloride",
        strength="8 mg",
        dosage_form="film-coated tablet",
        route="oral",
        stock_item_id=inv_ondansetron.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    med_cisplatin = PharmacyMedications(
        id=uuid.UUID("77777777-0002-0000-0000-000000000002"),
        code="RX-CIS-50MG",
        name="Cisplatin Injection USP",
        strength="50 mg / 50 mL",
        dosage_form="sterile IV concentrate",
        route="intravenous",
        stock_item_id=inv_cisplatin.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    med_pembro = PharmacyMedications(
        id=uuid.UUID("77777777-0003-0000-0000-000000000003"),
        code="RX-PEM-100MG",
        name="Pembrolizumab (Keytruda)",
        strength="100 mg / 4 mL",
        dosage_form="solution for infusion",
        route="intravenous",
        stock_item_id=inv_pembro.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    med_5fu = PharmacyMedications(
        id=uuid.UUID("77777777-0004-0000-0000-000000000004"),
        code="RX-5FU-500MG",
        name="Fluorouracil (5-FU)",
        strength="500 mg / 10 mL",
        dosage_form="IV solution",
        route="intravenous",
        stock_item_id=inv_5fu.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    med_leuco = PharmacyMedications(
        id=uuid.UUID("77777777-0005-0000-0000-000000000005"),
        code="RX-LEU-100MG",
        name="Leucovorin Calcium",
        strength="100 mg",
        dosage_form="lyophilized powder for IV",
        route="intravenous",
        stock_item_id=inv_leuco.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    med_oxali = PharmacyMedications(
        id=uuid.UUID("77777777-0006-0000-0000-000000000006"),
        code="RX-OXA-100MG",
        name="Oxaliplatin (Eloxatin)",
        strength="100 mg / 20 mL",
        dosage_form="IV concentrate",
        route="intravenous",
        stock_item_id=inv_oxali.id,
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add_all([med_ondansetron, med_cisplatin, med_pembro, med_5fu, med_leuco, med_oxali])
    db.flush()

    rx1_id = uuid.UUID("77777777-1001-0000-0000-000000000001")
    rx2_id = uuid.UUID("77777777-1002-0000-0000-000000000002")
    rx3_id = uuid.UUID("77777777-1003-0000-0000-000000000003")
    rx4_id = uuid.UUID("77777777-1004-0000-0000-000000000004")

    rx_records = [
        PharmacyPrescriptions(
            id=rx1_id,
            patient_id=p1_id,
            encounter_id=enc1_id,
            medication_id=med_ondansetron.id,
            quantity=Decimal("30"),
            directions="Take 8 mg orally twice daily 30 minutes before meals as needed for nausea.",
            refills=2,
            replaces_id=None,
            prescriber_id="dr_chen",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        PharmacyPrescriptions(
            id=rx2_id,
            patient_id=p2_id,
            encounter_id=enc2_id,
            medication_id=med_cisplatin.id,
            quantity=Decimal("4"),
            directions="Infuse 40 mg/m2 IV over 60 minutes weekly concurrent with head/neck radiotherapy.",
            refills=0,
            replaces_id=None,
            prescriber_id="dr_chen",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        PharmacyPrescriptions(
            id=rx3_id,
            patient_id=p4_id,
            encounter_id=enc4_id,
            medication_id=med_oxali.id,
            quantity=Decimal("2"),
            directions="Oxaliplatin 85 mg/m2 IV in 500 mL D5W over 2 hours on Day 1 every 2 weeks (FOLFOX).",
            refills=5,
            replaces_id=None,
            prescriber_id="dr_chen",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        PharmacyPrescriptions(
            id=rx4_id,
            patient_id=p6_id,
            encounter_id=enc6_id,
            medication_id=med_ondansetron.id,
            quantity=Decimal("20"),
            directions="Take 8 mg orally every 8 hours as needed for nausea associated with intracranial pressure.",
            refills=1,
            replaces_id=None,
            prescriber_id="dr_chen",
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(rx_records)
    db.flush()

    dispense_record = PharmacyDispense(
        id=uuid.uuid4(),
        prescription_id=rx1_id,
        quantity=Decimal("30"),
        lot="LOT-OND-2026-09",
        expiry=date(2028, 5, 31),
        pharmacist_id="pharma_alex",
        actor_id="pharma_alex",
        request_id=req_id,
    )
    db.add(dispense_record)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 9. Scheduling: Availability, Shifts, Swaps & Appointments
    # ──────────────────────────────────────────────────────────────────────────
    avail_records = [
        SchedulingAvailability(
            id=uuid.uuid4(),
            provider_id=staff_chen.id,
            start=now - timedelta(days=1),
            end=now + timedelta(days=30),
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
        SchedulingAvailability(
            id=uuid.uuid4(),
            provider_id=staff_patel.id,
            start=now - timedelta(days=1),
            end=now + timedelta(days=30),
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
        SchedulingAvailability(
            id=uuid.uuid4(),
            provider_id=staff_adams.id,
            start=now - timedelta(days=1),
            end=now + timedelta(days=30),
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
    ]
    db.add_all(avail_records)
    db.flush()

    shift1_id = uuid.UUID("88888888-0001-0000-0000-000000000001")
    shift2_id = uuid.UUID("88888888-0002-0000-0000-000000000002")
    shift_records = [
        SchedulingShifts(
            id=shift1_id,
            provider_id=staff_chen.id,
            start=now + timedelta(days=1, hours=1),
            end=now + timedelta(days=1, hours=9),
            department="Medical Oncology Day Clinic",
            status="assigned",
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
        SchedulingShifts(
            id=shift2_id,
            provider_id=staff_patel.id,
            start=now + timedelta(days=1, hours=2),
            end=now + timedelta(days=1, hours=10),
            department="Diagnostic Imaging Reading Room",
            status="assigned",
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
    ]
    db.add_all(shift_records)
    db.flush()

    swap_record = SchedulingSwaps(
        id=uuid.uuid4(),
        shift_id=shift1_id,
        replacement_id=staff_patel.id,
        reason="Coverage for multidisciplinary tumor board attendance",
        status="requested",
        actor_id="nurse_sarah",
        request_id=req_id,
    )
    db.add(swap_record)
    db.flush()

    appt_records = [
        SchedulingAppointments(
            id=uuid.uuid4(),
            patient_id=p1_id,
            provider_id=staff_chen.id,
            encounter_id=enc1_id,
            start=now + timedelta(days=1, hours=3),
            end=now + timedelta(days=1, hours=4),
            kind="Oncology Staging Follow-Up",
            status="booked",
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
        SchedulingAppointments(
            id=uuid.uuid4(),
            patient_id=p2_id,
            provider_id=staff_chen.id,
            encounter_id=enc2_id,
            start=now + timedelta(days=2, hours=2),
            end=now + timedelta(days=2, hours=3),
            kind="Surgical Biopsy Consultation",
            status="booked",
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
        SchedulingAppointments(
            id=uuid.uuid4(),
            patient_id=p4_id,
            provider_id=staff_chen.id,
            encounter_id=enc4_id,
            start=now + timedelta(days=1, hours=5),
            end=now + timedelta(days=1, hours=6),
            kind="Chemotherapy Infusion Cycle 1",
            status="booked",
            actor_id="nurse_sarah",
            request_id=req_id,
        ),
    ]
    db.add_all(appt_records)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 10. Revenue Cycle: Charge Items, Invoices, Lines, Payments, Claims & Adjustments
    # ──────────────────────────────────────────────────────────────────────────
    charge_ct = BillingChargeItems(
        id=uuid.UUID("99999999-0001-0000-0000-000000000001"),
        code="CPT-74160",
        name="CT Abdomen with IV Contrast",
        amount=Decimal("850.00"),
        coding_system="CPT-4",
        active=True,
        actor_id=base_actor,
        request_id=req_id,
    )
    charge_path = BillingChargeItems(
        id=uuid.UUID("99999999-0002-0000-0000-000000000002"),
        code="CPT-88305",
        name="Surgical Pathology Biopsy Examination (Level IV)",
        amount=Decimal("320.00"),
        coding_system="CPT-4",
        active=True,
        actor_id=base_actor,
        request_id=req_id,
    )
    charge_consult = BillingChargeItems(
        id=uuid.UUID("99999999-0003-0000-0000-000000000003"),
        code="CPT-99214",
        name="Outpatient Oncology Office Visit (Level 4)",
        amount=Decimal("240.00"),
        coding_system="CPT-4",
        active=True,
        actor_id=base_actor,
        request_id=req_id,
    )
    charge_chemo = BillingChargeItems(
        id=uuid.UUID("99999999-0004-0000-0000-000000000004"),
        code="CPT-96413",
        name="Chemotherapy Administration IV Infusion (Initial Hour)",
        amount=Decimal("450.00"),
        coding_system="CPT-4",
        active=True,
        actor_id=base_actor,
        request_id=req_id,
    )
    db.add_all([charge_ct, charge_path, charge_consult, charge_chemo])
    db.flush()

    # Invoice 1: Eleanor Vance ($1,090.00)
    inv1_id = uuid.UUID("99999999-1001-0000-0000-000000000001")
    invoice1 = BillingInvoices(
        id=inv1_id,
        patient_id=p1_id,
        lines=[
            {"code": "CPT-74160", "quantity": 1, "unit_price": "850.00", "amount": "850.00"},
            {"code": "CPT-99214", "quantity": 1, "unit_price": "240.00", "amount": "240.00"},
        ],
        due_date=date(2026, 11, 30),
        currency="USD",
        total=Decimal("1090.00"),
        number="INV-2026-10482",
        actor_id="billing_mark",
        request_id=req_id,
    )
    # Invoice 2: Arthur Pendleton ($690.00)
    inv2_id = uuid.UUID("99999999-1002-0000-0000-000000000002")
    invoice2 = BillingInvoices(
        id=inv2_id,
        patient_id=p4_id,
        lines=[
            {"code": "CPT-96413", "quantity": 1, "unit_price": "450.00", "amount": "450.00"},
            {"code": "CPT-99214", "quantity": 1, "unit_price": "240.00", "amount": "240.00"},
        ],
        due_date=date(2026, 12, 15),
        currency="USD",
        total=Decimal("690.00"),
        number="INV-2026-10483",
        actor_id="billing_mark",
        request_id=req_id,
    )
    db.add_all([invoice1, invoice2])
    db.flush()

    lines = [
        BillingInvoiceLines(
            id=uuid.uuid4(),
            invoice_id=inv1_id,
            charge_item_id=charge_ct.id,
            code="CPT-74160",
            quantity=Decimal("1"),
            unit_price=Decimal("850.00"),
            amount=Decimal("850.00"),
            actor_id="billing_mark",
            request_id=req_id,
        ),
        BillingInvoiceLines(
            id=uuid.uuid4(),
            invoice_id=inv1_id,
            charge_item_id=charge_consult.id,
            code="CPT-99214",
            quantity=Decimal("1"),
            unit_price=Decimal("240.00"),
            amount=Decimal("240.00"),
            actor_id="billing_mark",
            request_id=req_id,
        ),
        BillingInvoiceLines(
            id=uuid.uuid4(),
            invoice_id=inv2_id,
            charge_item_id=charge_chemo.id,
            code="CPT-96413",
            quantity=Decimal("1"),
            unit_price=Decimal("450.00"),
            amount=Decimal("450.00"),
            actor_id="billing_mark",
            request_id=req_id,
        ),
        BillingInvoiceLines(
            id=uuid.uuid4(),
            invoice_id=inv2_id,
            charge_item_id=charge_consult.id,
            code="CPT-99214",
            quantity=Decimal("1"),
            unit_price=Decimal("240.00"),
            amount=Decimal("240.00"),
            actor_id="billing_mark",
            request_id=req_id,
        ),
    ]
    db.add_all(lines)
    db.flush()

    payment_record = BillingPayments(
        id=uuid.uuid4(),
        invoice_id=inv1_id,
        amount=Decimal("250.00"),
        method="credit_card",
        reference="CC-TRANS-88194",
        actor_id="billing_mark",
        request_id=req_id,
    )
    payment2 = BillingPayments(
        id=uuid.uuid4(),
        invoice_id=inv2_id,
        amount=Decimal("690.00"),
        method="insurance_wire",
        reference="WIRE-UHC-99201",
        actor_id="billing_mark",
        request_id=req_id,
    )
    db.add_all([payment_record, payment2])
    db.flush()

    claim_record = BillingClaims(
        id=uuid.uuid4(),
        invoice_id=inv1_id,
        payer="Blue Cross Blue Shield of Washington",
        reference="CLM-2026-WA-0019",
        evidence_uri="/billing/claims/CLM-2026-WA-0019.837p",
        status="reviewed",
        actor_id="billing_mark",
        request_id=req_id,
    )
    db.add(claim_record)
    db.flush()

    adj_record = BillingAdjustments(
        id=uuid.uuid4(),
        invoice_id=inv1_id,
        amount=Decimal("150.00"),
        reason="Contractual allowance adjustment per BCBS fee schedule tier 1",
        reverses_id=None,
        actor_id="billing_mark",
        request_id=req_id,
    )
    db.add(adj_record)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 11. Finance: Periods & Authoritative Double-Entry Balanced Ledger (DR = CR)
    # ──────────────────────────────────────────────────────────────────────────
    period_record = FinancePeriods(
        id=uuid.uuid4(),
        period="2026-Q4",
        reason="Regular Q4-2026 Fiscal Hospital Accounting Period",
        actor_id="billing_mark",
        request_id=req_id,
    )
    db.add(period_record)
    db.flush()

    txn1_id = uuid.UUID("aaaaaaaa-0001-0000-0000-000000000001")
    txn2_id = uuid.UUID("aaaaaaaa-0002-0000-0000-000000000002")
    txn3_id = uuid.UUID("aaaaaaaa-0003-0000-0000-000000000003")

    ledger_entries = [
        # Txn 1: Invoice 1 Revenue Recognition ($1,090 DR AR, $1,090 CR Revenue)
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn1_id,
            account="1200-Accounts-Receivable",
            debit=Decimal("1090.00"),
            credit=Decimal("0.00"),
            source_id=inv1_id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn1_id,
            account="4000-Hospital-Oncology-Revenue",
            debit=Decimal("0.00"),
            credit=Decimal("1090.00"),
            source_id=inv1_id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
        # Txn 2: Payment 1 Cash Receipt ($250 DR Cash, $250 CR AR)
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn2_id,
            account="1010-Operating-Cash",
            debit=Decimal("250.00"),
            credit=Decimal("0.00"),
            source_id=payment_record.id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn2_id,
            account="1200-Accounts-Receivable",
            debit=Decimal("0.00"),
            credit=Decimal("250.00"),
            source_id=payment_record.id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
        # Txn 3: Invoice 2 Revenue Recognition ($690 DR AR, $690 CR Revenue)
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn3_id,
            account="1200-Accounts-Receivable",
            debit=Decimal("690.00"),
            credit=Decimal("0.00"),
            source_id=inv2_id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
        FinanceLedger(
            id=uuid.uuid4(),
            transaction_id=txn3_id,
            account="4000-Hospital-Oncology-Revenue",
            debit=Decimal("0.00"),
            credit=Decimal("690.00"),
            source_id=inv2_id,
            period="2026-Q4",
            reverses_id=None,
            actor_id="billing_mark",
            request_id=req_id,
        ),
    ]
    db.add_all(ledger_entries)
    db.flush()

    # ──────────────────────────────────────────────────────────────────────────
    # 12. Alerts & AI Reviews (Connecting V1 AI to Real Findings)
    # ──────────────────────────────────────────────────────────────────────────
    alert_records = [
        Alerts(
            id=uuid.uuid4(),
            kind="clinical",
            resource_id=p1_id,
            severity="high",
            message="OncoSentinel AI detection: Bosniak IV Renal Cortical Mass identified with 94.2% confidence. Nephrology consult pending.",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        Alerts(
            id=uuid.uuid4(),
            kind="safety",
            resource_id=p2_id,
            severity="medium",
            message="Confirmed oral squamous cell carcinoma staging. Multidisciplinary Tumor Board scheduled for tomorrow 08:00 AM.",
            actor_id="dr_adams",
            request_id=req_id,
        ),
        Alerts(
            id=uuid.uuid4(),
            kind="critical",
            resource_id=p4_id,
            severity="high",
            message="Critical Lab Alert: Serum CEA elevated at 8.4 ng/mL for Arthur Pendleton. Adjuvant chemotherapy cycle pending review.",
            actor_id="dr_adams",
            request_id=req_id,
        ),
        Alerts(
            id=uuid.uuid4(),
            kind="operational",
            resource_id=inv_oxali.id,
            severity="high",
            message="Low Pharmacy Stock Alert: Oxaliplatin 100mg/20mL is at 3 vials (below reorder point 15). Expedited replenishment PO-2026-OXA-0991 pending.",
            actor_id="pharma_alex",
            request_id=req_id,
        ),
    ]
    db.add_all(alert_records)
    db.flush()

    ai_reviews = [
        AiReviews(
            id=uuid.uuid4(),
            patient_id=p1_id,
            evidence_id="AI-EVID-KIDNEY-001",
            decision="concordant",
            comment="Clinician Dr. Chen confirmed concordance with MobileNetV3 renal tumor prediction. T1a mass matches surgical partial nephrectomy criteria.",
            actor_id="dr_chen",
            request_id=req_id,
        ),
        AiReviews(
            id=uuid.uuid4(),
            patient_id=p2_id,
            evidence_id="AI-EVID-ORAL-002",
            decision="concordant",
            comment="Pathologist Dr. Adams confirmed concordance with MobileNetV3 oral squamous biopsy classifier. OSCC grade II verified.",
            actor_id="dr_adams",
            request_id=req_id,
        ),
        AiReviews(
            id=uuid.uuid4(),
            patient_id=p7_id,
            evidence_id="AI-EVID-LYMPH-007",
            decision="refused",
            comment="Scan refused: Cellular necrosis and sample degradation prevent diagnostic inference. Manual repeat biopsy requested.",
            actor_id="dr_chen",
            request_id=req_id,
        ),
    ]
    db.add_all(ai_reviews)
    db.flush()

    logger.info("hms_seeding_completed_all_31_resources_populated")
