from django import forms
from django.db.models import Subquery, OuterRef
from django.utils import timezone
from .models import ClientContract, StaffContract, ClientContractHaken, ClientContractTtp, ClientContractHakenExempt, StaffContractTeishokubiDetail, ContractAssignmentConfirm, ContractAssignmentHaken, ContractClientFlag, ContractStaffFlag
from apps.client.models import Client, ClientUser, ClientDepartment
from apps.staff.models import Staff
from apps.system.settings.models import Dropdowns
from apps.company.models import Company, CompanyUser, CompanyDepartment
from apps.master.models_other import FlagStatus
from apps.common.constants import Constants
from apps.common.forms import MyRadioSelect


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
            'business_content', 'notes', 'memo', 'payment_site', 'worktime_pattern', 'overtime_pattern', 'time_punch'
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
            'business_content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'payment_site': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'worktime_pattern': forms.HiddenInput(),
            'overtime_pattern': forms.HiddenInput(),
            'time_punch': forms.HiddenInput(),
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
        self.fields['bill_unit'].choices = Dropdowns.get_choices('bill_unit')
        # 要求により請求単位は保存時に必須
        self.fields['bill_unit'].required = True

        # 契約番号は自動採番のため非表示
        self.fields['contract_number'].required = False
        
        # 就業時間パターンは必須
        self.fields['worktime_pattern'].required = True
        
        # 時間外算出パターンは必須
        self.fields['overtime_pattern'].required = True

        contract_type_code = None
        if self.is_bound and 'client_contract_type_code' in self.data:
            contract_type_code = self.data.get('client_contract_type_code')
        elif self.instance and self.instance.pk:
            contract_type_code = self.instance.client_contract_type_code
        elif self.initial and 'client_contract_type_code' in self.initial:
            contract_type_code = self.initial.get('client_contract_type_code')

        if contract_type_code:
            self.fields['contract_pattern'].queryset = ContractPattern.objects.filter(
                is_active=True, domain=Constants.DOMAIN.CLIENT, contract_type_code=contract_type_code
            )
            try:
                dropdown = Dropdowns.objects.get(category='client_contract_type', value=contract_type_code)
                self.fields['client_contract_type_display'].initial = dropdown.name
            except Dropdowns.DoesNotExist:
                self.fields['client_contract_type_display'].initial = '未設定'
        else:
            self.fields['contract_pattern'].queryset = ContractPattern.objects.none()

        # 編集画面では「作成中」「申請」のみ選択可能にする
        editable_statuses = [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]
        choices = []
        for dropdown in Dropdowns.objects.filter(category='contract_status', active=True).order_by('disp_seq'):
            if dropdown.value in editable_statuses:
                choices.append((dropdown.value, dropdown.name))
        
        # 現在の契約状況が編集可能範囲外の場合は追加
        if self.instance and self.instance.pk and self.instance.contract_status:
            if self.instance.contract_status not in editable_statuses:
                display_name = Dropdowns.get_display_name('contract_status', self.instance.contract_status)
                choices.append((self.instance.contract_status, display_name))
        
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
            # 「作成中」「申請」以外は全フィールドを編集不可にする
            if self.instance.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
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
        contract_status = cleaned_data.get('contract_status')
        client_contract_type_code = cleaned_data.get('client_contract_type_code')
        
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
            if client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:  # 派遣契約の場合
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
        
        # 派遣契約で申請状態にする場合の給与関連情報チェック
        if (client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and 
            contract_status == Constants.CONTRACT_STATUS.PENDING):
            self._validate_assigned_staff_payroll()
        
        return cleaned_data
    
    def _validate_assigned_staff_payroll(self):
        """割当されたスタッフの給与関連情報をチェックする"""
        # 編集時のみチェック（新規作成時はまだ割当がない）
        if not self.instance or not self.instance.pk:
            return
        
        from .models import ContractAssignment
        from apps.staff.models import StaffPayroll
        
        # この契約に割当されているスタッフ契約を取得
        assignments = ContractAssignment.objects.filter(
            client_contract=self.instance
        ).select_related('staff_contract__staff')
        
        missing_payroll_staff = []
        for assignment in assignments:
            staff = assignment.staff_contract.staff
            try:
                # 給与関連情報が登録されているかチェック
                staff.payroll
            except StaffPayroll.DoesNotExist:
                missing_payroll_staff.append(f"{staff.name_last} {staff.name_first}")
        
        if missing_payroll_staff:
            staff_names = '、'.join(missing_payroll_staff)
            error_message = (
                f'派遣契約を申請するには、割当されたスタッフの給与関連情報が必要です。派遣先通知書に保険加入状況を記載する必要があるためです。'
                f'以下のスタッフの給与関連情報を登録してください：{staff_names}'
            )
            # non_field_errorsとしてエラーを追加
            self.add_error(None, error_message)
    
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
        exclude = ['client_contract', 'tenant_id', 'version', 'created_at', 'created_by', 'updated_at', 'updated_by']
        widgets = {
            'work_location': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'responsibility_degree': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'complaint_officer_company': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'responsible_person_company': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'limit_by_agreement': MyRadioSelect(),
            'limit_indefinite_or_senior': MyRadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        # ビューから渡された client を取得
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)

        # 新規作成時に初期値マスタから値を設定
        if not self.instance.pk:  # 新規作成の場合
            from apps.master.models import DefaultValue
            try:
                # 協定対象派遣労働者に限定するか否かの別の初期値を取得
                default_limit_by_agreement = DefaultValue.objects.get(key='ClientContractHaken.limit_by_agreement')
                # 'true'文字列を定数値に変換
                if default_limit_by_agreement.value.lower() == 'true':
                    self.fields['limit_by_agreement'].initial = Constants.LIMIT_BY_AGREEMENT.LIMITED
                else:
                    self.fields['limit_by_agreement'].initial = Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED
            except DefaultValue.DoesNotExist:
                # マスタに設定がない場合はデフォルトで「限定しない」
                self.fields['limit_by_agreement'].initial = Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED

        # 全てのフィールドを必須にする
        for field_name, field in self.fields.items():
            # responsibility_degree, work_locationは任意入力
            if field_name in ['responsibility_degree', 'work_location']:
                field.required = False
                continue

            field.required = True
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = '選択してください'
            if isinstance(field.widget, (forms.RadioSelect, MyRadioSelect)):
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
        valid_departments = CompanyDepartment.get_valid_departments(timezone.localdate())
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
            'staff', 'employment_type', 'contract_name', 'job_category', 'contract_pattern', 'contract_number', 'contract_status',
            'start_date', 'end_date', 'contract_amount', 'pay_unit',
            'work_location', 'business_content', 'notes', 'memo', 'worktime_pattern', 'overtime_pattern', 'time_punch'
        ]
        widgets = {
            'staff': forms.HiddenInput(),
            'employment_type': forms.HiddenInput(),
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
            'worktime_pattern': forms.HiddenInput(),
            'overtime_pattern': forms.HiddenInput(),
            'time_punch': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.client_contract = kwargs.pop('client_contract', None)
        super().__init__(*args, **kwargs)
        from apps.master.models import ContractPattern, JobCategory
        self.fields['job_category'].queryset = JobCategory.objects.filter(is_active=True)
        self.fields['contract_pattern'].queryset = ContractPattern.objects.filter(is_active=True, domain=Constants.DOMAIN.STAFF)
        self.fields['contract_pattern'].required = True
        self.fields['contract_pattern'].empty_label = '契約書パターンを選択してください'
        if self.instance and self.instance.pk and hasattr(self.instance, 'staff') and self.instance.staff:
            self.fields['staff_display'].initial = f"{self.instance.staff.name_last} {self.instance.staff.name_first}"

        # 支払単位の選択肢を設定
        self.fields['pay_unit'].choices = Dropdowns.get_choices('pay_unit')
        self.fields['pay_unit'].required = True

        # 契約番号は自動採番のため非表示
        self.fields['contract_number'].required = False
        
        # 就業時間パターンは必須
        self.fields['worktime_pattern'].required = True
        
        # 時間外算出パターンは必須
        self.fields['overtime_pattern'].required = True
        
        # 雇用形態に就業時間パターンが設定されているかチェック
        employment_type = None
        if self.instance and self.instance.pk and self.instance.employment_type:
            employment_type = self.instance.employment_type
        elif self.is_bound and self.data.get('employment_type'):
            try:
                from apps.master.models import EmploymentType
                employment_type = EmploymentType.objects.get(pk=self.data.get('employment_type'))
            except (EmploymentType.DoesNotExist, ValueError):
                pass
        
        # 雇用形態に就業時間パターンが設定されている場合は編集不可にする
        if employment_type and employment_type.worktime_pattern:
            self.fields['worktime_pattern'].widget.attrs['data-locked'] = 'true'
            self.fields['worktime_pattern'].widget.attrs['data-locked-by-employment'] = 'true'
            self.fields['worktime_pattern'].help_text = '雇用形態で設定された就業時間が適用されます'
        
        # 雇用形態に時間外算出パターンが設定されている場合は編集不可にする
        if employment_type and employment_type.overtime_pattern:
            self.fields['overtime_pattern'].widget.attrs['data-locked'] = 'true'
            self.fields['overtime_pattern'].widget.attrs['data-locked-by-employment'] = 'true'
            self.fields['overtime_pattern'].help_text = '雇用形態で設定された時間外算出が適用されます'

        # 編集画面では「作成中」「申請」のみ選択可能にする
        editable_statuses = [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]
        choices = []
        for dropdown in Dropdowns.objects.filter(category='contract_status', active=True).order_by('disp_seq'):
            if dropdown.value in editable_statuses:
                choices.append((dropdown.value, dropdown.name))
        
        # 現在の契約状況が編集可能範囲外の場合は追加
        if self.instance and self.instance.pk and self.instance.contract_status:
            if self.instance.contract_status not in editable_statuses:
                display_name = Dropdowns.get_display_name('contract_status', self.instance.contract_status)
                choices.append((self.instance.contract_status, display_name))
        
        self.fields['contract_status'].choices = choices

        # 契約状況に応じたフォームの制御
        if self.instance and self.instance.pk:
            # 「作成中」「申請」以外は全フィールドを編集不可にする
            if self.instance.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
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
        pay_unit = cleaned_data.get('pay_unit')
        contract_amount = cleaned_data.get('contract_amount')
        work_location = cleaned_data.get('work_location')
        job_category = cleaned_data.get('job_category')
        employment_type = cleaned_data.get('employment_type')
        worktime_pattern = cleaned_data.get('worktime_pattern')

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

        # 外国籍情報チェック
        if staff:
            self._validate_foreign_staff_contract(staff, job_category, end_date)

        # クライアント契約からの作成時の制限チェック
        if staff and employment_type:
            self._validate_client_contract_limitations(staff, employment_type, start_date)
        
        # クライアント契約との契約期間整合性チェック
        self._validate_contract_period_compatibility(start_date, end_date)
        
        # 雇用形態に就業時間パターンが設定されている場合のチェック
        if employment_type and employment_type.worktime_pattern:
            # 雇用形態の就業時間パターンを強制的に適用
            cleaned_data['worktime_pattern'] = employment_type.worktime_pattern
        
        # 雇用形態に時間外算出パターンが設定されている場合のチェック
        if employment_type and employment_type.overtime_pattern:
            # 雇用形態の時間外算出パターンを強制的に適用
            cleaned_data['overtime_pattern'] = employment_type.overtime_pattern

        # 最低賃金チェック
        try:
            # self.instanceはフォームのインスタンス（モデルオブジェクト）
            # cleaned_dataから取得した値でインスタンスを更新してバリデーション
            instance = self.instance or StaffContract()
            instance.start_date = start_date
            instance.pay_unit = pay_unit
            instance.contract_amount = contract_amount
            instance.work_location = work_location
            instance.validate_minimum_wage()
        except forms.ValidationError as e:
            self.add_error('contract_amount', e)

        return cleaned_data

    def _validate_foreign_staff_contract(self, staff, job_category, end_date):
        """外国籍スタッフの契約バリデーション"""
        # 外国籍情報が登録されているかチェック
        try:
            international_info = staff.international
        except:
            # 外国籍情報が登録されていない場合は何もしない
            return

        # 外国籍情報が登録されている場合のチェック
        if international_info:
            # 1. 職種が特定技能外国人受入該当になっていなければエラー
            if job_category and not job_category.is_specified_skilled_worker:
                self.add_error('job_category', 
                    f'外国籍スタッフ「{staff.name_last} {staff.name_first}」の契約では、'
                    f'特定技能外国人受入該当の職種を選択してください。')

            # 2. 契約終了日より前に在留期限がある場合にはエラー
            if end_date and international_info.residence_period_to and end_date > international_info.residence_period_to:
                self.add_error('end_date', 
                    f'契約終了日（{end_date}）が在留期限（{international_info.residence_period_to}）を超えています。'
                    f'在留期限内の日付を設定してください。')

            # 3. クライアント契約が派遣の場合、職種が農業漁業派遣該当になっていなければエラー
            if (self.client_contract and 
                self.client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
                job_category and not job_category.is_agriculture_fishery_dispatch):
                self.add_error('job_category', 
                    f'外国籍スタッフ「{staff.name_last} {staff.name_first}」の派遣契約では、'
                    f'農業漁業派遣該当の職種を選択してください。')

    def _validate_client_contract_limitations(self, staff, employment_type, start_date):
        """クライアント契約からの作成時の制限チェック"""
        # フォーム初期化時にクライアント契約が渡されていない場合は何もしない
        if not self.client_contract:
            return
            
        # 無期雇用派遣労働者又は60歳以上の者に限定する場合のチェック
        if (hasattr(self.client_contract, 'haken_info') and self.client_contract.haken_info and
                self.client_contract.haken_info.limit_indefinite_or_senior == Constants.LIMIT_BY_AGREEMENT.LIMITED):
            
            # 条件1: 無期雇用か
            is_indefinite_employment = not employment_type.is_fixed_term
            
            # 条件2: 契約開始日時点で60歳以上か
            is_over_60 = False
            if staff.birth_date and start_date:
                age_at_start = start_date.year - staff.birth_date.year - \
                    ((start_date.month, start_date.day) < (staff.birth_date.month, staff.birth_date.day))
                if age_at_start >= 60:
                    is_over_60 = True
            
            if not (is_indefinite_employment or is_over_60):
                self.add_error('employment_type', 
                    f'このクライアント契約は無期雇用派遣労働者又は60歳以上の者に限定されています。'
                    f'スタッフ「{staff.name}」は条件を満たしていません。')

    def _validate_contract_period_compatibility(self, start_date, end_date):
        """クライアント契約との契約期間整合性チェック"""
        # フォーム初期化時にクライアント契約が渡されていない場合は何もしない
        if not self.client_contract:
            return
            
        # スタッフ契約の開始日がクライアント契約の終了日より後の場合はエラー
        if (start_date and self.client_contract.end_date and 
            start_date > self.client_contract.end_date):
            self.add_error('start_date', 
                f'スタッフ契約開始日（{start_date}）がクライアント契約終了日（{self.client_contract.end_date}）より後になっています。')
        
        # スタッフ契約の終了日がクライアント契約の開始日より前の場合はエラー
        if (end_date and self.client_contract.start_date and 
            end_date < self.client_contract.start_date):
            self.add_error('end_date', 
                f'スタッフ契約終了日（{end_date}）がクライアント契約開始日（{self.client_contract.start_date}）より前になっています。')


class ClientContractTtpForm(forms.ModelForm):
    """クライアント契約紹介予定派遣情報フォーム"""

    class Meta:
        model = ClientContractTtp
        exclude = ['haken', 'tenant_id', 'version', 'created_at', 'created_by', 'updated_at', 'updated_by']
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

class ClientContractHakenExemptForm(forms.ModelForm):
    """クライアント契約派遣抵触日制限外情報フォーム"""

    class Meta:
        model = ClientContractHakenExempt
        exclude = ['haken', 'tenant_id', 'version', 'created_at', 'created_by', 'updated_at', 'updated_by']
        widgets = {
            'period_exempt_detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 抵触日制限外詳細は必須
        self.fields['period_exempt_detail'].required = True


class StaffContractTeishokubiDetailForm(forms.ModelForm):
    """個人抵触日詳細フォーム"""
    
    class Meta:
        model = StaffContractTeishokubiDetail
        fields = ['assignment_start_date', 'assignment_end_date']
        widgets = {
            'assignment_start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'assignment_end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignment_start_date'].label = '割当開始日'
        self.fields['assignment_end_date'].label = '割当終了日'


class ContractAssignmentConfirmForm(forms.ModelForm):
    """契約割り当て確認フォーム"""
    
    class Meta:
        model = ContractAssignmentConfirm
        fields = ['confirm_type', 'termination_reason', 'notes']
        widgets = {
            'confirm_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'termination_reason': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 確認種別の選択肢を設定
        self.fields['confirm_type'].choices = [
            (Constants.ASSIGNMENT_CONFIRM_TYPE.EXTEND, '延長予定'),
            (Constants.ASSIGNMENT_CONFIRM_TYPE.TERMINATE, '終了予定')
        ]
        self.fields['confirm_type'].required = True
        
        # 終了理由は任意（JavaScriptで動的に制御）
        self.fields['termination_reason'].required = False
        self.fields['notes'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        confirm_type = cleaned_data.get('confirm_type')
        termination_reason = cleaned_data.get('termination_reason')
        
        # 終了予定の場合は終了理由が必須
        if (confirm_type == Constants.ASSIGNMENT_CONFIRM_TYPE.TERMINATE and 
            not termination_reason):
            self.add_error('termination_reason', '終了予定の場合は終了理由を入力してください。')
        
        return cleaned_data


class ContractAssignmentHakenForm(forms.ModelForm):
    """契約割り当て派遣雇用安定措置フォーム"""
    
    class Meta:
        model = ContractAssignmentHaken
        fields = [
            'direct_employment_request', 'direct_employment_detail',
            'new_dispatch_offer', 'new_dispatch_detail',
            'indefinite_employment', 'indefinite_employment_detail',
            'other_measures', 'other_measures_detail'
        ]
        widgets = {
            'direct_employment_request': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'direct_employment_detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'new_dispatch_offer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new_dispatch_detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'indefinite_employment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'indefinite_employment_detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'other_measures': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'other_measures_detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # すべてのフィールドを任意に設定（JavaScriptで動的に制御）
        for field_name in self.fields:
            self.fields[field_name].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        # 各チェックボックスがTrueの場合、対応する詳細が必須
        if cleaned_data.get('direct_employment_request') and not cleaned_data.get('direct_employment_detail'):
            self.add_error('direct_employment_detail', '派遣先への直接雇用の依頼をチェックした場合は、詳細を入力してください。')
        
        if cleaned_data.get('new_dispatch_offer') and not cleaned_data.get('new_dispatch_detail'):
            self.add_error('new_dispatch_detail', '新たな派遣先の提供をチェックした場合は、詳細を入力してください。')
        
        if cleaned_data.get('indefinite_employment') and not cleaned_data.get('indefinite_employment_detail'):
            self.add_error('indefinite_employment_detail', '派遣元での無期雇用化をチェックした場合は、詳細を入力してください。')
        
        if cleaned_data.get('other_measures') and not cleaned_data.get('other_measures_detail'):
            self.add_error('other_measures_detail', 'その他の雇用安定措置をチェックした場合は、詳細を入力してください。')
        
        return cleaned_data


class ContractClientFlagForm(forms.ModelForm):
    """クライアント契約フラッグフォーム"""
    client_contract = forms.ModelChoiceField(
        queryset=None,
        label='クライアント契約',
        required=True,
        widget=forms.HiddenInput()
    )
    company_department = forms.ModelChoiceField(
        queryset=None,
        label='会社組織',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    company_user = forms.ModelChoiceField(
        queryset=None,
        label='会社担当者',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    flag_status = forms.ModelChoiceField(
        queryset=None,
        label='フラッグステータス',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    class Meta:
        model = ContractClientFlag
        fields = ['client_contract', 'company_department', 'company_user', 'flag_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.common.middleware import get_current_tenant_id

        tenant_id = get_current_tenant_id()
        if tenant_id:
            self.fields['client_contract'].queryset = ClientContract.objects.filter(tenant_id=tenant_id)
            self.fields['company_department'].queryset = CompanyDepartment.objects.filter(tenant_id=tenant_id)
            self.fields['company_user'].queryset = CompanyUser.objects.filter(tenant_id=tenant_id)
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(tenant_id=tenant_id, is_active=True).order_by('display_order')
        else:
            self.fields['client_contract'].queryset = ClientContract.objects.all()
            self.fields['company_department'].queryset = CompanyDepartment.objects.all()
            self.fields['company_user'].queryset = CompanyUser.objects.all()
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(is_active=True).order_by('display_order')


class ContractStaffFlagForm(forms.ModelForm):
    """スタッフ契約フラッグフォーム"""
    staff_contract = forms.ModelChoiceField(
        queryset=None,
        label='スタッフ契約',
        required=True,
        widget=forms.HiddenInput()
    )
    company_department = forms.ModelChoiceField(
        queryset=None,
        label='会社組織',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    company_user = forms.ModelChoiceField(
        queryset=None,
        label='会社担当者',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    flag_status = forms.ModelChoiceField(
        queryset=None,
        label='フラッグステータス',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    class Meta:
        model = ContractStaffFlag
        fields = ['staff_contract', 'company_department', 'company_user', 'flag_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.common.middleware import get_current_tenant_id

        tenant_id = get_current_tenant_id()
        if tenant_id:
            self.fields['staff_contract'].queryset = StaffContract.objects.filter(tenant_id=tenant_id)
            self.fields['company_department'].queryset = CompanyDepartment.objects.filter(tenant_id=tenant_id)
            self.fields['company_user'].queryset = CompanyUser.objects.filter(tenant_id=tenant_id)
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(tenant_id=tenant_id, is_active=True).order_by('display_order')
        else:
            self.fields['staff_contract'].queryset = StaffContract.objects.all()
            self.fields['company_department'].queryset = CompanyDepartment.objects.all()
            self.fields['company_user'].queryset = CompanyUser.objects.all()
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(is_active=True).order_by('display_order')
