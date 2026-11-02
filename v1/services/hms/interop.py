from __future__ import annotations

from typing import Any

from services.hms.exceptions import HMSError

# R4 projections, not a substitute for full terminology/profile validation at the host boundary.
MRN_SYSTEM = "urn:oncosentinel:mrn"
FHIR_TYPES = {
    "Patient",
    "Encounter",
    "Medication",
    "MedicationRequest",
    "ServiceRequest",
    "DiagnosticReport",
    "Observation",
    "Bundle",
    "Appointment",
    "Schedule",
    "Slot",
}


def patient_to_fhir(data: dict[str, Any]) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(data["id"]),
        "identifier": [{"system": MRN_SYSTEM, "value": data["mrn"]}],
        "name": [{"use": "official", "family": data["family_name"], "given": [data["given_name"]]}],
        "birthDate": str(data["birth_date"]),
    }
    if data.get("gender") in ["male", "female", "other", "unknown"]:
        resource["gender"] = data["gender"]
    if isinstance(data.get("contact"), dict):
        resource["telecom"] = [
            {"system": k, "value": v}
            for k, v in data["contact"].items()
            if k in ["phone", "email"] and isinstance(v, str)
        ]
    return resource


def patient_from_fhir(resource: dict[str, Any]) -> dict[str, Any]:
    if resource.get("resourceType") != "Patient":
        raise HMSError("Expected a FHIR R4 Patient")
    identifiers = [
        r.get("value") for r in resource.get("identifier", []) if r.get("system") == MRN_SYSTEM
    ]
    names = resource.get("name", [])
    if (
        not identifiers
        or not names
        or not names[0].get("family")
        or not names[0].get("given")
        or not resource.get("birthDate")
    ):
        raise HMSError(
            "FHIR Patient requires the configured MRN, given/family name and full birthDate"
        )
    return {
        "mrn": identifiers[0],
        "given_name": names[0]["given"][0],
        "family_name": names[0]["family"],
        "birth_date": resource["birthDate"],
        "gender": resource.get("gender"),
        "contact": {
            v["system"]: v["value"]
            for v in resource.get("telecom", [])
            if v.get("system") in ["phone", "email"] and v.get("value")
        },
        "insurance": None,
        "consent": None,
    }


def reference(kind: str, identifier: Any) -> dict[str, str]:
    return {"reference": kind + "/" + str(identifier)}


def to_fhir(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    if kind not in FHIR_TYPES:
        raise HMSError("Unsupported FHIR resource")
    if kind == "Patient":
        return patient_to_fhir(data)
    if kind == "Bundle":
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": r} for r in data["resources"]],
        }
    r: dict[str, Any] = {"resourceType": kind, "id": str(data["id"])}
    if kind == "Encounter":
        r.update(
            status={"active": "in-progress", "discharged": "finished", "cancelled": "cancelled"}[
                data["status"]
            ],
            **{
                "class": {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "AMB",
                }
            },
            subject=reference("Patient", data["patient_id"]),
            period={"start": str(data["started_at"])},
        )
        if data.get("ended_at"):
            r["period"]["end"] = str(data["ended_at"])
    elif kind == "Medication":
        r.update(
            code={
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/ndc",
                        "code": data["code"],
                        "display": data["name"],
                    }
                ]
            },
            form={"text": data["dosage_form"]},
        )
    elif kind == "MedicationRequest":
        r.update(
            status="active",
            intent="order",
            subject=reference("Patient", data["patient_id"]),
            medicationReference=reference("Medication", data["medication_id"]),
            encounter=reference("Encounter", data["encounter_id"]),
            dosageInstruction=[{"text": data["directions"]}],
            dispenseRequest={
                "quantity": {"value": float(data["quantity"])},
                "numberOfRepeatsAllowed": data.get("refills") or 0,
            },
        )
    elif kind == "ServiceRequest":
        r.update(
            status="active" if data.get("status") != "cancelled" else "revoked",
            intent="order",
            subject=reference("Patient", data["patient_id"]),
            encounter=reference("Encounter", data["encounter_id"]),
            code={"text": str(data.get("test_id") or data.get("study_id"))},
        )
    elif kind == "Observation":
        # Caller supplies patient/code; a LabResult alone is not enough to form a valid Observation.
        if not data.get("patient_id") or not data.get("code"):
            raise HMSError("Observation projection requires patient and LOINC code")
        r.update(
            status="amended" if data.get("amends_id") else "final",
            subject=reference("Patient", data["patient_id"]),
            code={"coding": [{"system": "http://loinc.org", "code": data["code"]}]},
            valueQuantity={"value": float(data["value"]), "unit": data["unit"]},
        )
    elif kind == "DiagnosticReport":
        if not data.get("patient_id") or not data.get("code"):
            raise HMSError("DiagnosticReport requires patient and report code")
        r.update(
            status="amended" if data.get("amends_id") else "final",
            subject=reference("Patient", data["patient_id"]),
            code={"text": data["code"]},
            conclusion=data.get("impression", ""),
            result=[reference("Observation", i) for i in data.get("result_ids", [])],
        )
    elif kind == "Appointment":
        r.update(
            status={
                "booked": "booked",
                "arrived": "arrived",
                "completed": "fulfilled",
                "cancelled": "cancelled",
            }[data["status"]],
            start=str(data["start"]),
            end=str(data["end"]),
            participant=[
                {"actor": reference("Patient", data["patient_id"]), "status": "accepted"},
                {"actor": reference("Practitioner", data["provider_id"]), "status": "accepted"},
            ],
        )
    elif kind == "Schedule":
        r.update(
            active=True,
            actor=[reference("Practitioner", data["provider_id"])],
            planningHorizon={"start": str(data["start"]), "end": str(data["end"])},
        )
    elif kind == "Slot":
        if not data.get("schedule_id"):
            raise HMSError("Slot requires a Schedule reference")
        r.update(
            schedule=reference("Schedule", data["schedule_id"]),
            status="free",
            start=str(data["start"]),
            end=str(data["end"]),
        )
    return r


def from_fhir(resource: dict[str, Any]) -> dict[str, Any]:
    """Explicit normalized projections. Persist through validated domain "
    "services, not bulk inserts."""
    kind = resource.get("resourceType")
    if kind not in FHIR_TYPES:
        raise HMSError("Unsupported FHIR resource")
    if kind == "Patient":
        return patient_from_fhir(resource)
    if kind == "Bundle":
        return {
            "resources": [
                from_fhir(e["resource"]) for e in resource.get("entry", []) if "resource" in e
            ]
        }

    def ident(value: dict[str, Any]) -> str:
        result = value.get("reference", "").split("/")[-1]
        if not result:
            raise HMSError("Missing FHIR reference")
        return str(result)

    out: dict[str, Any] = {"id": resource.get("id")}
    if kind == "Encounter":
        statuses = {"in-progress": "active", "finished": "discharged", "cancelled": "cancelled"}
        if resource.get("status") not in statuses:
            raise HMSError("FHIR encounter state cannot be represented without loss")
        out.update(
            patient_id=ident(resource["subject"]),
            status=statuses[resource["status"]],
            started_at=resource["period"]["start"],
            ended_at=resource["period"].get("end"),
        )
    elif kind == "Medication":
        coding = resource["code"]["coding"][0]
        out.update(
            code=coding["code"],
            name=coding.get("display"),
            dosage_form=resource.get("form", {}).get("text"),
        )
    elif kind == "MedicationRequest":
        out.update(
            patient_id=ident(resource["subject"]),
            medication_id=ident(resource["medicationReference"]),
            encounter_id=ident(resource["encounter"]),
            directions=resource["dosageInstruction"][0]["text"],
            quantity=resource["dispenseRequest"]["quantity"]["value"],
            refills=resource["dispenseRequest"].get("numberOfRepeatsAllowed", 0),
        )
    elif kind == "ServiceRequest":
        out.update(
            patient_id=ident(resource["subject"]),
            encounter_id=ident(resource["encounter"]),
            catalogue_id=resource["code"]["text"],
        )
    elif kind == "Observation":
        out.update(
            patient_id=ident(resource["subject"]),
            code=resource["code"]["coding"][0]["code"],
            value=resource["valueQuantity"]["value"],
            unit=resource["valueQuantity"].get("unit"),
        )
    elif kind == "DiagnosticReport":
        out.update(
            patient_id=ident(resource["subject"]),
            code=resource["code"].get("text"),
            impression=resource.get("conclusion"),
            result_ids=[ident(i) for i in resource.get("result", [])],
        )
    elif kind == "Appointment":
        states = {
            "booked": "booked",
            "arrived": "arrived",
            "fulfilled": "completed",
            "cancelled": "cancelled",
        }
        if resource.get("status") not in states:
            raise HMSError("Unsupported appointment status")
        out.update(start=resource["start"], end=resource["end"], status=states[resource["status"]])
        for participant in resource["participant"]:
            ref = participant["actor"]["reference"]
            if ref.startswith("Patient/"):
                out["patient_id"] = ident(participant["actor"])
            if ref.startswith("Practitioner/"):
                out["provider_id"] = ident(participant["actor"])
    elif kind == "Schedule":
        out.update(
            provider_id=ident(resource["actor"][0]),
            start=resource["planningHorizon"]["start"],
            end=resource["planningHorizon"]["end"],
        )
    elif kind == "Slot":
        out.update(
            schedule_id=ident(resource["schedule"]), start=resource["start"], end=resource["end"]
        )
    return out
