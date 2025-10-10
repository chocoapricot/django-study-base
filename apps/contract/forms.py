from django import forms
from django.db.models import Subquery, OuterRef
from django.utils import timezone
from .models import ClientContract, StaffContract, ClientContractHaken, ClientContractTtp
from apps.client.models import Client, ClientUser, ClientDepartment
from apps.staff.models import Staff
from apps.system.settings.models import Dropdowns
from apps.company.models import Company, CompanyUser, CompanyDepartment


class DynamicClientUserField(forms.CharField):
    """動的プルダウン用のClientUserフィールド"""
    
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.Select(attrs={'class': 'form-select form-select-sm'})
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """文字列値をClientUserインスタンスに変換"""
        if not value:
            return None
        
        try:
            user_id = int(value)
            return ClientUser.objects.get(id=user_id)
        except (ValueError, TypeError, ClientUser.DoesNotExist):
            raise forms.ValidationError('無効な選択です。')


class DynamicClientDepartmentField(forms.CharField):
    """動的プルダウン用のClientDepartmentフィールド"""

    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.Select(attrs={'class': 'form-select form-select-sm'})
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """文字列値をClientDepartmentインスタンスに変換"""
        if not value:
            return None

        try:
            department_id = int(value)
            return ClientDepartment.objects.get(id=department_id)
        except (ValueError, TypeError, ClientDepartment.DoesNotExist):
            raise forms.ValidationError('無効な選択です。')


class CorporateNumberMixin:
    """契約に自社の法人番号を自動設定するMixin"""
    def save(self, commit=True):
        instance = super().save(commit=False)
        company = Company.objects.first()
        if company:
            instance.corporate_number = company.corporate_number
        if commit:
            instance.save()
            # many-to-manyフィールドを保存するために必要
            self.save_m2m()
        return instance


class ClientContractForm(CorporateNumberMixin, forms.ModelForm):
    """クライアント契約フォーム"""
    # 請求単位をテンプレートで確実にselectとしてレンダリングするために
    # フォームクラスでChoiceFieldを定義しておく
    bill_unit = forms.ChoiceField(
        label='請求単位',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
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

    client_contract_type_display = forms.CharField(
        label='契約種別',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'readonly': True})
    )
    
    contract_status = forms.ChoiceField(
        label='契約状況',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        required=False,
    )
    
    class Meta:
        model = ClientContract
        fields = [
            'client', 'client_contract_type_code', 'contract_name', 'job_category', 'contract_pattern', 'contract_number', 'contract_status',
            'start_date', 'end_date', 'contract_amount', 'bill_unit',
            'notes', 'memo', 'payment_site'
        ]
        widgets = {
            'client': forms.HiddenInput(),
            'client_contract_type_code': forms.HiddenInput(),
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'job_category': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'contract_pattern': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'contract_number': forms.HiddenInput(),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'bill_unit': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'payment_site': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.master.models import BillPayment, ContractPattern, JobCategory
        self.fields['job_category'].queryset = JobCategory.objects.filter(is_active=True)
        self.fields['contract_pattern'].required = True
        self.fields['contract_pattern'].empty_label = '契約書パターンを選択してください'
        self.fields['end_date'].required = True
        self.fields['payment_site'].queryset = BillPayment.get_active_list()

        # 請求単位の選択肢を設定
        # Dropdownsモデルからactiveな請求単位を取得して選択肢を組み立てる
        bill_choices = [('', '---------')] + [
            (d.value, d.name) for d in Dropdowns.objects.filter(category='bill_unit', active=True).order_by('disp_seq')
        ]
        self.fields['bill_unit'].choices = bill_choices
        # 要求により請求単位は保存時に必須
        self.fields['bill_unit'].required = True

        # 契約番号は自動採番のため非表示
        self.fields['contract_number'].required = False

        contract_type_code = None
        if self.is_bound and 'client_contract_type_code' in self.data:
            contract_type_code = self.data.get('client_contract_type_code')
        elif self.instance and self.instance.pk:
            contract_type_code = self.instance.client_contract_type_code
        elif self.initial and 'client_contract_type_code' in self.initial:
            contract_type_code = self.initial.get('client_contract_type_code')

        if contract_type_code:
            self.fields['contract_pattern'].queryset = ContractPattern.objects.filter(
                is_active=True, domain='10', contract_type_code=contract_type_code
            )
            try:
                dropdown = Dropdowns.objects.get(category='client_contract_type', value=contract_type_code)
                self.fields['client_contract_type_display'].initial = dropdown.name
            except Dropdowns.DoesNotExist:
                self.fields['client_contract_type_display'].initial = '未設定'
        else:
            self.fields['contract_pattern'].queryset = ContractPattern.objects.none()

        # 編集画面では「作成中」「申請中」のみ選択可能にする
        choices = [
            (ClientContract.ContractStatus.DRAFT.value, ClientContract.ContractStatus.DRAFT.label),
            (ClientContract.ContractStatus.PENDING.value, ClientContract.ContractStatus.PENDING.label),
        ]
        if self.instance and self.instance.pk and self.instance.contract_status:
            current_choice = (self.instance.contract_status, self.instance.get_contract_status_display())
            if current_choice not in choices:
                choices.append(current_choice)
        self.fields['contract_status'].choices = choices

        # クライアントを取得
        client = None
        client_id = None

        if self.is_bound:
            # POSTデータからclient_idを取得
            # ClientContractFormのIDは 'client'
            client_id = self.data.get('client')
        elif self.instance and self.instance.pk:
            client_id = self.instance.client_id
        elif 'client' in self.initial:
            client_id = self.initial.get('client')

        if client_id:
            try:
                client = Client.objects.get(pk=client_id)
                self.fields['client_display'].initial = client.name
            except (Client.DoesNotExist, ValueError):
                pass
        
        # クライアントに支払条件が設定されている場合の処理
        if client and client.payment_site:
            # 選択肢を制限し、必須にする
            self.fields['payment_site'].queryset = BillPayment.objects.filter(id=client.payment_site.id)
            self.fields['payment_site'].initial = client.payment_site
            self.fields['payment_site'].required = True
            self.fields['payment_site'].widget.attrs.update({
                'style': 'pointer-events: none; background-color: #e9ecef;',
                'data-client-locked': 'true'
            })
            self.fields['payment_site'].help_text = 'クライアントで設定された支払条件が適用されます'
            # 空の選択肢を削除
            self.fields['payment_site'].empty_label = None

        # 契約状況に応じたフォームの制御
        if self.instance and self.instance.pk:
            # 「作成中」「申請中」以外は全フィールドを編集不可にする
            if self.instance.contract_status not in [ClientContract.ContractStatus.DRAFT, ClientContract.ContractStatus.PENDING]:
                for field_name, field in self.fields.items():
                    # payment_siteはクライアント設定でロックされている場合、そのスタイルを維持
                    if field_name == 'payment_site' and 'data-client-locked' in field.widget.attrs:
                        continue

                    if hasattr(field.widget, 'attrs'):
                        if isinstance(field.widget, forms.Select):
                            field.widget.attrs['style'] = 'pointer-events: none; background-color: #e9ecef;'
                        elif isinstance(field.widget, forms.CheckboxInput):
                             field.widget.attrs['disabled'] = True
                        else:
                            field.widget.attrs['readonly'] = True
                            current_class = field.widget.attrs.get('class', '')
                            if 'form-control' in current_class:
                                new_class = current_class.replace('form-control', 'form-control-plaintext')
                                field.widget.attrs['class'] = new_class
    
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
        
        if client and not client.corporate_number:
            self.add_error('client', '法人番号が設定されていないクライアントは選択できません。')

        # クライアントの基本契約締結日との関係チェック
        if client and start_date:
            contract_type_code = self.cleaned_data.get('client_contract_type_code')
            if contract_type_code == '20':  # 派遣契約の場合
                if client.basic_contract_date_haken and start_date < client.basic_contract_date_haken:
                    self.add_error('start_date', f'契約開始日は基本契約締結日（派遣）（{client.basic_contract_date_haken}）以降の日付を入力してください。')
            else:  # 業務委託などの場合
                if client.basic_contract_date and start_date < client.basic_contract_date:
                    self.add_error('start_date', f'契約開始日は基本契約締結日（業務委託）（{client.basic_contract_date}）以降の日付を入力してください。')
        
        # 支払条件のバリデーション
        if client:
            if client.payment_site:
                # クライアントに支払条件が設定されている場合は必須
                if not payment_site:
                    self.add_error('payment_site', 'クライアントに支払条件が設定されているため、支払条件は必須です。')
                elif payment_site != client.payment_site:
                    self.add_error('payment_site', 'クライアントで設定された支払条件と異なる支払条件は選択できません。')
        
        return cleaned_data
    
    def clean_payment_site(self):
        """支払条件のクリーニング"""
        payment_site = self.cleaned_data.get('payment_site')
        client = self.cleaned_data.get('client') or (self.instance.client if self.instance and self.instance.pk else None)
        
        # クライアントに支払条件が設定されている場合は強制的にそれを使用
        if client and client.payment_site:
            return client.payment_site
        
        return payment_site


class ClientContractHakenForm(forms.ModelForm):
    """クライアント契約派遣情報フォーム"""
    
    # 派遣先関連フィールドを動的プルダウン用のカスタムフィールドに変更
    haken_office = DynamicClientDepartmentField(
        label='派遣先事業所',
        required=True
    )
    haken_unit = DynamicClientDepartmentField(
        label='組織単位',
        required=True
    )
    commander = DynamicClientUserField(
        label='派遣先指揮命令者',
        required=True
    )
    complaint_officer_client = DynamicClientUserField(
        label='派遣先苦情申出先',
        required=True
    )
    responsible_person_client = DynamicClientUserField(
        label='派遣先責任者',
        required=True
    )
    
    class Meta:
        model = ClientContractHaken
        exclude = ['client_contract', 'version', 'created_at', 'created_by', 'updated_at', 'updated_by']
        widgets = {
            'work_location': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'business_content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'responsibility_degree': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'complaint_officer_company': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'responsible_person_company': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'limit_by_agreement': forms.RadioSelect,
            'limit_indefinite_or_senior': forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        # ビューから渡された client を取得
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)

        # 全てのフィールドを必須にする
        for field_name, field in self.fields.items():
            # business_content, responsibility_degree, work_locationは任意入力
            if field_name in ['business_content', 'responsibility_degree', 'work_location']:
                field.required = False
                continue

            field.required = True
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '選択してください'
            if isinstance(field.widget, forms.RadioSelect):
                field.error_messages['required'] = f'{field.label}を選択してください。'
                if field_name in ['limit_by_agreement', 'limit_indefinite_or_senior']:
                    field.choices = [choice for choice in field.choices if choice[0]]

        # 派遣先関連フィールドの初期設定（動的プルダウン用）
        dispatch_fields = [
            'haken_office', 'haken_unit',
            'commander', 'complaint_officer_client', 'responsible_person_client'
        ]
        for field_name in dispatch_fields:
            self.fields[field_name].choices = [('', '選択してください')]

        # 派遣元関連のフィールドの選択肢を自社ユーザに限定
        valid_departments = CompanyDepartment.get_valid_departments(timezone.now().date())
        department_display_order = valid_departments.filter(
            department_code=OuterRef('department_code')
        ).values('display_order')[:1]
        company_users = CompanyUser.objects.annotate(
            department_display_order=Subquery(department_display_order)
        ).order_by('department_display_order', 'display_order')

        self.fields['complaint_officer_company'].queryset = company_users
        self.fields['responsible_person_company'].queryset = company_users

        # 選択肢がない場合のラベルを設定
        if not company_users.exists():
            self.fields['complaint_officer_company'].empty_label = '選択可能な担当者はいません'
            self.fields['responsible_person_company'].empty_label = '選択可能な担当者はいません'

        # インスタンスがある場合、派遣先関連フィールドの値を設定
        if self.instance and self.instance.pk:
            if self.instance.haken_office_id:
                try:
                    office = ClientDepartment.objects.get(pk=self.instance.haken_office_id)
                    self.fields['haken_office'].initial = str(office.id)
                    self.fields['haken_office'].choices = [('', '選択してください'), (str(office.id), office.name)]
                except ClientDepartment.DoesNotExist:
                    pass

            if self.instance.haken_unit_id:
                try:
                    unit = ClientDepartment.objects.get(pk=self.instance.haken_unit_id)
                    self.fields['haken_unit'].initial = str(unit.id)
                    self.fields['haken_unit'].choices = [('', '選択してください'), (str(unit.id), unit.name)]
                except ClientDepartment.DoesNotExist:
                    pass

            if self.instance.commander_id:
                try:
                    commander = ClientUser.objects.get(pk=self.instance.commander_id)
                    self.fields['commander'].initial = str(commander.id)
                    self.fields['commander'].choices = [('', '選択してください'), (str(commander.id), commander.name)]
                except ClientUser.DoesNotExist:
                    pass
            
            if self.instance.complaint_officer_client_id:
                try:
                    officer = ClientUser.objects.get(pk=self.instance.complaint_officer_client_id)
                    self.fields['complaint_officer_client'].initial = str(officer.id)
                    self.fields['complaint_officer_client'].choices = [('', '選択してください'), (str(officer.id), officer.name)]
                except ClientUser.DoesNotExist:
                    pass
            
            if self.instance.responsible_person_client_id:
                try:
                    person = ClientUser.objects.get(pk=self.instance.responsible_person_client_id)
                    self.fields['responsible_person_client'].initial = str(person.id)
                    self.fields['responsible_person_client'].choices = [('', '選択してください'), (str(person.id), person.name)]
                except ClientUser.DoesNotExist:
                    pass






class StaffContractForm(CorporateNumberMixin, forms.ModelForm):
    """スタッフ契約フォーム"""
    pay_unit = forms.ChoiceField(
        label='支払単位',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
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

    contract_status = forms.ChoiceField(
        label='契約状況',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        required=False,
    )
    
    class Meta:
        model = StaffContract
        fields = [
            'staff', 'contract_name', 'job_category', 'contract_pattern', 'contract_number', 'contract_status',
            'start_date', 'end_date', 'contract_amount', 'pay_unit',
            'work_location', 'business_content', 'notes', 'memo'
        ]
        widgets = {
            'staff': forms.HiddenInput(),
            'contract_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'job_category': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'contract_pattern': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'contract_number': forms.HiddenInput(),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'pay_unit': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'work_location': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'business_content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.master.models import ContractPattern, JobCategory
        self.fields['job_category'].queryset = JobCategory.objects.filter(is_active=True)
        self.fields['contract_pattern'].queryset = ContractPattern.objects.filter(is_active=True, domain='1')
        if self.instance and self.instance.pk and hasattr(self.instance, 'staff') and self.instance.staff:
            self.fields['staff_display'].initial = f"{self.instance.staff.name_last} {self.instance.staff.name_first}"

        # 支払単位の選択肢を設定
        pay_unit_choices = [('', '---------')] + [
            (d.value, d.name) for d in Dropdowns.objects.filter(category='pay_unit', active=True).order_by('disp_seq')
        ]
        self.fields['pay_unit'].choices = pay_unit_choices
        self.fields['pay_unit'].required = True

        # 契約番号は自動採番のため非表示
        self.fields['contract_number'].required = False

        # 編集画面では「作成中」「申請中」のみ選択可能にする
        choices = [
            (StaffContract.ContractStatus.DRAFT.value, StaffContract.ContractStatus.DRAFT.label),
            (StaffContract.ContractStatus.PENDING.value, StaffContract.ContractStatus.PENDING.label),
        ]
        if self.instance and self.instance.pk and self.instance.contract_status:
            current_choice = (self.instance.contract_status, self.instance.get_contract_status_display())
            if current_choice not in choices:
                choices.append(current_choice)
        self.fields['contract_status'].choices = choices

        # 契約状況に応じたフォームの制御
        if self.instance and self.instance.pk:
            # 「作成中」「申請中」以外は全フィールドを編集不可にする
            if self.instance.contract_status not in [StaffContract.ContractStatus.DRAFT, StaffContract.ContractStatus.PENDING]:
                for field_name, field in self.fields.items():
                    if hasattr(field.widget, 'attrs'):
                        if isinstance(field.widget, forms.Select):
                            field.widget.attrs['style'] = 'pointer-events: none; background-color: #e9ecef;'
                        elif isinstance(field.widget, forms.CheckboxInput):
                             field.widget.attrs['disabled'] = True
                        else:
                            field.widget.attrs['readonly'] = True
                            current_class = field.widget.attrs.get('class', '')
                            if 'form-control' in current_class:
                                new_class = current_class.replace('form-control', 'form-control-plaintext')
                                field.widget.attrs['class'] = new_class
    
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


class ClientContractTtpForm(forms.ModelForm):
    """クライアント契約紹介予定派遣情報フォーム"""

    class Meta:
        model = ClientContractTtp
        exclude = ['haken', 'version', 'created_at', 'created_by', 'updated_at', 'updated_by']
        widgets = {
            'contract_period': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'probation_period': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'business_content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'work_location': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'working_hours': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'break_time': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'overtime': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'holidays': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'vacations': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'wages': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'insurances': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'employer_name': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
            'other': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.required = False