from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Submit

from .models import Patient, PatientCategory


class PatientRegistrationForm(forms.ModelForm):
    """Form for registering a new patient."""

    class Meta:
        model = Patient
        fields = [
            "photo", "national_id", "first_name", "last_name", "middle_name",
            "gender", "date_of_birth", "phone", "address",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "patient_category", "payment_type", "registration_fee",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "national_id": forms.TextInput(attrs={"placeholder": "NIN (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient_category"].queryset = PatientCategory.objects.filter(
            is_active=True,
        )
        self.fields["patient_category"].required = False
        self.fields["patient_category"].empty_label = "-- None --"
        self.fields["next_of_kin_name"].required = False
        self.fields["next_of_kin_phone"].required = False
        self.fields["next_of_kin_name"].widget.attrs["placeholder"] = "Optional"
        self.fields["next_of_kin_phone"].widget.attrs["placeholder"] = "Optional"
        self.fields["payment_type"].initial = "INSURANCE"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Row(
                Column("photo", css_class="col-md-4"),
                Column("national_id", css_class="col-md-8"),
            ),
            Row(
                Column("first_name", css_class="col-md-4"),
                Column("middle_name", css_class="col-md-4"),
                Column("last_name", css_class="col-md-4"),
            ),
            Row(
                Column("gender", css_class="col-md-4"),
                Column("date_of_birth", css_class="col-md-4"),
                Column("phone", css_class="col-md-4"),
            ),
            "address",
            Row(
                Column("next_of_kin_name", css_class="col-md-4"),
                Column("next_of_kin_phone", css_class="col-md-4"),
                Column("next_of_kin_relationship", css_class="col-md-4"),
            ),
            Row(
                Column("patient_category", css_class="col-md-4"),
                Column("payment_type", css_class="col-md-4"),
                Column("registration_fee", css_class="col-md-4"),
            ),
            Submit("submit", "Register Patient", css_class="btn btn-success"),
        )


class PatientSearchForm(forms.Form):
    """Form for searching patients."""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Search by name, phone, or ID...",
            "class": "form-control",
            "autofocus": True,
        }),
    )


class PatientUpdateForm(forms.ModelForm):
    """Form for editing an existing patient."""

    class Meta:
        model = Patient
        fields = [
            "photo", "national_id", "first_name", "last_name", "middle_name",
            "gender", "date_of_birth", "phone", "address",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "patient_category", "payment_type",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient_category"].queryset = PatientCategory.objects.filter(is_active=True)
        self.fields["patient_category"].required = False
        self.fields["patient_category"].empty_label = "-- None --"
        self.fields["next_of_kin_name"].required = False
        self.fields["next_of_kin_phone"].required = False
        self.fields["next_of_kin_name"].widget.attrs["placeholder"] = "Optional"
        self.fields["next_of_kin_phone"].widget.attrs["placeholder"] = "Optional"
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Row(
                Column("photo", css_class="col-md-4"),
                Column("national_id", css_class="col-md-8"),
            ),
            Row(
                Column("first_name", css_class="col-md-4"),
                Column("middle_name", css_class="col-md-4"),
                Column("last_name", css_class="col-md-4"),
            ),
            Row(
                Column("gender", css_class="col-md-4"),
                Column("date_of_birth", css_class="col-md-4"),
                Column("phone", css_class="col-md-4"),
            ),
            "address",
            Row(
                Column("next_of_kin_name", css_class="col-md-4"),
                Column("next_of_kin_phone", css_class="col-md-4"),
                Column("next_of_kin_relationship", css_class="col-md-4"),
            ),
            Row(
                Column("patient_category", css_class="col-md-6"),
                Column("payment_type", css_class="col-md-6"),
            ),
            Submit("submit", "Save Changes", css_class="btn btn-primary"),
        )
