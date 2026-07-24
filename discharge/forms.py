from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML

from .models import DischargeSummary, DischargeMedication


class DischargeSummaryForm(forms.ModelForm):
    """Form for creating/editing discharge summary clinical and follow-up info."""

    class Meta:
        model = DischargeSummary
        fields = [
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
            "follow_up_date",
            "lifestyle_advice",
            "diet_advice",
            "activity_restrictions",
            "warning_signs",
        ]
        widgets = {
            "primary_diagnosis": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "secondary_diagnosis": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "reason_for_admission": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "history_of_present_illness": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "clinical_findings": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "investigations_performed": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "procedures_done": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "treatment_given": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "patient_progress": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "condition_on_discharge": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "doctor_advice": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "follow_up_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
            "lifestyle_advice": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "diet_advice": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "activity_restrictions": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "warning_signs": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "discharge-form"
        self.helper.layout = Layout()


class DischargeMedicationForm(forms.ModelForm):
    """Form for adding a discharge medication."""

    class Meta:
        model = DischargeMedication
        fields = [
            "medicine_name",
            "dosage",
            "frequency",
            "duration",
            "instructions",
        ]
        widgets = {
            "medicine_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Paracetamol"}),
            "dosage": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 500mg"}),
            "frequency": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 3 times daily"}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 7 days"}),
            "instructions": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Take after food"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "d-flex gap-2 align-items-end"
        self.helper.layout = Layout(
            Row(
                Column("medicine_name", css_class="col-md-3"),
                Column("dosage", css_class="col-md-2"),
                Column("frequency", css_class="col-md-2"),
                Column("duration", css_class="col-md-2"),
                Column("instructions", css_class="col-md-2"),
                Column(
                    Submit("submit", "Add", css_class="btn btn-success btn-sm"),
                    css_class="col-md-1",
                ),
            ),
        )


class DoctorSignatureForm(forms.Form):
    """Form for uploading doctor signature image."""

    doctor_signature = forms.ImageField(
        required=False,
        label="Doctor Signature",
    )
