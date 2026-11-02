from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    actor_id: str
    request_id: str
    version: int
    extra: dict[str, Any]


class Query(RequestModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)
    filters: dict[str, str] = Field(default_factory=dict)


class Page(BaseModel):
    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


class PatientsCreate(RequestModel):
    mrn: str = Field(min_length=1, max_length=4000)
    given_name: str = Field(min_length=1, max_length=4000)
    family_name: str = Field(min_length=1, max_length=4000)
    birth_date: date = Field(description="Birth date")
    gender: str | None = Field(default=None, min_length=1, max_length=4000)
    contact: Any | None = Field(default=None)
    insurance: Any | None = Field(default=None)
    consent: Any | None = Field(default=None)


class PatientsResponse(RecordResponse, PatientsCreate):
    pass


class PatientsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    mrn: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    contact: Any | None = None
    insurance: Any | None = None
    consent: Any | None = None


class EncountersCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    department: str = Field(min_length=1, max_length=4000)
    attending_id: str = Field(min_length=1, max_length=4000)
    started_at: AwareDatetime = Field(description="Started at")
    ended_at: AwareDatetime | None = Field(default=None)
    status: str = Field(default="active", min_length=1, max_length=4000)


class EncountersResponse(RecordResponse, EncountersCreate):
    pass


class EncountersUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    patient_id: UUID | None = None
    department: str | None = None
    attending_id: str | None = None
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    status: str | None = None


class MedicalRecordsCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    kind: str = Field(min_length=1, max_length=4000)
    content: Any = Field(description="Content")
    document_uri: str | None = Field(default=None, min_length=1, max_length=4000)
    amends_id: UUID | None = Field(default=None)


class MedicalRecordsResponse(RecordResponse, MedicalRecordsCreate):
    pass


class BillingChargeItemsCreate(RequestModel):
    code: str = Field(min_length=1, max_length=4000)
    name: str = Field(min_length=1, max_length=4000)
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    coding_system: str = Field(min_length=1, max_length=4000)
    active: bool | None = Field(default=True)


class BillingChargeItemsResponse(RecordResponse, BillingChargeItemsCreate):
    pass


class BillingChargeItemsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    code: str | None = None
    name: str | None = None
    amount: Decimal | None = None
    coding_system: str | None = None
    active: bool | None = None


class BillingInvoicesCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    lines: Any = Field(description="Lines")
    due_date: date = Field(description="Due date")
    currency: str = Field(default="INR", min_length=1, max_length=4000)


class BillingInvoicesResponse(RecordResponse, BillingInvoicesCreate):
    total: Decimal
    number: str


class BillingPaymentsCreate(RequestModel):
    invoice_id: UUID = Field(description="Invoice id")
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    method: str = Field(min_length=1, max_length=4000)
    reference: str = Field(min_length=1, max_length=4000)


class BillingPaymentsResponse(RecordResponse, BillingPaymentsCreate):
    pass


class BillingClaimsCreate(RequestModel):
    invoice_id: UUID = Field(description="Invoice id")
    payer: str = Field(min_length=1, max_length=4000)
    reference: str = Field(min_length=1, max_length=4000)
    evidence_uri: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="reviewed", min_length=1, max_length=4000)


class BillingClaimsResponse(RecordResponse, BillingClaimsCreate):
    pass


class BillingAdjustmentsCreate(RequestModel):
    invoice_id: UUID = Field(description="Invoice id")
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    reason: str = Field(min_length=1, max_length=4000)
    reverses_id: UUID | None = Field(default=None)


class BillingAdjustmentsResponse(RecordResponse, BillingAdjustmentsCreate):
    pass


class FinanceLedgerCreate(RequestModel):
    transaction_id: UUID = Field(description="Transaction id")
    account: str = Field(min_length=1, max_length=4000)
    debit: Decimal = Field(max_digits=18, decimal_places=2)
    credit: Decimal = Field(max_digits=18, decimal_places=2)
    source_id: UUID = Field(description="Source id")
    period: str = Field(min_length=1, max_length=4000)
    reverses_id: UUID | None = Field(default=None)


class FinanceLedgerResponse(RecordResponse, FinanceLedgerCreate):
    pass


class FinancePeriodsCreate(RequestModel):
    period: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=1, max_length=4000)


class FinancePeriodsResponse(RecordResponse, FinancePeriodsCreate):
    pass


class PharmacyMedicationsCreate(RequestModel):
    code: str = Field(min_length=1, max_length=4000)
    name: str = Field(min_length=1, max_length=4000)
    strength: str = Field(min_length=1, max_length=4000)
    dosage_form: str = Field(min_length=1, max_length=4000)
    route: str = Field(min_length=1, max_length=4000)
    stock_item_id: UUID = Field(description="Stock item id")


class PharmacyMedicationsResponse(RecordResponse, PharmacyMedicationsCreate):
    pass


class PharmacyMedicationsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    code: str | None = None
    name: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    route: str | None = None
    stock_item_id: UUID | None = None


class PharmacyPrescriptionsCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    encounter_id: UUID = Field(description="Encounter id")
    medication_id: UUID = Field(description="Medication id")
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    directions: str = Field(min_length=1, max_length=4000)
    refills: int | None = Field(default=0)
    replaces_id: UUID | None = Field(default=None)


class PharmacyPrescriptionsResponse(RecordResponse, PharmacyPrescriptionsCreate):
    prescriber_id: str


class PharmacyDispenseCreate(RequestModel):
    prescription_id: UUID = Field(description="Prescription id")
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    lot: str = Field(min_length=1, max_length=4000)
    expiry: date = Field(description="Expiry")


class PharmacyDispenseResponse(RecordResponse, PharmacyDispenseCreate):
    pharmacist_id: str


class InventoryItemsCreate(RequestModel):
    sku: str = Field(min_length=1, max_length=4000)
    name: str = Field(min_length=1, max_length=4000)
    category: str = Field(min_length=1, max_length=4000)
    unit: str = Field(min_length=1, max_length=4000)
    par_level: Decimal = Field(max_digits=18, decimal_places=4)
    reorder_point: Decimal = Field(max_digits=18, decimal_places=4)


class InventoryItemsResponse(RecordResponse, InventoryItemsCreate):
    pass


class InventoryItemsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    sku: str | None = None
    name: str | None = None
    category: str | None = None
    unit: str | None = None
    par_level: Decimal | None = None
    reorder_point: Decimal | None = None


class InventoryMovementsCreate(RequestModel):
    item_id: UUID = Field(description="Item id")
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    kind: str = Field(min_length=1, max_length=4000)
    lot: str = Field(min_length=1, max_length=4000)
    expiry: date = Field(description="Expiry")
    reason: str = Field(min_length=1, max_length=4000)
    purchase_order_id: UUID | None = Field(default=None)


class InventoryMovementsResponse(RecordResponse, InventoryMovementsCreate):
    pass


class InventoryPurchaseOrdersCreate(RequestModel):
    supplier: str = Field(min_length=1, max_length=4000)
    item_id: UUID = Field(description="Item id")
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    reference: str = Field(min_length=1, max_length=4000)


class InventoryPurchaseOrdersResponse(RecordResponse, InventoryPurchaseOrdersCreate):
    pass


class InventoryReceiptsCreate(RequestModel):
    purchase_order_id: UUID = Field(description="Purchase order id")
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    lot: str = Field(min_length=1, max_length=4000)
    expiry: date = Field(description="Expiry")


class InventoryReceiptsResponse(RecordResponse, InventoryReceiptsCreate):
    pass


class StaffCreate(RequestModel):
    display_name: str = Field(min_length=1, max_length=4000)
    role: str = Field(min_length=1, max_length=4000)
    department: str = Field(min_length=1, max_length=4000)
    credentials: Any = Field(description="Credentials")
    license_expiry: date = Field(description="License expiry")
    contact: Any | None = Field(default=None)


class StaffResponse(RecordResponse, StaffCreate):
    pass


class StaffUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    display_name: str | None = None
    role: str | None = None
    department: str | None = None
    credentials: Any | None = None
    license_expiry: date | None = None
    contact: Any | None = None


class SchedulingAvailabilityCreate(RequestModel):
    provider_id: UUID = Field(description="Provider id")
    start: AwareDatetime = Field(description="Start")
    end: AwareDatetime = Field(description="End")


class SchedulingAvailabilityResponse(RecordResponse, SchedulingAvailabilityCreate):
    pass


class SchedulingAvailabilityUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    provider_id: UUID | None = None
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None


class SchedulingShiftsCreate(RequestModel):
    provider_id: UUID = Field(description="Provider id")
    start: AwareDatetime = Field(description="Start")
    end: AwareDatetime = Field(description="End")
    department: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="assigned", min_length=1, max_length=4000)


class SchedulingShiftsResponse(RecordResponse, SchedulingShiftsCreate):
    pass


class SchedulingShiftsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    provider_id: UUID | None = None
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    department: str | None = None
    status: str | None = None


class SchedulingSwapsCreate(RequestModel):
    shift_id: UUID = Field(description="Shift id")
    replacement_id: UUID = Field(description="Replacement id")
    reason: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="requested", min_length=1, max_length=4000)


class SchedulingSwapsResponse(RecordResponse, SchedulingSwapsCreate):
    pass


class SchedulingAppointmentsCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    provider_id: UUID = Field(description="Provider id")
    encounter_id: UUID | None = Field(default=None)
    start: AwareDatetime = Field(description="Start")
    end: AwareDatetime = Field(description="End")
    kind: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="booked", min_length=1, max_length=4000)


class SchedulingAppointmentsResponse(RecordResponse, SchedulingAppointmentsCreate):
    pass


class SchedulingAppointmentsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    patient_id: UUID | None = None
    provider_id: UUID | None = None
    encounter_id: UUID | None = None
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    kind: str | None = None
    status: str | None = None


class LabTestsCreate(RequestModel):
    code: str = Field(min_length=1, max_length=4000)
    name: str = Field(min_length=1, max_length=4000)
    specimen: str = Field(min_length=1, max_length=4000)
    unit: str = Field(min_length=1, max_length=4000)
    reference_low: Decimal = Field(max_digits=18, decimal_places=4)
    reference_high: Decimal = Field(max_digits=18, decimal_places=4)
    critical_low: Decimal = Field(max_digits=18, decimal_places=4)
    critical_high: Decimal = Field(max_digits=18, decimal_places=4)


class LabTestsResponse(RecordResponse, LabTestsCreate):
    pass


class LabTestsUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    code: str | None = None
    name: str | None = None
    specimen: str | None = None
    unit: str | None = None
    reference_low: Decimal | None = None
    reference_high: Decimal | None = None
    critical_low: Decimal | None = None
    critical_high: Decimal | None = None


class LabOrdersCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    encounter_id: UUID = Field(description="Encounter id")
    test_id: UUID = Field(description="Test id")
    status: str = Field(default="ordered", min_length=1, max_length=4000)


class LabOrdersResponse(RecordResponse, LabOrdersCreate):
    pass


class LabOrdersUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    test_id: UUID | None = None
    status: str | None = None


class LabResultsCreate(RequestModel):
    order_id: UUID = Field(description="Order id")
    value: Decimal = Field(max_digits=18, decimal_places=4)
    unit: str = Field(min_length=1, max_length=4000)
    verified: bool = Field(description="Verified")
    amends_id: UUID | None = Field(default=None)


class LabResultsResponse(RecordResponse, LabResultsCreate):
    flag: str
    verifier_id: str


class RadiologyStudiesCreate(RequestModel):
    modality: str = Field(min_length=1, max_length=4000)
    body_part: str = Field(min_length=1, max_length=4000)
    name: str = Field(min_length=1, max_length=4000)


class RadiologyStudiesResponse(RecordResponse, RadiologyStudiesCreate):
    pass


class RadiologyStudiesUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    modality: str | None = None
    body_part: str | None = None
    name: str | None = None


class RadiologyOrdersCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    encounter_id: UUID = Field(description="Encounter id")
    study_id: UUID = Field(description="Study id")
    priority: str = Field(min_length=1, max_length=4000)
    preparation: str = Field(min_length=1, max_length=4000)
    status: str = Field(default="ordered", min_length=1, max_length=4000)


class RadiologyOrdersResponse(RecordResponse, RadiologyOrdersCreate):
    pass


class RadiologyOrdersUpdate(RequestModel):
    expected_version: int = Field(ge=1)
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    study_id: UUID | None = None
    priority: str | None = None
    preparation: str | None = None
    status: str | None = None


class RadiologyReportsCreate(RequestModel):
    order_id: UUID = Field(description="Order id")
    findings: str = Field(min_length=1, max_length=4000)
    impression: str = Field(min_length=1, max_length=4000)
    image_uri: str = Field(min_length=1, max_length=4000)
    dicom_metadata: Any = Field(description="Dicom metadata")
    diagnostic_use: bool = Field(description="Diagnostic use")
    amends_id: UUID | None = Field(default=None)


class RadiologyReportsResponse(RecordResponse, RadiologyReportsCreate):
    signer_id: str
    signed_at: datetime
    quality_evidence: Any


class AlertsCreate(RequestModel):
    kind: str = Field(min_length=1, max_length=4000)
    resource_id: UUID = Field(description="Resource id")
    severity: str = Field(min_length=1, max_length=4000)
    message: str = Field(min_length=1, max_length=4000)


class AlertsResponse(RecordResponse, AlertsCreate):
    pass


class AiReviewsCreate(RequestModel):
    patient_id: UUID = Field(description="Patient id")
    evidence_id: str = Field(min_length=1, max_length=4000)
    decision: str = Field(min_length=1, max_length=4000)
    comment: str = Field(min_length=1, max_length=4000)


class AiReviewsResponse(RecordResponse, AiReviewsCreate):
    pass


class BillingInvoiceLinesCreate(RequestModel):
    invoice_id: UUID = Field(description="Invoice id")
    charge_item_id: UUID = Field(description="Charge item id")
    code: str = Field(min_length=1, max_length=4000)
    quantity: Decimal = Field(max_digits=18, decimal_places=4)
    unit_price: Decimal = Field(max_digits=18, decimal_places=2)
    amount: Decimal = Field(max_digits=18, decimal_places=2)


class BillingInvoiceLinesResponse(RecordResponse, BillingInvoiceLinesCreate):
    pass


CREATES: dict[str, type[BaseModel]] = {
    "patients": PatientsCreate,
    "encounters": EncountersCreate,
    "medical-records": MedicalRecordsCreate,
    "billing/charge-items": BillingChargeItemsCreate,
    "billing/invoices": BillingInvoicesCreate,
    "billing/payments": BillingPaymentsCreate,
    "billing/claims": BillingClaimsCreate,
    "billing/adjustments": BillingAdjustmentsCreate,
    "finance/ledger": FinanceLedgerCreate,
    "finance/periods": FinancePeriodsCreate,
    "pharmacy/medications": PharmacyMedicationsCreate,
    "pharmacy/prescriptions": PharmacyPrescriptionsCreate,
    "pharmacy/dispense": PharmacyDispenseCreate,
    "inventory/items": InventoryItemsCreate,
    "inventory/movements": InventoryMovementsCreate,
    "inventory/purchase-orders": InventoryPurchaseOrdersCreate,
    "inventory/receipts": InventoryReceiptsCreate,
    "staff": StaffCreate,
    "scheduling/availability": SchedulingAvailabilityCreate,
    "scheduling/shifts": SchedulingShiftsCreate,
    "scheduling/swaps": SchedulingSwapsCreate,
    "scheduling/appointments": SchedulingAppointmentsCreate,
    "lab/tests": LabTestsCreate,
    "lab/orders": LabOrdersCreate,
    "lab/results": LabResultsCreate,
    "radiology/studies": RadiologyStudiesCreate,
    "radiology/orders": RadiologyOrdersCreate,
    "radiology/reports": RadiologyReportsCreate,
    "alerts": AlertsCreate,
    "ai/reviews": AiReviewsCreate,
    "billing/invoice-lines": BillingInvoiceLinesCreate,
}
RESPONSES: dict[str, type[BaseModel]] = {
    "patients": PatientsResponse,
    "encounters": EncountersResponse,
    "medical-records": MedicalRecordsResponse,
    "billing/charge-items": BillingChargeItemsResponse,
    "billing/invoices": BillingInvoicesResponse,
    "billing/payments": BillingPaymentsResponse,
    "billing/claims": BillingClaimsResponse,
    "billing/adjustments": BillingAdjustmentsResponse,
    "finance/ledger": FinanceLedgerResponse,
    "finance/periods": FinancePeriodsResponse,
    "pharmacy/medications": PharmacyMedicationsResponse,
    "pharmacy/prescriptions": PharmacyPrescriptionsResponse,
    "pharmacy/dispense": PharmacyDispenseResponse,
    "inventory/items": InventoryItemsResponse,
    "inventory/movements": InventoryMovementsResponse,
    "inventory/purchase-orders": InventoryPurchaseOrdersResponse,
    "inventory/receipts": InventoryReceiptsResponse,
    "staff": StaffResponse,
    "scheduling/availability": SchedulingAvailabilityResponse,
    "scheduling/shifts": SchedulingShiftsResponse,
    "scheduling/swaps": SchedulingSwapsResponse,
    "scheduling/appointments": SchedulingAppointmentsResponse,
    "lab/tests": LabTestsResponse,
    "lab/orders": LabOrdersResponse,
    "lab/results": LabResultsResponse,
    "radiology/studies": RadiologyStudiesResponse,
    "radiology/orders": RadiologyOrdersResponse,
    "radiology/reports": RadiologyReportsResponse,
    "alerts": AlertsResponse,
    "ai/reviews": AiReviewsResponse,
    "billing/invoice-lines": BillingInvoiceLinesResponse,
}
UPDATES: dict[str, type[BaseModel]] = {
    "patients": PatientsUpdate,
    "encounters": EncountersUpdate,
    "billing/charge-items": BillingChargeItemsUpdate,
    "pharmacy/medications": PharmacyMedicationsUpdate,
    "inventory/items": InventoryItemsUpdate,
    "staff": StaffUpdate,
    "scheduling/availability": SchedulingAvailabilityUpdate,
    "scheduling/shifts": SchedulingShiftsUpdate,
    "scheduling/appointments": SchedulingAppointmentsUpdate,
    "lab/tests": LabTestsUpdate,
    "lab/orders": LabOrdersUpdate,
    "radiology/studies": RadiologyStudiesUpdate,
    "radiology/orders": RadiologyOrdersUpdate,
}
