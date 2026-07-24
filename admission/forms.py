from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

from .models import Ward, Room, Bed, Admission


class AdmissionForm(forms.Form):
    """Form for admitting a patient (ward, room, bed selection)."""

    ward_id = forms.IntegerField(widget=forms.HiddenInput)
    room_id = forms.IntegerField(widget=forms.HiddenInput)
    bed_id = forms.IntegerField(widget=forms.HiddenInput)
    diagnosis = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Diagnosis",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Notes",
    )

    def clean_ward_id(self):
        try:
            return Ward.objects.get(pk=self.cleaned_data["ward_id"], is_active=True)
        except Ward.DoesNotExist:
            raise forms.ValidationError("Invalid ward selected.")

    def clean_room_id(self):
        try:
            return Room.objects.get(pk=self.cleaned_data["room_id"], is_active=True, is_occupied=False)
        except Room.DoesNotExist:
            raise forms.ValidationError("Room is not available.")

    def clean_bed_id(self):
        try:
            return Bed.objects.get(pk=self.cleaned_data["bed_id"], is_active=True, is_occupied=False)
        except Bed.DoesNotExist:
            raise forms.ValidationError("Bed is not available.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "ward",
            "room",
            "bed",
            "diagnosis",
            "notes",
            Submit("submit", "Admit Patient", css_class="btn btn-primary"),
        )


class WardForm(forms.ModelForm):
    """Form for creating/editing a ward."""

    class Meta:
        model = Ward
        fields = ["name", "ward_type", "description", "price_per_night"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "name",
            "ward_type",
            "description",
            "price_per_night",
            Submit("submit", "Save Ward", css_class="btn btn-primary"),
        )


class RoomForm(forms.ModelForm):
    """Form for creating/editing a room."""

    class Meta:
        model = Room
        fields = ["ward", "room_number", "room_type", "capacity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ward"].queryset = Ward.objects.filter(is_active=True)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "ward",
            "room_number",
            "room_type",
            "capacity",
            Submit("submit", "Save Room", css_class="btn btn-primary"),
        )


class BedForm(forms.ModelForm):
    """Form for creating/editing a bed."""

    class Meta:
        model = Bed
        fields = ["room", "bed_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "room",
            "bed_number",
            Submit("submit", "Save Bed", css_class="btn btn-primary"),
        )
