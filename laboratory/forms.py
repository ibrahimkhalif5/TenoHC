from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit


class LabResultForm(forms.Form):
    """Form for entering lab results (used inline in the detail template)."""
    result = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Enter test result..."}),
        label="Result",
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional remarks..."}),
        label="Remarks",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "result",
            "remarks",
            Submit("submit", "Save Result", css_class="btn btn-success"),
        )
