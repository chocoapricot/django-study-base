from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.staff.models import Staff, StaffDisability
from apps.system.settings.models import Dropdowns
from datetime import date

User = get_user_model()

class StaffDisabilityViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # StaffDisabilityモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(StaffDisability)
        # 必要な権限をユーザーに付与
        self.view_perm = Permission.objects.get(codename='view_staffdisability', content_type=content_type)
        self.add_perm = Permission.objects.get(codename='add_staffdisability', content_type=content_type)
        self.change_perm = Permission.objects.get(codename='change_staffdisability', content_type=content_type)
        self.delete_perm = Permission.objects.get(codename='delete_staffdisability', content_type=content_type)

        staff_content_type = ContentType.objects.get_for_model(Staff)
        self.view_staff_perm = Permission.objects.get(codename='view_staff', content_type=staff_content_type)


        self.user.user_permissions.add(self.view_perm, self.add_perm, self.change_perm, self.delete_perm, self.view_staff_perm)

        # テスト用Dropdownsデータを作成
        self.disability_type1 = Dropdowns.objects.create(category='disability_type', value='1', name='視覚障害', disp_seq=1)
        self.disability_type2 = Dropdowns.objects.create(category='disability_type', value='2', name='聴覚障害', disp_seq=2)
        self.disability_type3 = Dropdowns.objects.create(category='disability_type', value='3', name='肢体不自由', disp_seq=3)
        self.disability_type4 = Dropdowns.objects.create(category='disability_type', value='4', name='内部障害', disp_seq=4)
        self.disability_type5 = Dropdowns.objects.create(category='disability_type', value='5', name='精神障害', disp_seq=5)
        self.disability_type6 = Dropdowns.objects.create(category='disability_type', value='6', name='知的障害', disp_seq=6)

        # テスト用スタッフデータを作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            birth_date=date(1990, 1, 1),
            sex=1,
        )

    def test_disability_create_view_get(self):
        """登録画面へのGETリクエストが成功することをテスト"""
        response = self.client.get(reverse('staff:staff_disability_create', kwargs={'staff_pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_disability_form.html')

    def test_disability_create_view_post(self):
        """登録処理が成功することをテスト"""
        data = {
            'disability_type': self.disability_type1.value,
            'severity': '1級',
        }
        response = self.client.post(reverse('staff:staff_disability_create', kwargs={'staff_pk': self.staff.pk}), data)
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        self.assertTrue(StaffDisability.objects.filter(staff=self.staff).exists())
        disability = StaffDisability.objects.get(staff=self.staff)
        self.assertEqual(disability.disability_type, self.disability_type1.value)
        self.assertEqual(disability.severity, '1級')

    def test_disability_detail_view(self):
        """詳細画面へのGETリクエストが成功することをテスト"""
        disability = StaffDisability.objects.create(
            staff=self.staff,
            disability_type=self.disability_type2.value,
            severity='2級'
        )
        response = self.client.get(reverse('staff:staff_disability_detail', kwargs={'staff_pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_disability_detail.html')
        self.assertContains(response, self.disability_type2.name)
        self.assertContains(response, '2級')

    def test_disability_edit_view_get(self):
        """編集画面へのGETリクエストが成功することをテスト"""
        disability = StaffDisability.objects.create(
            staff=self.staff,
            disability_type=self.disability_type3.value,
            severity='3級'
        )
        response = self.client.get(reverse('staff:staff_disability_edit', kwargs={'staff_pk': self.staff.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/staff_disability_form.html')
        self.assertContains(response, self.disability_type3.name)
        self.assertContains(response, f'value="{disability.severity}"')
        self.assertContains(response, f'value="{disability.disability_type}" checked')


    def test_disability_edit_view_post(self):
        """更新処理が成功することをテスト"""
        disability = StaffDisability.objects.create(
            staff=self.staff,
            disability_type=self.disability_type4.value,
            severity='4級'
        )
        data = {
            'disability_type': self.disability_type5.value,
            'severity': '1級',
        }
        response = self.client.post(reverse('staff:staff_disability_edit', kwargs={'staff_pk': self.staff.pk}), data)
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        disability.refresh_from_db()
        self.assertEqual(disability.disability_type, self.disability_type5.value)
        self.assertEqual(disability.severity, '1級')

    def test_disability_delete_view_post(self):
        """削除処理が成功することをテスト"""
        disability = StaffDisability.objects.create(
            staff=self.staff,
            disability_type=self.disability_type6.value,
            severity='A'
        )
        response = self.client.post(reverse('staff:staff_disability_delete', kwargs={'staff_pk': self.staff.pk}))
        self.assertEqual(response.status_code, 302) # スタッフ詳細ページへリダイレクト
        self.assertFalse(StaffDisability.objects.filter(pk=disability.pk).exists())