from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from apps.master.models import StaffTag

User = get_user_model()

class StaffTagSearchTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        # StaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Staff)
        # 必要な権限をユーザーに付与
        self.user.user_permissions.add(Permission.objects.get(codename='view_staff', content_type=content_type))

        # タグを作成
        self.tag1 = StaffTag.objects.create(name='タグ1', display_order=1)
        self.tag2 = StaffTag.objects.create(name='タグ2', display_order=2)

        # スタッフを作成
        self.staff1 = Staff.objects.create(name_last='田中', name_first='太郎')
        self.staff1.tags.add(self.tag1)

        self.staff2 = Staff.objects.create(name_last='佐藤', name_first='花子')
        self.staff2.tags.add(self.tag2)

        self.staff3 = Staff.objects.create(name_last='鈴木', name_first='次郎')
        self.staff3.tags.add(self.tag1, self.tag2)

        self.staff4 = Staff.objects.create(name_last='伊藤', name_first='健')
        # 伊藤にはタグなし

    def test_staff_list_filter_by_tag(self):
        """タグでの絞り込み機能をテスト"""
        # 1. タグ1で絞り込み
        response = self.client.get(reverse('staff:staff_list'), {'tag': self.tag1.pk})
        self.assertEqual(response.status_code, 200)
        staffs = response.context['staffs'].object_list
        self.assertEqual(len(staffs), 2)
        self.assertIn(self.staff1, staffs)
        self.assertIn(self.staff3, staffs)
        self.assertNotIn(self.staff2, staffs)
        self.assertNotIn(self.staff4, staffs)

        # 2. タグ2で絞り込み
        response = self.client.get(reverse('staff:staff_list'), {'tag': self.tag2.pk})
        self.assertEqual(response.status_code, 200)
        staffs = response.context['staffs'].object_list
        self.assertEqual(len(staffs), 2)
        self.assertIn(self.staff2, staffs)
        self.assertIn(self.staff3, staffs)
        self.assertNotIn(self.staff1, staffs)
        self.assertNotIn(self.staff4, staffs)

        # 3. タグフィルターなし（全て表示）
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        staffs = response.context['staffs'].object_list
        self.assertEqual(len(staffs), 4)

    def test_staff_export_filter_by_tag(self):
        """エクスポートでのタグ絞り込み機能をテスト"""
        # 1. タグ1でエクスポート (CSV)
        response = self.client.get(reverse('staff:staff_export'), {'tag': self.tag1.pk, 'format': 'csv'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode('utf-8')
        self.assertIn('田中', content)
        self.assertIn('鈴木', content)
        self.assertNotIn('佐藤', content)
        self.assertNotIn('伊藤', content)
