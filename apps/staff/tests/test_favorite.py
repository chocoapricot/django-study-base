from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffFavorite
from apps.company.models import Company
from datetime import date
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class StaffFavoriteTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        # スレッドローカルにテナントIDをセット
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(username='testuser', password='testpassword', tenant_id=self.company.tenant_id)
        self.client.login(username='testuser', password='testpassword')

        # 権限付与
        content_type = ContentType.objects.get_for_model(Staff)
        self.user.user_permissions.add(Permission.objects.get(codename='view_staff', content_type=content_type))

        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,
            employee_no='EMP001',
            tenant_id=self.company.tenant_id
        )

    def test_favorite_add_view(self):
        """お気に入り追加ビューのテスト"""
        url = reverse('staff:staff_favorite_add', args=[self.staff.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffFavorite.objects.filter(staff=self.staff, user=self.user).exists())

    def test_favorite_remove_view(self):
        """お気に入り削除ビューのテスト"""
        StaffFavorite.objects.create(staff=self.staff, user=self.user, tenant_id=self.company.tenant_id)
        url = reverse('staff:staff_favorite_remove', args=[self.staff.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffFavorite.objects.filter(staff=self.staff, user=self.user).exists())

    def test_staff_list_favorite_annotation(self):
        """スタッフ一覧でお気に入り状況がアノテーションされているかテスト"""
        # ログインユーザーの会社設定が必要な場合があるため
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # お気に入りなし
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        staffs = response.context['staffs']
        self.assertFalse(staffs[0].is_favorite)

        # お気に入りあり
        StaffFavorite.objects.create(staff=self.staff, user=self.user, tenant_id=self.company.tenant_id)
        response = self.client.get(reverse('staff:staff_list'))
        self.assertEqual(response.status_code, 200)
        staffs = response.context['staffs']
        self.assertTrue(staffs[0].is_favorite)

    def test_staff_detail_favorite_context(self):
        """スタッフ詳細にお気に入り状況が含まれているかテスト"""
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # お気に入りなし
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get('is_favorite', False))
        self.assertContains(response, 'お気に入り追加')

        # お気に入りあり
        StaffFavorite.objects.create(staff=self.staff, user=self.user, tenant_id=self.company.tenant_id)
        response = self.client.get(reverse('staff:staff_detail', args=[self.staff.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('is_favorite', False))
        self.assertNotContains(response, 'お気に入り追加')
        self.assertContains(response, 'bi-star-fill')
        self.assertContains(response, 'お気に入り解除')
