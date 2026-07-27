from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

from .models import TriageAssessment


class TriageAssessmentForm(forms.ModelForm):
    """Form for triage vitals capture."""

    class Meta:
        model = TriageAssessment
        fields = [
            "temperature", "weight", "height",
            "blood_pressure_systolic", "blood_pressure_diastolic",
            "pulse", "respiratory_rate", "oxygen_saturation",
            "chief_complaint", "nurse_notes",
        ]
        widgets = {
            "chief_complaint": forms.Textarea(attrs={"rows": 3}),
            "nurse_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["temperature"].initial = 37.0
        self.fields["pulse"].initial = 72
        self.fields["respiratory_rate"].initial = 16
        self.fields["oxygen_saturation"].initial = 98
        self.fields["blood_pressure_systolic"].required = False
        self.fields["blood_pressure_diastolic"].required = False
        self.fields["blood_pressure_systolic"].initial = None
        self.fields["blood_pressure_diastolic"].initial = None
        self.fields["weight"].initial = 70.0
        self.fields["height"].initial = 170.0
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("temperature", css_class="col-md-6"),
                Column("weight", css_class="col-md-6"),
            ),
            Row(
                Column("height", css_class="col-md-6"),
                Column("pulse", css_class="col-md-6"),
            ),
            Row(
                Column("blood_pressure_systolic", css_class="col-md-6"),
                Column("blood_pressure_diastolic", css_class="col-md-6"),
            ),
            Row(
                Column("respiratory_rate", css_class="col-md-6"),
                Column("oxygen_saturation", css_class="col-md-6"),
            ),
            "chief_complaint",
            "nurse_notes",
            Submit("submit", "Release to Doctor", css_class="btn btn-success"),
        )

    def clean_temperature(self):
        val = self.cleaned_data["temperature"]
        if val < 30 or val > 45:
            raise forms.ValidationError("Temperature must be between 30 and 45 Celsius")
        return val

    def clean_blood_pressure_systolic(self):
        val = self.cleaned_data.get("blood_pressure_systolic")
        if val is not None and (val < 60 or val > 300):
            raise forms.ValidationError("Systolic BP must be between 60 and 300")
        return val

    def clean_blood_pressure_diastolic(self):
        val = self.cleaned_data.get("blood_pressure_diastolic")
        if val is not None and (val < 30 or val > 200):
            raise forms.ValidationError("Diastolic BP must be between 30 and 200")
        return val

    def clean_pulse(self):
        val = self.cleaned_data["pulse"]
        if val < 20 or val > 300:
            raise forms.ValidationError("Pulse must be between 20 and 300 bpm")
        return val

    def clean_respiratory_rate(self):
        val = self.cleaned_data["respiratory_rate"]
        if val < 5 or val > 80:
            raise forms.ValidationError("Respiratory rate must be between 5 and 80")
        return val

    def clean_oxygen_saturation(self):
        val = self.cleaned_data["oxygen_saturation"]
        if val < 0 or val > 100:
            raise forms.ValidationError("Oxygen saturation must be between 0 and 100%")
        return val
