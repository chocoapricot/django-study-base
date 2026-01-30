from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.master.models import StaffTag
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class StaffListTagsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='passwordforstudybase!',
            tenant_id=self.company.tenant_id
        )
        self.client.login(email='admin@example.com', password='passwordforstudybase!')

        # タグを作成
        self.tag1 = StaffTag.objects.create(name='Tag1', display_order=1, is_active=True)
        self.tag2 = StaffTag.objects.create(name='Tag2', display_order=2, is_active=True)

        # スタッフを作成
        self.staff = Staff.objects.create(
            name_last='Tag',
            name_first='User',
            name_kana_last='タグ',
            name_kana_first='ユーザー',
            employee_no='TAG001'
        )
        self.staff.tags.add(self.tag1, self.tag2)

    def test_tags_displayed_in_list(self):
        """スタッフ一覧でタグが表示されることを確認"""
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)

        # スタッフ名が表示されていることを確認
        self.assertContains(response, 'Tag User')

        # タグ名が表示されていることを確認
        self.assertContains(response, 'Tag1')
        self.assertContains(response, 'Tag2')

        # 期待されるHTML構造（バッジ、アイコンなど）が含まれていることを確認
        self.assertContains(response, 'badge rounded-pill')
        self.assertContains(response, 'bi-tag-fill')
