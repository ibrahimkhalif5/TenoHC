from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name", "category", "description", "unit_price", "cost_price",
            "unit_of_measure", "normal_range", "unit", "department", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g., Amoxicillin 500mg, Full Blood Count"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional description..."}),
            "unit_price": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0.00"}),
            "cost_price": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0.00"}),
            "unit_of_measure": forms.TextInput(attrs={"placeholder": "e.g., Tablet, Test, Session, Night"}),
            "normal_range": forms.TextInput(attrs={"placeholder": "e.g., 70-100 mg/dL, Negative, 4.5-11.0 x10^9/L"}),
            "unit": forms.TextInput(attrs={"placeholder": "e.g., mg/dL, x10^9/L, U/L, mEq/L"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["category"].required = True
        self.fields["unit_price"].required = True
        self.fields["description"].required = False
        self.fields["cost_price"].required = False
        self.fields["unit_of_measure"].required = False
        self.fields["normal_range"].required = False
        self.fields["unit"].required = False
        self.fields["department"].required = False

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="col-md-8"),
                Column("category", css_class="col-md-4"),
            ),
            Row(
                Column("unit_price", css_class="col-md-4"),
                Column("cost_price", css_class="col-md-4"),
                Column("unit_of_measure", css_class="col-md-4"),
            ),
            Row(
                Column("normal_range", css_class="col-md-8"),
                Column("unit", css_class="col-md-4"),
            ),
            Row(
                Column("department", css_class="col-md-6"),
                Column("is_active", css_class="col-md-6"),
            ),
            Field("description"),
        )
