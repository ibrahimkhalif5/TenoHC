from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit


class DispenseConfirmForm(forms.Form):
    """Simple confirmation form for dispensing a prescription."""

    confirm = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.HiddenInput,
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional dispensing notes..."}),
        label="Notes",
    )

    def __init__(self, *args, **kwargs):
        self.prescription = kwargs.pop("prescription", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "notes",
            Submit("submit", "Dispense Medication", css_class="btn btn-success"),
        )
