from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from .models import NursingNote, DailyVitals, Treatment


class NursingNoteForm(forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = ["note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter nursing note..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "note",
            Submit("submit", "Add Note", css_class="btn btn-primary"),
        )


class DailyVitalsForm(forms.ModelForm):
    class Meta:
        model = DailyVitals
        fields = [
            "temperature", "blood_pressure_systolic", "blood_pressure_diastolic",
            "pulse", "respiratory_rate", "oxygen_saturation", "weight", "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "temperature",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "pulse",
            "respiratory_rate",
            "oxygen_saturation",
            "weight",
            "notes",
            Submit("submit", "Record Vitals", css_class="btn btn-success"),
        )


class TreatmentForm(forms.ModelForm):
    class Meta:
        model = Treatment
        fields = ["treatment", "medication", "dosage", "frequency", "notes"]
        widgets = {
            "treatment": forms.TextInput(attrs={"placeholder": "e.g. IV Cannulation, Wound Dressing"}),
            "medication": forms.TextInput(attrs={"placeholder": "e.g. Paracetamol"}),
            "dosage": forms.TextInput(attrs={"placeholder": "e.g. 500mg"}),
            "frequency": forms.TextInput(attrs={"placeholder": "e.g. Twice daily"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "treatment",
            "medication",
            "dosage",
            "frequency",
            "notes",
            Submit("submit", "Record Treatment", css_class="btn btn-info text-white"),
        )
