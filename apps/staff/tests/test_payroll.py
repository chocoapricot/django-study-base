from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffPayroll
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from datetime import date

User = get_user_model()

class StaffPayrollViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        content_type = ContentType.objects.get_for_model(StaffPayroll)
        self.view_perm = Permission.objects.get(codename='view_staffpayroll', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_staffpayroll', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_staffpayroll', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_staffpayroll', content_type=content_type)

        staff_content_type = ContentType.objects.get_for_model(Staff)
        self.view_staff_perm = Permission.objects.get(codename='view_staff', content_type=staff_content_type)

        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm, self.view_staff_perm)

        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
        )

    def test_staff_payroll_create_view_get(self):
        response = self.client.get(reverse('staff:staff_payroll_create', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_form.html')

    def test_staff_payroll_create_view_post(self):
        data = {
            'health_insurance_join_date': '2022-01-01',
            'welfare_pension_join_date': '2022-01-01',
            'employment_insurance_join_date': '2022-01-01',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffPayroll.objects.filter(staff=self.staff).exists())

    def test_staff_payroll_detail_view(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_detail.html')
        self.assertContains(response, reverse('staff:staff_payroll_edit', args=[self.staff.pk]))

    def test_staff_payroll_edit_view_get(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_edit', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_form.html')

    def test_staff_payroll_edit_view_post(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        data = {
            'health_insurance_join_date': '2023-01-01',
            'pension_insurance_non_enrollment_reason': '年金制度対象外',
            'employment_insurance_non_enrollment_reason': '短期雇用のため対象外',
        }
        response = self.client.post(reverse('staff:staff_payroll_edit', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)
        payroll.refresh_from_db()
        self.assertEqual(payroll.health_insurance_join_date, date(2023, 1, 1))

    def test_staff_payroll_delete_view_get(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.get(reverse('staff:staff_payroll_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_payroll_confirm_delete.html')

    def test_staff_payroll_delete_view_post(self):
        payroll = StaffPayroll.objects.create(staff=self.staff)
        response = self.client.post(reverse('staff:staff_payroll_delete', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffPayroll.objects.filter(staff=self.staff).exists())

    def test_staff_payroll_validation_date_and_reason_both_provided(self):
        """日付と非加入理由の両方が入力された場合のバリデーションエラーテスト"""
        data = {
            'health_insurance_join_date': '2022-01-01',
            'health_insurance_non_enrollment_reason': '他の保険に加入済み',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        self.assertContains(response, '健康保険の加入日が入力されている場合、非加入理由は入力できません。')

    def test_staff_payroll_validation_neither_date_nor_reason(self):
        """日付も非加入理由も入力されていない場合のバリデーションエラーテスト"""
        data = {
            # 健康保険の日付も理由も入力しない
            'welfare_pension_join_date': '2022-01-01',
            'employment_insurance_join_date': '2022-01-01',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        self.assertContains(response, '健康保険の加入日または非加入理由のいずれかを入力してください。')

    def test_staff_payroll_validation_multiple_insurance_errors(self):
        """複数の保険でバリデーションエラーが発生する場合のテスト"""
        data = {
            'health_insurance_join_date': '2022-01-01',
            'health_insurance_non_enrollment_reason': '他の保険に加入済み',
            'welfare_pension_join_date': '2022-01-01',
            'pension_insurance_non_enrollment_reason': '年金制度対象外',
            # 雇用保険は日付も理由も入力しない
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        # 複数のエラーメッセージが含まれることを確認（順序は問わない）
        response_content = response.content.decode('utf-8')
        self.assertIn('健康保険の加入日が入力されている場合、非加入理由は入力できません。', response_content)
        self.assertIn('厚生年金の加入日が入力されている場合、非加入理由は入力できません。', response_content)
        self.assertIn('雇用保険の加入日または非加入理由のいずれかを入力してください。', response_content)

    def test_staff_payroll_validation_valid_date_only(self):
        """加入日のみ入力された場合の正常ケーステスト"""
        data = {
            'health_insurance_join_date': '2022-01-01',
            'welfare_pension_join_date': '2022-01-01',
            'employment_insurance_join_date': '2022-01-01',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)  # 正常に登録されてリダイレクト
        self.assertTrue(StaffPayroll.objects.filter(staff=self.staff).exists())

    def test_staff_payroll_validation_valid_reason_only(self):
        """非加入理由のみ入力された場合の正常ケーステスト"""
        data = {
            'health_insurance_non_enrollment_reason': '他の保険に加入済み',
            'pension_insurance_non_enrollment_reason': '年金制度対象外',
            'employment_insurance_non_enrollment_reason': '短期雇用のため対象外',
        }
        response = self.client.post(reverse('staff:staff_payroll_create', args=[self.staff.pk]), data)
        self.assertEqual(response.status_code, 302)  # 正常に登録されてリダイレクト
        self.assertTrue(StaffPayroll.objects.filter(staff=self.staff).exists())

from apps.staff.forms_payroll import StaffPayrollForm

class StaffPayrollFormTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
        )

    def test_form_validation_date_and_reason_both_provided(self):
        """日付と非加入理由の両方が入力された場合のフォームバリデーションテスト"""
        form_data = {
            'health_insurance_join_date': '2022-01-01',
            'health_insurance_non_enrollment_reason': '他の保険に加入済み',
        }
        form = StaffPayrollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('健康保険の加入日が入力されている場合、非加入理由は入力できません。', form.non_field_errors())

    def test_form_validation_neither_date_nor_reason(self):
        """日付も非加入理由も入力されていない場合のフォームバリデーションテスト"""
        form_data = {
            # 健康保険の日付も理由も入力しない
        }
        form = StaffPayrollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('健康保険の加入日または非加入理由のいずれかを入力してください。', form.non_field_errors())

    def test_form_validation_valid_date_only(self):
        """加入日のみ入力された場合の正常ケーステスト"""
        form_data = {
            'health_insurance_join_date': '2022-01-01',
            'welfare_pension_join_date': '2022-01-01',
            'employment_insurance_join_date': '2022-01-01',
        }
        form = StaffPayrollForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_validation_valid_reason_only(self):
        """非加入理由のみ入力された場合の正常ケーステスト"""
        form_data = {
            'health_insurance_non_enrollment_reason': '他の保険に加入済み',
            'pension_insurance_non_enrollment_reason': '年金制度対象外',
            'employment_insurance_non_enrollment_reason': '短期雇用のため対象外',
        }
        form = StaffPayrollForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_validation_mixed_valid_cases(self):
        """一部は日付、一部は理由を入力した混合ケーステスト"""
        form_data = {
            'health_insurance_join_date': '2022-01-01',
            'pension_insurance_non_enrollment_reason': '年金制度対象外',
            'employment_insurance_join_date': '2022-01-01',
        }
        form = StaffPayrollForm(data=form_data)
        self.assertTrue(form.is_valid())