from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit


class RadiologyResultForm(forms.Form):
    """Form for entering radiology findings and impression."""
    findings = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Enter radiological findings..."}),
        label="Findings",
    )
    impression = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Enter impression..."}),
        label="Impression",
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        label="Upload Image (optional)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            "findings",
            "impression",
            "image",
            Submit("submit", "Save Report", css_class="btn btn-success"),
        )
