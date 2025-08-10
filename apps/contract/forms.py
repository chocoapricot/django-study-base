from django import forms
from .models import ClientContract, StaffContract
from apps.client.models import Client
from apps.staff.models import Staff


class ClientContractForm(forms.ModelForm):
    """クライアント契約フォーム"""
    
    # 選択されたクライアント名を表示するための読み取り専用フィールド
    client_display = forms.CharField(
        label='クライアント',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'readonly': True,
            'placeholder': 'クライアントを選択してください'
        })
    )
    
    class Meta:
        model = ClientContract
        fields = [
            'client', 'contract_name', 'contract_number', 'contract_type',
            'start_date', 'end_date', 'contract_amount', 'payment_terms',
            'description', 'notes', 'is_active'
        ]
        widgets = {
            'client': forms.HiddenInput(),  # 隠しフィールドに変更
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 終了日を必須にする
        self.fields['end_date'].required = True
        # 編集時に選択されたクライアント名を表示
        if self.instance and self.instance.pk and hasattr(self.instance, 'client') and self.instance.client:
            self.fields['client_display'].initial = self.instance.client.name
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        client = cleaned_data.get('client')
        
        # 終了日を必須にする
        if not end_date:
            self.add_error('end_date', '契約終了日は必須です。')
        
        # 開始日と終了日の関係チェック
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('契約開始日は終了日より前の日付を入力してください。')
        
        # クライアントの基本契約締結日との関係チェック
        if client and start_date:
            # 基本契約締結日より前の開始日はエラー
            if client.basic_contract_date and start_date < client.basic_contract_date:
                self.add_error('start_date', f'契約開始日は基本契約締結日（{client.basic_contract_date}）以降の日付を入力してください。')
        
        return cleaned_data


class StaffContractForm(forms.ModelForm):
    """スタッフ契約フォーム"""
    
    # 選択されたスタッフ名を表示するための読み取り専用フィールド
    staff_display = forms.CharField(
        label='スタッフ',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'readonly': True,
            'placeholder': 'スタッフを選択してください'
        })
    )
    
    class Meta:
        model = StaffContract
        fields = [
            'staff', 'contract_name', 'contract_number', 'contract_type',
            'start_date', 'end_date', 'contract_amount', 'payment_terms',
            'description', 'notes', 'is_active'
        ]
        widgets = {
            'staff': forms.HiddenInput(),  # 隠しフィールドに変更
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 編集時に選択されたスタッフ名を表示
        if self.instance and self.instance.pk and hasattr(self.instance, 'staff') and self.instance.staff:
            self.fields['staff_display'].initial = f"{self.instance.staff.name_last} {self.instance.staff.name_first}"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        staff = cleaned_data.get('staff')
        
        # 開始日と終了日の関係チェック
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('契約開始日は終了日より前の日付を入力してください。')
        
        # スタッフの入社日・退職日との関係チェック
        if staff and start_date:
            # 入社日より前の開始日はエラー
            if staff.hire_date and start_date < staff.hire_date:
                self.add_error('start_date', f'契約開始日は入社日（{staff.hire_date}）以降の日付を入力してください。')
            
            # 退職日より後の終了日はエラー
            if staff.resignation_date and end_date and end_date > staff.resignation_date:
                self.add_error('end_date', f'契約終了日は退職日（{staff.resignation_date}）以前の日付を入力してください。')
        
        return cleaned_data