from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models_staff import Staff, StaffGrade
from apps.company.models import Company
from datetime import date, timedelta
from django.utils import timezone
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class StaffGradeBoldTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        if not self.company.tenant_id:
            self.company.tenant_id = 1
            self.company.save()
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)

        # Grant permissions
        content_type = ContentType.objects.get_for_model(Staff)
        permissions = Permission.objects.filter(content_type=content_type)
        for perm in permissions:
            self.user.user_permissions.add(perm)

        self.client.login(username='testuser', password='testpassword')

        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
            employee_no='EMP001',
            hire_date=date(2020, 4, 1)
        )

        today = timezone.localdate()

        # Past grade
        self.grade_past = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G1',
            valid_from=today - timedelta(days=60),
            valid_to=today - timedelta(days=31)
        )

        # Current grade
        self.grade_current = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G2',
            valid_from=today - timedelta(days=30),
            valid_to=today + timedelta(days=30)
        )

        # Future grade
        self.grade_future = StaffGrade.objects.create(
            staff=self.staff,
            grade_code='G3',
            valid_from=today + timedelta(days=31),
            valid_to=today + timedelta(days=60)
        )

    def test_current_grade_is_bolded(self):
        # We need to set tenant ID again because middleware might clear it in some environments
        # though standard TestCase should handle it if set in setUp.
        # But for MyTenantModel.save() it's better to be sure.
        set_current_tenant_id(self.company.tenant_id)

        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # After change, G2 should have fw-bold in the history list
        # We search for G2 in the history section.
        # The history section starts with "等級履歴（最新5件）"

        history_start = content.find("等級履歴（最新5件）")
        self.assertNotEqual(history_start, -1)
        history_content = content[history_start:]

        # G2 should be present
        self.assertIn('G2', history_content)
        # And bolded with fw-bold class
        # Check specifically for G2's span
        self.assertIn('class="ms-1 fw-bold">G2', history_content)

        # Also verify G1 and G3 are NOT bolded
        # G3 (future)
        self.assertIn('G3', history_content)
        # Check that G3 is not bolded
        self.assertIn('class="ms-1 ">G3', history_content)
        # Check that G1 is not bolded
        self.assertIn('class="ms-1 ">G1', history_content)
