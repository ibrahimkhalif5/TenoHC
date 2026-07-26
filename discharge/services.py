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
    """
    admission = summary.admission
    visit = admission.visit
    update_fields = []

    # ── Gather data from all sources ──
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

    # ── 1. Primary Diagnosis ──
    if not summary.primary_diagnosis.strip():
        diagnoses = []
        if admission.diagnosis and admission.diagnosis.strip():
            diagnoses.append(admission.diagnosis.strip())
        for c in consultations:
            if c.diagnosis and c.diagnosis.strip():
                diagnoses.append(c.diagnosis.strip())
        if diagnoses:
            summary.primary_diagnosis = "\n".join(dict.fromkeys(diagnoses))
            update_fields.append("primary_diagnosis")

    # ── 2. Secondary Diagnosis ──
    if not summary.secondary_diagnosis.strip() and consultations:
        # If multiple consultations with different diagnoses, secondary = rest
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
    if not summary.reason_for_admission.strip():
        reasons = []
        if triage and triage.chief_complaint and triage.chief_complaint.strip():
            reasons.append(triage.chief_complaint.strip())
        if admission.diagnosis and admission.diagnosis.strip():
            reasons.append(f"Diagnosed with: {admission.diagnosis.strip()}")
        if reasons:
            summary.reason_for_admission = "\n".join(reasons)
            update_fields.append("reason_for_admission")

    # ── 4. History of Present Illness ──
    if not summary.history_of_present_illness.strip():
        hpi_parts = []
        if triage:
            if triage.chief_complaint and triage.chief_complaint.strip():
                hpi_parts.append(f"Chief Complaint: {triage.chief_complaint.strip()}")
            if triage.nurse_notes and triage.nurse_notes.strip():
                hpi_parts.append(f"Triage Notes: {triage.nurse_notes.strip()}")
        for c in consultations:
            if c.notes and c.notes.strip():
                hpi_parts.append(f"Consultation Notes: {c.notes.strip()}")
                break  # Only the most recent consultation notes
        if hpi_parts:
            summary.history_of_present_illness = "\n\n".join(hpi_parts)
            update_fields.append("history_of_present_illness")

    # ── 5. Clinical Findings (vitals + exam) ──
    if not summary.clinical_findings.strip():
        findings = []
        # Triage vitals
        if triage:
            vitals_text = (
                f"Temperature: {triage.temperature}°C | "
                f"BP: {triage.blood_pressure_systolic}/{triage.blood_pressure_diastolic} mmHg | "
                f"Pulse: {triage.pulse} bpm | "
                f"RR: {triage.respiratory_rate}/min | "
                f"SpO2: {triage.oxygen_saturation}% | "
                f"Weight: {triage.weight} kg"
            )
            findings.append(f"Initial Vitals: {vitals_text}")
        # Latest daily vitals
        if daily_vitals:
            latest = daily_vitals[0]
            findings.append(
                f"Latest Vitals ({latest.record_date}): "
                f"Temp {latest.temperature}°C, "
                f"BP {latest.blood_pressure_systolic}/{latest.blood_pressure_diastolic}, "
                f"Pulse {latest.pulse}, SpO2 {latest.oxygen_saturation}%"
            )
        # Consultation clinical findings (from notes)
        for c in consultations:
            if c.notes and c.notes.strip():
                findings.append(f"Clinical Notes: {c.notes.strip()}")
                break
        if findings:
            summary.clinical_findings = "\n".join(findings)
            update_fields.append("clinical_findings")

    # ── 6. Treatment Given ──
    if not summary.treatment_given.strip():
        tx_parts = []
        # Consultation treatment plans
        for c in consultations:
            if c.treatment_plan and c.treatment_plan.strip():
                tx_parts.append(f"Doctor's Plan: {c.treatment_plan.strip()}")
                break
        # Prescriptions
        if prescriptions:
            med_lines = []
            for p in prescriptions:
                line = f"{p.medicine.name} {p.dosage} {p.frequency} for {p.duration_days} days"
                if p.instructions:
                    line += f" ({p.instructions})"
                med_lines.append(line)
            tx_parts.append("Prescriptions:\n" + "\n".join(med_lines))
        # Nursing treatments during admission
        if treatments:
            tx_lines = []
            for t in treatments:
                line = f"- {t.treatment}"
                if t.medication:
                    line += f" ({t.medication} {t.dosage})"
                tx_lines.append(line)
            tx_parts.append("In-patient Treatments:\n" + "\n".join(tx_lines))
        if tx_parts:
            summary.treatment_given = "\n\n".join(tx_parts)
            update_fields.append("treatment_given")

    # ── 7. Procedures Done ──
    if not summary.procedures_done.strip():
        proc_lines = []
        for t in treatments:
            if t.treatment and "procedure" in t.treatment.lower() or "surgery" in t.treatment.lower():
                proc_lines.append(f"- {t.treatment}")
        if proc_lines:
            summary.procedures_done = "\n".join(proc_lines)
            update_fields.append("procedures_done")

    # ── 8. Patient Progress ──
    if not summary.patient_progress.strip():
        progress_parts = []
        if nursing_notes:
            for note in nursing_notes[:5]:  # Last 5 nursing notes
                progress_parts.append(
                    f"[{note.created_at.strftime('%d %b %Y %H:%M')}] {note.note}"
                )
        if daily_vitals and len(daily_vitals) > 1:
            progress_parts.append(
                f"Vitals monitored daily over {len(daily_vitals)} day(s). "
                f"Latest: BP {daily_vitals[0].blood_pressure_systolic}/{daily_vitals[0].blood_pressure_diastolic}, "
                f"Temp {daily_vitals[0].temperature}°C"
            )
        if progress_parts:
            summary.patient_progress = "\n\n".join(progress_parts)
            update_fields.append("patient_progress")

    # ── 9. Condition on Discharge (sensible default) ──
    if not summary.condition_on_discharge.strip():
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
    from laboratory.models import LabRequest
    from radiology.models import RadiologyRequest

    labs = LabRequest.objects.filter(visit=visit).select_related("lab_test")
    rads = RadiologyRequest.objects.filter(visit=visit).select_related("radiology_service")

    return labs, rads


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
