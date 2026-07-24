from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from .models import Payment


class PaymentForm(forms.Form):
    """Form for processing a payment."""

    PAYMENT_METHOD_CHOICES = Payment.PaymentMethod.choices

    amount = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        label="Amount",
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        initial="INSURANCE",
        label="Payment Method",
    )
    reference_number = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Transaction reference (optional)"}),
        label="Reference Number",
    )

    def __init__(self, *args, **kwargs):
        self.max_amount = kwargs.pop("max_amount", None)
        super().__init__(*args, **kwargs)
        if self.max_amount is not None:
            self.fields["amount"].widget.attrs["max"] = str(self.max_amount)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "amount",
            "payment_method",
            "reference_number",
            Submit("submit", "Process Payment", css_class="btn btn-success"),
        )

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero")
        if self.max_amount is not None and amount is not None and amount > self.max_amount:
            raise forms.ValidationError(
                f"Amount cannot exceed outstanding balance of KSh {self.max_amount:,.2f}"
            )
        return amount
