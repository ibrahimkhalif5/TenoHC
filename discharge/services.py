"""
Service layer for the discharge summary module.
"""
from datetime import date
from django.db import transaction
from django.utils import timezone

from .models import DischargeSummary, DischargeMedication


def get_discharge_summary(admission_id):
    """Get or return None for a discharge summary linked to an admission."""
    return DischargeSummary.objects.filter(admission_id=admission_id).first()


def create_discharge_summary(admission_id, user=None):
    """Create a new draft discharge summary for an admission."""
    from admission.models import Admission

    with transaction.atomic():
        admission = Admission.objects.select_for_update().get(pk=admission_id)

        existing = DischargeSummary.objects.filter(admission=admission).first()
        if existing:
            return existing

        summary = DischargeSummary.objects.create(
            admission=admission,
            created_by=user,
        )
        return summary


def auto_populate_summary(summary):
    """
    Auto-populate discharge summary fields from all available clinical data.
    Only fills fields that are currently empty — never overwrites doctor input.
    Pulls from: triage, consultations, prescriptions, nursing, admission,
    lab requests (clinical indication), radiology, and visit events.
    """
    admission = summary.admission
    visit = admission.visit
    update_fields = []

    def _dirty(field):
        """Check if a text field is empty/blank."""
        return not getattr(summary, field, "").strip()

    # ── Gather data from ALL sources ──
    triage = None
    if visit:
        triage = (
            visit.triage_assessments
            .order_by("-assessed_at")
            .first()
        )

    consultations = []
    if visit:
        consultations = list(
            visit.consultations
            .select_related("doctor")
            .order_by("-started_at")
        )

    prescriptions = []
    if visit:
        from consultation.models import Prescription
        prescriptions = list(
            Prescription.objects
            .filter(consultation__visit=visit)
            .select_related("medicine")
        )

    from nursing.models import NursingNote, DailyVitals, Treatment
    nursing_notes = list(
        NursingNote.objects.filter(admission=admission).order_by("-created_at")
    )
    daily_vitals = list(
        DailyVitals.objects.filter(admission=admission).order_by("-record_date")
    )
    treatments = list(
        Treatment.objects.filter(admission=admission).order_by("-created_at")
    )

    # Lab requests with clinical indication
    lab_requests = []
    if visit:
        from laboratory.models import LabRequest
        lab_requests = list(
            LabRequest.objects
            .filter(visit=visit)
            .select_related("lab_test")
        )

    # Radiology requests with clinical indication
    radiology_requests = []
    if visit:
        from radiology.models import RadiologyRequest
        radiology_requests = list(
            RadiologyRequest.objects
            .filter(visit=visit)
            .select_related("radiology_service")
        )

    # Visit events (audit trail)
    visit_events = []
    if visit:
        from triage.models import VisitEvent
        visit_events = list(
            VisitEvent.objects
            .filter(visit=visit)
            .select_related("created_by")
            .order_by("timestamp")
        )

    # ── 1. Primary Diagnosis ──
    if _dirty("primary_diagnosis"):
        diagnoses = []
        # Admission diagnosis
        if admission.diagnosis and admission.diagnosis.strip():
            diagnoses.append(admission.diagnosis.strip())
        # Consultation diagnoses
        for c in consultations:
            if c.diagnosis and c.diagnosis.strip():
                diagnoses.append(c.diagnosis.strip())
        # Lab clinical indications (doctor's suspected diagnosis when ordering tests)
        for lr in lab_requests:
            if lr.clinical_indication and lr.clinical_indication.strip():
                text = lr.clinical_indication.strip()
                if text.lower() not in [d.lower() for d in diagnoses]:
                    diagnoses.append(f"Lab Indication: {text}")
        # Radiology clinical indications
        for rr in radiology_requests:
            if hasattr(rr, 'clinical_indication') and rr.clinical_indication and rr.clinical_indication.strip():
                text = rr.clinical_indication.strip()
                if text.lower() not in [d.lower() for d in diagnoses]:
                    diagnoses.append(f"Imaging Indication: {text}")
        if diagnoses:
            summary.primary_diagnosis = "\n".join(dict.fromkeys(diagnoses))
            update_fields.append("primary_diagnosis")

    # ── 2. Secondary Diagnosis ──
    if _dirty("secondary_diagnosis"):
        all_dx = []
        if admission.diagnosis and admission.diagnosis.strip():
            all_dx.append(admission.diagnosis.strip())
        for c in consultations:
            if c.diagnosis and c.diagnosis.strip():
                all_dx.append(c.diagnosis.strip())
        unique_dx = list(dict.fromkeys(all_dx))
        if len(unique_dx) > 1:
            summary.secondary_diagnosis = "\n".join(unique_dx[1:])
            update_fields.append("secondary_diagnosis")

    # ── 3. Reason for Admission ──
    if _dirty("reason_for_admission"):
        reasons = []
        if triage and triage.chief_complaint and triage.chief_complaint.strip():
            reasons.append(f"Presenting Complaint: {triage.chief_complaint.strip()}")
        if admission.diagnosis and admission.diagnosis.strip():
            reasons.append(f"Diagnosis: {admission.diagnosis.strip()}")
        if admission.notes and admission.notes.strip():
            reasons.append(f"Admission Notes: {admission.notes.strip()}")
        # Lab clinical indications
        indications = []
        for lr in lab_requests:
            if lr.clinical_indication and lr.clinical_indication.strip():
                indications.append(lr.clinical_indication.strip())
        if indications:
            reasons.append(f"Clinical Indications: {'; '.join(dict.fromkeys(indications))}")
        if reasons:
            summary.reason_for_admission = "\n".join(reasons)
            update_fields.append("reason_for_admission")

    # ── 4. History of Present Illness ──
    if _dirty("history_of_present_illness"):
        hpi_parts = []
        if triage:
            if triage.chief_complaint and triage.chief_complaint.strip():
                hpi_parts.append(f"Chief Complaint: {triage.chief_complaint.strip()}")
            if triage.nurse_notes and triage.nurse_notes.strip():
                hpi_parts.append(f"Triage Assessment: {triage.nurse_notes.strip()}")
        # All consultation notes (most recent first)
        for c in consultations:
            if c.notes and c.notes.strip():
                doctor_name = c.doctor.get_full_name() if c.doctor else "Doctor"
                hpi_parts.append(f"Consultation ({doctor_name}): {c.notes.strip()}")
        # Admission notes
        if admission.notes and admission.notes.strip():
            hpi_parts.append(f"Admission Notes: {admission.notes.strip()}")
        if hpi_parts:
            summary.history_of_present_illness = "\n\n".join(hpi_parts)
            update_fields.append("history_of_present_illness")

    # ── 5. Clinical Findings (vitals + exam + lab indications) ──
    if _dirty("clinical_findings"):
        findings = []
        # Triage vitals
        if triage:
            vitals_text = (
                f"Temperature: {triage.temperature}\u00b0C | "
                f"BP: {triage.blood_pressure_systolic}/{triage.blood_pressure_diastolic} mmHg | "
                f"Pulse: {triage.pulse} bpm | "
                f"RR: {triage.respiratory_rate}/min | "
                f"SpO2: {triage.oxygen_saturation}% | "
                f"Weight: {triage.weight} kg"
            )
            findings.append(f"Initial Vitals: {vitals_text}")
            # BMI if height/weight available
            if triage.height and triage.weight:
                height_m = float(triage.height) / 100
                if height_m > 0:
                    bmi = float(triage.weight) / (height_m ** 2)
                    findings.append(f"BMI: {bmi:.1f} kg/m\u00b2")
        # Latest daily vitals
        if daily_vitals:
            latest = daily_vitals[0]
            findings.append(
                f"Latest Vitals ({latest.record_date}): "
                f"Temp {latest.temperature}\u00b0C, "
                f"BP {latest.blood_pressure_systolic}/{latest.blood_pressure_diastolic}, "
                f"Pulse {latest.pulse}, SpO2 {latest.oxygen_saturation}%"
            )
        # Consultation clinical findings
        for c in consultations:
            if c.notes and c.notes.strip():
                findings.append(f"Clinical Examination: {c.notes.strip()}")
                break
        if findings:
            summary.clinical_findings = "\n".join(findings)
            update_fields.append("clinical_findings")

    # ── 6. Treatment Given ──
    if _dirty("treatment_given"):
        tx_parts = []
        # Consultation treatment plans
        for c in consultations:
            if c.treatment_plan and c.treatment_plan.strip():
                doctor_name = c.doctor.get_full_name() if c.doctor else "Doctor"
                tx_parts.append(f"Doctor's Plan ({doctor_name}): {c.treatment_plan.strip()}")
                break
        # Prescriptions
        if prescriptions:
            med_lines = []
            for p in prescriptions:
                line = f"\u2022 {p.medicine.name} {p.dosage} {p.frequency} for {p.duration_days} days"
                if p.instructions:
                    line += f" ({p.instructions})"
                med_lines.append(line)
            tx_parts.append("Prescriptions:\n" + "\n".join(med_lines))
        # Nursing treatments during admission
        if treatments:
            tx_lines = []
            for t in treatments:
                line = f"\u2022 {t.treatment}"
                if t.medication:
                    line += f" ({t.medication} {t.dosage})"
                if t.notes:
                    line += f" - {t.notes}"
                tx_lines.append(line)
            tx_parts.append("In-patient Treatments:\n" + "\n".join(tx_lines))
        if tx_parts:
            summary.treatment_given = "\n\n".join(tx_parts)
            update_fields.append("treatment_given")

    # ── 7. Procedures Done ──
    if _dirty("procedures_done"):
        proc_lines = []
        for t in treatments:
            desc = t.treatment.lower() if t.treatment else ""
            if any(kw in desc for kw in ["procedure", "surgery", "operation", "incision", "drainage", "sutur", "biopsy"]):
                line = f"\u2022 {t.treatment}"
                if t.notes:
                    line += f" ({t.notes})"
                proc_lines.append(line)
        if proc_lines:
            summary.procedures_done = "\n".join(proc_lines)
            update_fields.append("procedures_done")

    # ── 8. Patient Progress ──
    if _dirty("patient_progress"):
        progress_parts = []
        if nursing_notes:
            for note in nursing_notes[:5]:
                progress_parts.append(
                    f"[{note.created_at.strftime('%d %b %Y %H:%M')}] {note.note}"
                )
        if daily_vitals and len(daily_vitals) > 1:
            progress_parts.append(
                f"Vitals monitored daily over {len(daily_vitals)} day(s). "
                f"Latest: BP {daily_vitals[0].blood_pressure_systolic}/{daily_vitals[0].blood_pressure_diastolic}, "
                f"Temp {daily_vitals[0].temperature}\u00b0C"
            )
        if visit_events:
            event_descriptions = []
            for ev in visit_events:
                if ev.description and ev.description.strip():
                    event_descriptions.append(ev.description.strip())
            if event_descriptions:
                progress_parts.append("Visit Timeline:\n" + "\n".join(
                    f"\u2022 {d}" for d in event_descriptions
                ))
        if progress_parts:
            summary.patient_progress = "\n\n".join(progress_parts)
            update_fields.append("patient_progress")

    # ── 9. Condition on Discharge (sensible default) ──
    if _dirty("condition_on_discharge"):
        summary.condition_on_discharge = "Stable"
        update_fields.append("condition_on_discharge")

    # ── Save all at once ──
    if update_fields:
        update_fields.append("updated_at")
        summary.save(update_fields=update_fields)

    return summary


def save_draft(summary_id, data, user=None):
    """Save discharge summary draft fields."""
    with transaction.atomic():
        summary = DischargeSummary.objects.select_for_update().get(pk=summary_id)

        text_fields = [
            "primary_diagnosis",
            "secondary_diagnosis",
            "reason_for_admission",
            "history_of_present_illness",
            "clinical_findings",
            "investigations_performed",
            "procedures_done",
            "treatment_given",
            "patient_progress",
            "condition_on_discharge",
            "doctor_advice",
            "lifestyle_advice",
            "diet_advice",
            "activity_restrictions",
            "warning_signs",
        ]
        update_fields = []
        for field in text_fields:
            if field in data:
                setattr(summary, field, data[field])
                update_fields.append(field)

        follow_up_date = data.get("follow_up_date", "")
        if follow_up_date:
            summary.follow_up_date = follow_up_date
            update_fields.append("follow_up_date")
        elif "follow_up_date" in data:
            summary.follow_up_date = None
            update_fields.append("follow_up_date")

        if "doctor_signature" in data:
            summary.doctor_signature = data["doctor_signature"]
            update_fields.append("doctor_signature")

        update_fields.append("updated_at")
        summary.save(update_fields=update_fields)
        return summary


def finalize_discharge_summary(summary_id, user=None):
    """Finalize the discharge summary and perform discharge actions."""
    from admission.models import Admission
    from admission.services import discharge_patient

    with transaction.atomic():
        summary = DischargeSummary.objects.select_for_update().get(pk=summary_id)

        validation_errors = summary.can_finalize()
        if validation_errors:
            return summary, validation_errors

        summary.status = DischargeSummary.Status.FINALIZED
        summary.finalized_by = user
        summary.finalized_at = timezone.now()
        summary.save(update_fields=[
            "status", "finalized_by", "finalized_at", "updated_at",
        ])

        admission = summary.admission
        if admission.status == Admission.Status.ADMITTED:
            discharge_patient(admission_id=admission.pk, user=user)

        return summary, []


def get_all_discharge_summaries():
    """Get all discharge summaries with related data."""
    return (
        DischargeSummary.objects
        .select_related(
            "admission",
            "admission__patient",
            "admission__ward",
            "admission__room",
            "admission__bed",
            "admission__visit",
            "created_by",
            "finalized_by",
        )
        .order_by("-created_at")
    )


def get_patient_discharge_summaries(patient_id):
    """Get discharge summaries for a specific patient."""
    return (
        DischargeSummary.objects
        .filter(admission__patient_id=patient_id)
        .select_related(
            "admission",
            "admission__ward",
            "admission__room",
            "admission__bed",
        )
        .order_by("-created_at")
    )


def add_discharge_medication(summary_id, data):
    """Add a discharge medication to a summary."""
    summary = DischargeSummary.objects.get(pk=summary_id)
    return DischargeMedication.objects.create(
        discharge_summary=summary,
        medicine_name=data["medicine_name"],
        dosage=data.get("dosage", ""),
        frequency=data.get("frequency", ""),
        duration=data.get("duration", ""),
        instructions=data.get("instructions", ""),
    )


def remove_discharge_medication(medication_id):
    """Remove a discharge medication."""
    DischargeMedication.objects.filter(pk=medication_id).delete()


def get_investigations_for_visit(visit):
    """Retrieve lab and radiology investigations for a visit."""
    from laboratory.models import LabRequest, LabTestResultValue

    labs = (
        LabRequest.objects
        .filter(visit=visit)
        .select_related("lab_test")
        .prefetch_related("result_values__parameter")
    )

    # Attach structured results to each lab request
    labs_with_results = []
    for lab in labs:
        structured = {}
        for rv in lab.result_values.all():
            structured[rv.parameter.name] = {
                "value": rv.value,
                "unit": rv.parameter.unit,
                "normal_range": rv.parameter.normal_range,
            }

        # Determine display result
        display_result = ""
        if structured:
            parts = []
            for name, data in structured.items():
                line = f"{name}: {data['value']}"
                if data["unit"]:
                    line += f" {data['unit']}"
                if data["normal_range"]:
                    line += f" (Ref: {data['normal_range']})"
                parts.append(line)
            display_result = ", ".join(parts)
        elif lab.result:
            display_result = lab.result

        labs_with_results.append({
            "lab_test": lab.lab_test,
            "result": display_result or "Pending",
            "remarks": lab.remarks,
            "is_completed": lab.is_completed,
            "result_status": lab.result_status,
            "structured": structured,
        })

    from radiology.models import RadiologyRequest
    rads = RadiologyRequest.objects.filter(visit=visit).select_related("radiology_service")

    return labs_with_results, rads


def get_treatments_for_admission(admission):
    """Retrieve nursing treatments for an admission."""
    from nursing.models import Treatment
    return Treatment.objects.filter(admission=admission)


def get_prescriptions_for_visit(visit):
    """Retrieve prescriptions from consultations for a visit."""
    from consultation.models import Prescription
    return (
        Prescription.objects
        .filter(consultation__visit=visit)
        .select_related("medicine")
    )
