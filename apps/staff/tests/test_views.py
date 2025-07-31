from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffContacted
from apps.system.dropdowns.models import Dropdowns
from datetime import date

User = get_user_model()

class StaffViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # StaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Staff)
        # 必要な権限をユーザーに付与
        self.view_staff_permission = Permission.objects.get(codename='view_staff', content_type=content_type)
        self.add_staff_permission = Permission.objects.get(codename='add_staff', content_type=content_type)
        self.change_staff_permission = Permission.objects.get(codename='change_staff', content_type=content_type)
        self.delete_staff_permission = Permission.objects.get(codename='delete_staff', content_type=content_type)

        self.user.user_permissions.add(self.view_staff_permission)
        self.user.user_permissions.add(self.add_staff_permission)
        self.user.user_permissions.add(self.change_staff_permission)
        self.user.user_permissions.add(self.delete_staff_permission)

        # StaffContactedモデルのContentTypeを取得
        contacted_content_type = ContentType.objects.get_for_model(StaffContacted)
        self.view_staffcontacted_permission = Permission.objects.get(codename='view_staffcontacted', content_type=contacted_content_type)
        self.add_staffcontacted_permission = Permission.objects.get(codename='add_staffcontacted', content_type=contacted_content_type)
        self.change_staffcontacted_permission = Permission.objects.get(codename='change_staffcontacted', content_type=contacted_content_type)
        self.delete_staffcontacted_permission = Permission.objects.get(codename='delete_staffcontacted', content_type=contacted_content_type)

        self.user.user_permissions.add(self.view_staffcontacted_permission)
        self.user.user_permissions.add(self.add_staffcontacted_permission)
        self.user.user_permissions.add(self.change_staffcontacted_permission)
        self.user.user_permissions.add(self.delete_staffcontacted_permission)

        # Create necessary Dropdowns for StaffForm
        Dropdowns.objects.create(category='sex', value='1', name='男性', active=True, disp_seq=1)
        Dropdowns.objects.create(category='sex', value='2', name='女性', active=True, disp_seq=2)
        Dropdowns.objects.create(category='regist_form', value='1', name='正社員', active=True, disp_seq=1)
        Dropdowns.objects.create(category='regist_form', value='2', name='契約社員', active=True, disp_seq=2)
        # Create necessary Dropdowns for StaffContactedForm
        Dropdowns.objects.create(category='contact_type', value='1', name='電話', active=True, disp_seq=1)
        Dropdowns.objects.create(category='contact_type', value='2', name='メール', active=True, disp_seq=2)

        self.staff_obj = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            name_kana_last='テスト',
            name_kana_first='スタッフ',
            birth_date=date(1990, 1, 1),
            sex=1,
            regist_form_code=1,
            employee_no='ZEMP000', # ソート順で最後にくるように変更
            email='test@example.com',
            address1='テスト住所', # address1を追加
            age=10 # ageを10に変更
        )
        # ソートテスト用のスタッフデータを作成 (12件)
        for i in range(1, 13):
            Staff.objects.create(
                name_last=f'Staff {i:02d}',
                name_first='Test',
                name_kana_last=f'スタッフ{i:02d}',
                name_kana_first='テスト',
                birth_date=date(1990, 1, 1),
                sex=1,
                regist_form_code=1,
                employee_no=f'EMP{i:03d}',
                email=f'staff{i:02d}@example.com',
                address1=f'住所{i:02d}',
                age=20 + i
            )

    def test_staff_list_view(self):
        response = self.client.get(reverse('staff_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_list.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_create_view_get(self):
        response = self.client.get(reverse('staff_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_form.html')

    def test_staff_create_view_post(self):
        data = {
            'name_last': '新規',
            'name_first': 'スタッフ',
            'name_kana_last': 'シンキ',
            'name_kana_first': 'スタッフ',
            'birth_date': '1995-05-05',
            'sex': 2,
            'regist_form_code': 2,
            'employee_no': 'EMP002',
            'email': 'newstaff@example.com'
        }
        response = self.client.post(reverse('staff_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_list
        self.assertTrue(Staff.objects.filter(name_last='新規', name_first='スタッフ').exists())

    def test_staff_detail_view(self):
        response = self.client.get(reverse('staff_detail', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_detail.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_update_view_get(self):
        response = self.client.get(reverse('staff_update', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_form.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_update_view_post(self):
        data = {
            'name_last': '更新',
            'name_first': 'スタッフ',
            'name_kana_last': 'コウシン',
            'name_kana_first': 'スタッフ',
            'birth_date': '1990-01-01',
            'sex': 1,
            'regist_form_code': 1,
            'employee_no': 'EMP001',
            'email': 'test@example.com'
        }
        response = self.client.post(reverse('staff_update', args=[self.staff_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        self.staff_obj.refresh_from_db()
        self.assertEqual(self.staff_obj.name_last, '更新')

    def test_staff_delete_view_get(self):
        response = self.client.get(reverse('staff_delete', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_confirm_delete.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')

    def test_staff_delete_view_post(self):
        response = self.client.post(reverse('staff_delete', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to staff_list
        self.assertFalse(Staff.objects.filter(pk=self.staff_obj.pk).exists())

    def test_staff_contacted_create_view_get(self):
        response = self.client.get(reverse('staff_contacted_create', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_form.html')

    def test_staff_contacted_create_view_post(self):
        data = {
            'content': 'テスト連絡',
            'detail': 'これはテスト連絡の詳細です。',
            'contact_type': 1,
        }
        response = self.client.post(reverse('staff_contacted_create', args=[self.staff_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        self.assertTrue(StaffContacted.objects.filter(staff=self.staff_obj, content='テスト連絡').exists())

    def test_staff_contacted_list_view(self):
        StaffContacted.objects.create(staff=self.staff_obj, content='連絡1')
        StaffContacted.objects.create(staff=self.staff_obj, content='連絡2')
        response = self.client.get(reverse('staff_contacted_list', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_list.html')
        self.assertContains(response, '連絡1')
        self.assertContains(response, '連絡2')

    def test_staff_contacted_detail_view(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='詳細テスト連絡', detail='詳細')
        response = self.client.get(reverse('staff_contacted_detail', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_detail.html')
        self.assertContains(response, '詳細')

    def test_staff_contacted_update_view_get(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='元の連絡')
        response = self.client.get(reverse('staff_contacted_update', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_form.html')
        self.assertContains(response, '元の連絡')

    def test_staff_contacted_update_view_post(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='元の連絡')
        data = {
            'content': '更新された連絡',
            'detail': '更新された連絡の詳細です。',
            'contact_type': 2,
        }
        response = self.client.post(reverse('staff_contacted_update', args=[contacted_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to staff_detail
        contacted_obj.refresh_from_db()
        self.assertEqual(contacted_obj.content, '更新された連絡')

    def test_staff_contacted_delete_view_get(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='削除テスト連絡')
        response = self.client.get(reverse('staff_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_contacted_confirm_delete.html')
        self.assertContains(response, '削除テスト連絡')

    def test_staff_contacted_delete_view_post(self):
        contacted_obj = StaffContacted.objects.create(staff=self.staff_obj, content='削除テスト連絡')
        response = self.client.post(reverse('staff_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to staff_list
        self.assertFalse(StaffContacted.objects.filter(pk=contacted_obj.pk).exists())

    def test_staff_change_history_list_view(self):
        response = self.client.get(reverse('staff_change_history_list', args=[self.staff_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_change_history_list.html')
        self.assertContains(response, 'テスト')
        self.assertContains(response, 'スタッフ')