from django import forms
from .models import Company, CompanyDepartment

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'corporate_number', 'postal_code', 'address', 'phone_number', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'corporate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class CompanyDepartmentForm(forms.ModelForm):
    class Meta:
        model = CompanyDepartment
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
