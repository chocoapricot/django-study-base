from django import forms
from .models import ClientContract, StaffContract
from apps.client.models import Client
from apps.staff.models import Staff


class ClientContractForm(forms.ModelForm):
    """クライアント契約フォーム"""
    
    class Meta:
        model = ClientContract
        fields = [
            'client', 'contract_name', 'contract_number', 'contract_type',
            'start_date', 'end_date', 'contract_amount', 'payment_terms',
            'description', 'notes', 'auto_renewal', 'is_active'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'auto_renewal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # クライアントの選択肢を設定
        self.fields['client'].queryset = Client.objects.all().order_by('name')
        self.fields['client'].empty_label = '選択してください'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('契約開始日は終了日より前の日付を入力してください。')
        
        return cleaned_data


class StaffContractForm(forms.ModelForm):
    """スタッフ契約フォーム"""
    
    class Meta:
        model = StaffContract
        fields = [
            'staff', 'contract_name', 'contract_number', 'contract_type',
            'start_date', 'end_date', 'contract_amount', 'payment_terms',
            'description', 'notes', 'auto_renewal', 'is_active'
        ]
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'auto_renewal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # スタッフの選択肢を設定
        self.fields['staff'].queryset = Staff.objects.all().order_by('name_last', 'name_first')
        self.fields['staff'].empty_label = '選択してください'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('契約開始日は終了日より前の日付を入力してください。')
        
        return cleaned_data