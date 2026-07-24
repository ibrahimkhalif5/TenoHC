from django import forms


class ReportDateForm(forms.Form):
    report_type = forms.ChoiceField(
        choices=[
            ("financial", "Financial"),
            ("clinical", "Clinical"),
            ("patient", "Patient & Visit"),
            ("inventory", "Inventory"),
        ],
        widget=forms.Select(attrs={"class": "form-select", "onchange": "this.form.submit()"}),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        required=False,
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        required=False,
    )
