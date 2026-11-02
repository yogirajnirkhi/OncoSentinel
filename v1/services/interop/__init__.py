"""
OncoSentinel v2.0 — Interoperability Layer (HL7 FHIR & Hospital Adapters)
Satisfies: NFR-13 (Interoperability: PACS/RIS/LIS/FHIR/HL7 integration)
"""
from services.interop.fhir_adapter import FHIRAdapter, get_fhir_adapter

__all__ = ["FHIRAdapter", "get_fhir_adapter"]
