from datetime import datetime, timedelta

from django import forms

# Create custom widget in your forms.py file.
class DateInput(forms.DateInput):
    input_type = 'date'

def my_date():
    return datetime.today() + timedelta(days=167)

class WarehouseForm(forms.Form):
    Date = forms.DateField(widget=DateInput, initial=my_date())
    Amount = forms.IntegerField(max_value=3000)

class palletForm(forms.Form):
    pallets = forms.IntegerField()
