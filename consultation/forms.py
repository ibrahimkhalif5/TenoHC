from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Fieldset, ButtonHolder

from .models import Consultation, Prescription


class ConsultationForm(forms.ModelForm):
    """Form for completing a consultation."""

    class Meta:
        model = Consultation
        fields = ["diagnosis", "notes", "treatment_plan", "consultation_fee"]
        widgets = {
            "diagnosis": forms.Textarea(attrs={"rows": 4, "placeholder": "Enter diagnosis..."}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Clinical notes..."}),
            "treatment_plan": forms.Textarea(attrs={"rows": 3, "placeholder": "Treatment plan..."}),
            "consultation_fee": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            "diagnosis",
            "notes",
            "treatment_plan",
            "consultation_fee",
        )


class PrescriptionForm(forms.Form):
    """A single prescription line item — simplified for doctors."""

    medicine = forms.IntegerField(
        widget=forms.HiddenInput(),
    )
    dosage = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. 500mg",
            "class": "form-control form-control-sm",
        }),
        label="Dosage",
    )
    frequency = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. BD, TDS",
            "class": "form-control form-control-sm",
        }),
        label="Frequency",
    )
    duration_days = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            "min": "1",
            "placeholder": "Days",
            "class": "form-control form-control-sm",
        }),
        label="Duration (days)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("dosage", css_class="col-md-4"),
                Column("frequency", css_class="col-md-4"),
                Column("duration_days", css_class="col-md-4"),
            ),
        )


class PrescriptionFormSet(forms.BaseFormSet):
    """Formset for multiple prescriptions."""

    def clean(self):
        if any(self.errors):
            return
        medicines = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                medicine = form.cleaned_data.get("medicine")
                if medicine in medicines:
                    raise forms.ValidationError(
                        f"{medicine} is listed more than once. Please combine duplicate entries."
                    )
                medicines.append(medicine)


PrescriptionFormSet = forms.formset_factory(
    PrescriptionForm,
    formset=PrescriptionFormSet,
    extra=2,
    max_num=10,
    can_delete=True,
)
