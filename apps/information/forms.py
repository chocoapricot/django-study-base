from django import forms
from .models import InformationFromCompany

class InformationForm(forms.ModelForm):
    class Meta:
        model = InformationFromCompany
        fields = ['target', 'title', 'content', 'start_date', 'end_date']
        widgets = {
            'target': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 5}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }
