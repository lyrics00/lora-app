from django import forms

class BorrowItemForm(forms.Form):
    borrow_duration = forms.IntegerField(
        min_value=1,
        label="Borrow Duration (Days)",
        help_text="Enter the number of days you wish to borrow this item."
    )