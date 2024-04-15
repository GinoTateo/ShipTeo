from django import forms
from django.forms import ModelForm

from . import models
from .models import Store, Merch, User, Item


# class StoreForm(forms.ModelForm):
#    class Meta:
#      model = Store
#      fields = '__all__'
#
# class ItemForm(forms.ModelForm):
#    class Meta:
#      model = Item
#      fields = '__all__'
#
class MerchForm(forms.ModelForm):
    class Meta:
        model = Merch
        fields = ['upload']
#
#     def __init__(self, *args, **kwargs):
#         super(MerchForm, self).__init__(*args, **kwargs)
#         self.fields['OOS'].required = False
#         self.fields['worked_cases'].required = False
#
# class WeeklyDataForm(forms.ModelForm):
#     class Meta:
#         model = WeeklyData
#         fields = '__all__'
#
# class StoreForm2(forms.Form):
#     store = forms.CharField(max_length=100)
#     number = forms.IntegerField()
#
# class MerchForm2(ModelForm):
#     OOS = forms.ModelChoiceField(queryset=Item.objects.all())
#     worked_cases = forms.ModelChoiceField(queryset=Item.objects.all())
#     upload = forms.ImageField()
#     class Meta:
#             model = Merch
#             fields = ['OOS','worked_cases','upload']
#
#
#
#
# class MerchForm3(forms.ModelForm):
#    class Meta:
#        user = forms.ModelChoiceField(queryset=User.objects.all())
#        store = forms.ModelChoiceField(queryset=Store.objects)
#        OOS = forms.ModelMultipleChoiceField(queryset=Item.objects)
#        case_count = forms.IntegerField()
