from import_export import resources, fields
from .models import Staff
from apps.system.settings.models import Dropdowns
from apps.company.models import CompanyDepartment
from apps.master.models import StaffRegistStatus
from django.utils import timezone

class StaffResource(resources.ModelResource):
    """スタッフデータのエクスポート用リソース"""

    regist_status_display = fields.Field(
        column_name='登録区分',
        attribute='regist_status__name',
        readonly=True
    )
    employment_type_display = fields.Field(
        column_name='雇用形態',
        attribute='employment_type',
        readonly=True
    )
    department_display = fields.Field(
        column_name='所属部署',
        attribute='department_code',
        readonly=True
    )
    sex_display = fields.Field(
        column_name='性別',
        attribute='sex',
        readonly=True
    )

    class Meta:
        model = Staff
        fields = (
            'id',
            'employee_no',
            'name_last',
            'name_first',
            'name_kana_last',
            'name_kana_first',
            'birth_date',
            'age',
            'sex_display',
            'postal_code',
            'address1',
            'address2',
            'address3',
            'phone',
            'email',
            'hire_date',
            'resignation_date',
            'regist_status_display',
            'employment_type_display',
            'department_display',
            'memo',
            'created_at',
            'updated_at',
        )
        export_order = fields

    def dehydrate_regist_status_display(self, staff):
        """登録区分の表示名を取得"""
        if staff.regist_status:
            return staff.regist_status.name
        return ''

    def dehydrate_employment_type_display(self, staff):
        """雇用形態の表示名を取得"""
        if staff.employment_type:
            return staff.employment_type.name
        return ''

    def dehydrate_department_display(self, staff):
        """所属部署の表示名を取得"""
        if staff.department_code:
            try:
                current_date = timezone.localdate()
                department = CompanyDepartment.get_valid_departments(current_date).get(
                    department_code=staff.department_code
                )
                return department.name
            except CompanyDepartment.DoesNotExist:
                return f"部署コード: {staff.department_code} (無効)"
        return ''

    def dehydrate_sex_display(self, staff):
        """性別の表示名を取得"""
        if staff.sex:
            try:
                dropdown = Dropdowns.objects.get(
                    category='sex',
                    value=staff.sex,
                    active=True
                )
                return dropdown.name
            except Dropdowns.DoesNotExist:
                return str(staff.sex)
        return ''
