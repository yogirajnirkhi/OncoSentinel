from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.models import Base


class HMSMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    actor_id: Mapped[str] = mapped_column(String(255))
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Patients(HMSMixin, Base):
    encounters: Mapped[list[Encounters]] = relationship(back_populates="patient", lazy="raise")
    __tablename__ = "hms_patients"
    mrn: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    given_name: Mapped[str] = mapped_column(String(4000))
    family_name: Mapped[str] = mapped_column(String(4000))
    birth_date: Mapped[date] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    contact: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    insurance: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    consent: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Encounters(HMSMixin, Base):
    patient: Mapped[Patients] = relationship(back_populates="encounters", lazy="raise")
    __tablename__ = "hms_encounters"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'discharged', 'cancelled', 'scheduled')", name="ck_hms_encounters_status"
        ),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    department: Mapped[str] = mapped_column(String(4000))
    attending_id: Mapped[str] = mapped_column(String(4000))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(4000))


class MedicalRecords(HMSMixin, Base):
    __tablename__ = "hms_medical_records"
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(4000))
    content: Mapped[Any] = mapped_column(JSON)
    document_uri: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    amends_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_medical_records.id"), index=True, nullable=True
    )


class BillingChargeItems(HMSMixin, Base):
    __tablename__ = "hms_billing_charge_items"
    code: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(4000))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    coding_system: Mapped[str] = mapped_column(String(4000))
    active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class BillingInvoices(HMSMixin, Base):
    line_items: Mapped[list[BillingInvoiceLines]] = relationship(
        back_populates="invoice", lazy="raise"
    )
    __tablename__ = "hms_billing_invoices"
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    lines: Mapped[Any] = mapped_column(JSON)
    due_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(4000))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    number: Mapped[str] = mapped_column(String(4000), index=True, unique=True)


class BillingPayments(HMSMixin, Base):
    __tablename__ = "hms_billing_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_hms_billing_payments_positive"),)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_billing_invoices.id"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    method: Mapped[str] = mapped_column(String(4000))
    reference: Mapped[str] = mapped_column(String(4000))


class BillingClaims(HMSMixin, Base):
    __tablename__ = "hms_billing_claims"
    __table_args__ = (
        CheckConstraint("status IN ('reviewed')", name="ck_hms_billing_claims_status"),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_billing_invoices.id"), index=True
    )
    payer: Mapped[str] = mapped_column(String(4000))
    reference: Mapped[str] = mapped_column(String(4000))
    evidence_uri: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(4000))


class BillingAdjustments(HMSMixin, Base):
    __tablename__ = "hms_billing_adjustments"
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_billing_invoices.id"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    reason: Mapped[str] = mapped_column(String(4000))
    reverses_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_billing_adjustments.id"), index=True, nullable=True
    )


class FinanceLedger(HMSMixin, Base):
    __tablename__ = "hms_finance_ledger"
    __table_args__ = (
        CheckConstraint(
            "debit >= 0 AND credit >= 0 AND "
            "((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0))",
            name="ck_hms_ledger_one_side",
        ),
    )
    transaction_id: Mapped[UUID] = mapped_column(Uuid)
    account: Mapped[str] = mapped_column(String(4000))
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source_id: Mapped[UUID] = mapped_column(Uuid)
    period: Mapped[str] = mapped_column(String(4000), index=True)
    reverses_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_finance_ledger.id"), index=True, nullable=True
    )


class FinancePeriods(HMSMixin, Base):
    __tablename__ = "hms_finance_periods"
    period: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    reason: Mapped[str] = mapped_column(String(4000))


class PharmacyMedications(HMSMixin, Base):
    __tablename__ = "hms_pharmacy_medications"
    code: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(4000))
    strength: Mapped[str] = mapped_column(String(4000))
    dosage_form: Mapped[str] = mapped_column(String(4000))
    route: Mapped[str] = mapped_column(String(4000))
    stock_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_inventory_items.id"), index=True
    )


class PharmacyPrescriptions(HMSMixin, Base):
    dispenses: Mapped[list[PharmacyDispense]] = relationship(
        back_populates="prescription", lazy="raise"
    )
    __tablename__ = "hms_pharmacy_prescriptions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_hms_pharmacy_prescriptions_positive"),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    encounter_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_encounters.id"), index=True)
    medication_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_pharmacy_medications.id"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    directions: Mapped[str] = mapped_column(String(4000))
    refills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    replaces_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_pharmacy_prescriptions.id"), index=True, nullable=True
    )
    prescriber_id: Mapped[str] = mapped_column(String(4000))


class PharmacyDispense(HMSMixin, Base):
    prescription: Mapped[PharmacyPrescriptions] = relationship(
        back_populates="dispenses", lazy="raise"
    )
    __tablename__ = "hms_pharmacy_dispense"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_hms_pharmacy_dispense_positive"),)
    prescription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_pharmacy_prescriptions.id"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    lot: Mapped[str] = mapped_column(String(4000))
    expiry: Mapped[date] = mapped_column(Date)
    pharmacist_id: Mapped[str] = mapped_column(String(4000))


class InventoryItems(HMSMixin, Base):
    movements: Mapped[list[InventoryMovements]] = relationship(back_populates="item", lazy="raise")
    __tablename__ = "hms_inventory_items"
    sku: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(4000))
    category: Mapped[str] = mapped_column(String(4000))
    unit: Mapped[str] = mapped_column(String(4000))
    par_level: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 4))


class InventoryMovements(HMSMixin, Base):
    item: Mapped[InventoryItems] = relationship(back_populates="movements", lazy="raise")
    __tablename__ = "hms_inventory_movements"
    item_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_inventory_items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    kind: Mapped[str] = mapped_column(String(4000))
    lot: Mapped[str] = mapped_column(String(4000))
    expiry: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(4000))
    purchase_order_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_inventory_purchase_orders.id"), index=True, nullable=True
    )


class InventoryPurchaseOrders(HMSMixin, Base):
    __tablename__ = "hms_inventory_purchase_orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_hms_inventory_purchase_orders_positive"),
    )
    supplier: Mapped[str] = mapped_column(String(4000))
    item_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_inventory_items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reference: Mapped[str] = mapped_column(String(4000))


class InventoryReceipts(HMSMixin, Base):
    __tablename__ = "hms_inventory_receipts"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_hms_inventory_receipts_positive"),)
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_inventory_purchase_orders.id"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    lot: Mapped[str] = mapped_column(String(4000))
    expiry: Mapped[date] = mapped_column(Date)


class Staff(HMSMixin, Base):
    __tablename__ = "hms_staff"
    display_name: Mapped[str] = mapped_column(String(4000))
    role: Mapped[str] = mapped_column(String(4000))
    department: Mapped[str] = mapped_column(String(4000))
    credentials: Mapped[Any] = mapped_column(JSON)
    license_expiry: Mapped[date] = mapped_column(Date)
    contact: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class SchedulingAvailability(HMSMixin, Base):
    __tablename__ = "hms_scheduling_availability"
    __table_args__ = (
        CheckConstraint('start < "end"', name="ck_hms_scheduling_availability_interval"),
    )
    provider_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_staff.id"), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SchedulingShifts(HMSMixin, Base):
    __tablename__ = "hms_scheduling_shifts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('assigned', 'cancelled')", name="ck_hms_scheduling_shifts_status"
        ),
        CheckConstraint('start < "end"', name="ck_hms_scheduling_shifts_interval"),
    )
    provider_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_staff.id"), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    department: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(4000))


class SchedulingSwaps(HMSMixin, Base):
    __tablename__ = "hms_scheduling_swaps"
    __table_args__ = (
        CheckConstraint("status IN ('requested')", name="ck_hms_scheduling_swaps_status"),
    )
    shift_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_scheduling_shifts.id"), index=True)
    replacement_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_staff.id"), index=True)
    reason: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(4000))


class SchedulingAppointments(HMSMixin, Base):
    __tablename__ = "hms_scheduling_appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('booked', 'arrived', 'completed', 'cancelled')",
            name="ck_hms_scheduling_appointments_status",
        ),
        CheckConstraint('start < "end"', name="ck_hms_scheduling_appointments_interval"),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    provider_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_staff.id"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_encounters.id"), index=True, nullable=True
    )
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(4000))


class LabTests(HMSMixin, Base):
    __tablename__ = "hms_lab_tests"
    code: Mapped[str] = mapped_column(String(4000), index=True, unique=True)
    name: Mapped[str] = mapped_column(String(4000))
    specimen: Mapped[str] = mapped_column(String(4000))
    unit: Mapped[str] = mapped_column(String(4000))
    reference_low: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    reference_high: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    critical_low: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    critical_high: Mapped[Decimal] = mapped_column(Numeric(18, 4))


class LabOrders(HMSMixin, Base):
    results: Mapped[list[LabResults]] = relationship(back_populates="order", lazy="raise")
    __tablename__ = "hms_lab_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ordered', 'collected', 'resulted', 'cancelled')",
            name="ck_hms_lab_orders_status",
        ),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    encounter_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_encounters.id"), index=True)
    test_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_lab_tests.id"), index=True)
    status: Mapped[str] = mapped_column(String(4000))


class LabResults(HMSMixin, Base):
    order: Mapped[LabOrders] = relationship(back_populates="results", lazy="raise")
    __tablename__ = "hms_lab_results"
    order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_lab_orders.id"), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(4000))
    verified: Mapped[bool] = mapped_column(Boolean)
    amends_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_lab_results.id"), index=True, nullable=True
    )
    flag: Mapped[str] = mapped_column(String(4000))
    verifier_id: Mapped[str] = mapped_column(String(4000))


class RadiologyStudies(HMSMixin, Base):
    __tablename__ = "hms_radiology_studies"
    modality: Mapped[str] = mapped_column(String(4000))
    body_part: Mapped[str] = mapped_column(String(4000))
    name: Mapped[str] = mapped_column(String(4000))


class RadiologyOrders(HMSMixin, Base):
    reports: Mapped[list[RadiologyReports]] = relationship(back_populates="order", lazy="raise")
    __tablename__ = "hms_radiology_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ordered', 'scheduled', 'acquired', 'reported', 'cancelled')",
            name="ck_hms_radiology_orders_status",
        ),
    )
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    encounter_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_encounters.id"), index=True)
    study_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_radiology_studies.id"), index=True)
    priority: Mapped[str] = mapped_column(String(4000))
    preparation: Mapped[str] = mapped_column(String(4000))
    status: Mapped[str] = mapped_column(String(4000))


class RadiologyReports(HMSMixin, Base):
    order: Mapped[RadiologyOrders] = relationship(back_populates="reports", lazy="raise")
    __tablename__ = "hms_radiology_reports"
    order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_radiology_orders.id"), index=True)
    findings: Mapped[str] = mapped_column(String(4000))
    impression: Mapped[str] = mapped_column(String(4000))
    image_uri: Mapped[str] = mapped_column(String(4000))
    dicom_metadata: Mapped[Any] = mapped_column(JSON)
    diagnostic_use: Mapped[bool] = mapped_column(Boolean)
    amends_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hms_radiology_reports.id"), index=True, nullable=True
    )
    signer_id: Mapped[str] = mapped_column(String(4000))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quality_evidence: Mapped[Any] = mapped_column(JSON)


class Alerts(HMSMixin, Base):
    __tablename__ = "hms_alerts"
    kind: Mapped[str] = mapped_column(String(4000))
    resource_id: Mapped[UUID] = mapped_column(Uuid)
    severity: Mapped[str] = mapped_column(String(4000))
    message: Mapped[str] = mapped_column(String(4000))


class AiReviews(HMSMixin, Base):
    __tablename__ = "hms_ai_reviews"
    patient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("hms_patients.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(String(4000))
    decision: Mapped[str] = mapped_column(String(4000))
    comment: Mapped[str] = mapped_column(String(4000))


class BillingInvoiceLines(HMSMixin, Base):
    invoice: Mapped[BillingInvoices] = relationship(back_populates="line_items", lazy="raise")
    __tablename__ = "hms_billing_invoice_lines"
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_billing_invoices.id"), index=True
    )
    charge_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hms_billing_charge_items.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(4000), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class OperationReceipt(Base):
    __tablename__ = "hms_operation_receipts"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


MODELS: dict[str, type[Any]] = {
    "patients": Patients,
    "encounters": Encounters,
    "medical-records": MedicalRecords,
    "billing/charge-items": BillingChargeItems,
    "billing/invoices": BillingInvoices,
    "billing/payments": BillingPayments,
    "billing/claims": BillingClaims,
    "billing/adjustments": BillingAdjustments,
    "finance/ledger": FinanceLedger,
    "finance/periods": FinancePeriods,
    "pharmacy/medications": PharmacyMedications,
    "pharmacy/prescriptions": PharmacyPrescriptions,
    "pharmacy/dispense": PharmacyDispense,
    "inventory/items": InventoryItems,
    "inventory/movements": InventoryMovements,
    "inventory/purchase-orders": InventoryPurchaseOrders,
    "inventory/receipts": InventoryReceipts,
    "staff": Staff,
    "scheduling/availability": SchedulingAvailability,
    "scheduling/shifts": SchedulingShifts,
    "scheduling/swaps": SchedulingSwaps,
    "scheduling/appointments": SchedulingAppointments,
    "lab/tests": LabTests,
    "lab/orders": LabOrders,
    "lab/results": LabResults,
    "radiology/studies": RadiologyStudies,
    "radiology/orders": RadiologyOrders,
    "radiology/reports": RadiologyReports,
    "alerts": Alerts,
    "ai/reviews": AiReviews,
    "billing/invoice-lines": BillingInvoiceLines,
}
IMMUTABLE = (
    MedicalRecords,
    BillingInvoices,
    BillingPayments,
    BillingClaims,
    BillingAdjustments,
    FinanceLedger,
    FinancePeriods,
    PharmacyPrescriptions,
    PharmacyDispense,
    InventoryMovements,
    InventoryPurchaseOrders,
    InventoryReceipts,
    SchedulingSwaps,
    LabResults,
    RadiologyReports,
    Alerts,
    AiReviews,
    BillingInvoiceLines,
    OperationReceipt,
)


def deny_change(mapper: Any, connection: Any, target: Any) -> None:
    raise ValueError("Append-only record: create an amendment or reversal instead")


for immutable_model in IMMUTABLE:
    event.listen(immutable_model, "before_update", deny_change)
    event.listen(immutable_model, "before_delete", deny_change)
