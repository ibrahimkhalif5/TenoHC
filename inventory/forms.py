from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

from .models import Medicine, MedicineCategory, Supplier, Purchase, PurchaseItem


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "name", "generic_name", "category", "dosage_form", "strength",
            "unit", "selling_price", "cost_price", "minimum_stock",
            "reorder_level", "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = MedicineCategory.objects.filter(is_active=True)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row("name", "generic_name"),
            Row("category", "dosage_form"),
            Row("strength", "unit"),
            Row("selling_price", "cost_price"),
            Row("minimum_stock", "reorder_level"),
            "description",
            Submit("submit", "Save Medicine", css_class="btn btn-primary"),
        )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone", "email", "address"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "name", "contact_person", "phone", "email", "address",
            Submit("submit", "Save Supplier", css_class="btn btn-primary"),
        )


class PurchaseForm(forms.Form):
    """Create a new purchase order with items."""

    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        empty_label="-- Select Supplier --",
    )
    purchase_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    invoice_number = forms.CharField(max_length=100, required=False)
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"


class PurchaseItemForm(forms.Form):
    """Add a single item to a purchase."""

    medicine = forms.ModelChoiceField(
        queryset=Medicine.objects.filter(is_active=True),
        empty_label="-- Select Medicine --",
    )
    quantity = forms.IntegerField(min_value=1)
    unit_cost = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    batch_number = forms.CharField(max_length=100, required=False)
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"


class StockAdjustForm(forms.Form):
    """Manually adjust stock for a batch."""

    new_quantity = forms.IntegerField(min_value=0, label="New Quantity")
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Reason for Adjustment",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "new_quantity",
            "reason",
            Submit("submit", "Adjust Stock", css_class="btn btn-warning"),
        )


class DispenseForm(forms.Form):
    """Dispense stock for a patient."""

    quantity = forms.IntegerField(min_value=1, label="Quantity to Dispense")
    reference = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Patient # or Visit #"}),
        label="Reference",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "quantity", "reference", "notes",
            Submit("submit", "Dispense", css_class="btn btn-danger"),
        )
