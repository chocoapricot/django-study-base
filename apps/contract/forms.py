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
            'description', 'notes', 'payment_site', 'is_active'
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
            'payment_site': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.master.models import BillPayment
        
        # 終了日を必須にする
        self.fields['end_date'].required = True
        
        # 支払いサイトの選択肢を設定（デフォルト）
        self.fields['payment_site'].queryset = BillPayment.get_active_list()
        
        # クライアントを取得
        client = None
        if self.instance and self.instance.pk and hasattr(self.instance, 'client') and self.instance.client:
            # 編集時
            client = self.instance.client
            self.fields['client_display'].initial = client.name
        elif hasattr(self, 'initial') and 'client' in self.initial:
            # 新規作成時にクライアントが指定されている場合
            try:
                client = Client.objects.get(pk=self.initial['client'])
                # クライアント表示名も設定
                self.fields['client_display'].initial = client.name
            except Client.DoesNotExist:
                pass
        
        # クライアントに支払いサイトが設定されている場合の処理
        if client and client.payment_site:
            # 選択肢を制限し、必須にする
            self.fields['payment_site'].queryset = BillPayment.objects.filter(id=client.payment_site.id)
            self.fields['payment_site'].initial = client.payment_site
            self.fields['payment_site'].required = True
            self.fields['payment_site'].widget.attrs.update({
                'style': 'pointer-events: none; background-color: #e9ecef;',
                'data-client-locked': 'true'
            })
            self.fields['payment_site'].help_text = 'クライアントで設定された支払いサイトが適用されます'
            # 空の選択肢を削除
            self.fields['payment_site'].empty_label = None
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        client = cleaned_data.get('client')
        payment_site = cleaned_data.get('payment_site')
        
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
        
        # 支払いサイトのバリデーション
        if client:
            if client.payment_site:
                # クライアントに支払いサイトが設定されている場合は必須
                if not payment_site:
                    self.add_error('payment_site', 'クライアントに支払いサイトが設定されているため、支払いサイトは必須です。')
                elif payment_site != client.payment_site:
                    self.add_error('payment_site', 'クライアントで設定された支払いサイトと異なる支払いサイトは選択できません。')
        
        return cleaned_data
    
    def clean_payment_site(self):
        """支払いサイトのクリーニング"""
        payment_site = self.cleaned_data.get('payment_site')
        client = self.cleaned_data.get('client') or (self.instance.client if self.instance and self.instance.pk else None)
        
        # クライアントに支払いサイトが設定されている場合は強制的にそれを使用
        if client and client.payment_site:
            return client.payment_site
        
        return payment_site


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