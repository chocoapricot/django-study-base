from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import MyUser
from apps.information.models import InformationFromCompany
from apps.company.models import Company

class InformationViewsTest(TestCase):

    def setUp(self):
        """テストのセットアップ"""
        self.client = Client()
        self.user = MyUser.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Company is needed for corporate_number
        self.company = Company.objects.create(
            name="Test Company",
            corporate_number="1234567890123"
        )

        self.info = InformationFromCompany.objects.create(
            title="Test Info",
            content="Test Content",
            corporate_number=self.company.corporate_number
        )

    def test_information_list_view(self):
        """お知らせ一覧ページの表示をテストします。"""
        response = self.client.get(reverse('information:information_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.info.title)

    def test_information_detail_view(self):
        """お知らせ詳細ページの表示をテストします。"""
        response = self.client.get(reverse('information:information_detail', args=[self.info.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.info.title)

    def test_information_create_view_get(self):
        """お知らせ作成ページのGETリクエストをテストします。"""
        response = self.client.get(reverse('information:information_create'))
        self.assertEqual(response.status_code, 200)

    def test_information_create_view_post(self):
        """お知らせ作成ページのPOSTリクエストをテストします。"""
        data = {
            'title': 'New Info',
            'content': 'New Content',
            'target': 'client',
        }
        response = self.client.post(reverse('information:information_create'), data)
        self.assertEqual(response.status_code, 302) # Redirect on success
        self.assertTrue(InformationFromCompany.objects.filter(title='New Info').exists())
        new_info = InformationFromCompany.objects.get(title='New Info')
        self.assertEqual(new_info.corporate_number, self.company.corporate_number)

    def test_information_update_view(self):
        """お知らせ更新ページのPOSTリクエストをテストします。"""
        data = {
            'title': 'Updated Info',
            'content': 'Updated Content',
            'target': 'company',
        }
        response = self.client.post(reverse('information:information_update', args=[self.info.pk]), data)
        self.assertEqual(response.status_code, 302) # Redirect on success
        self.info.refresh_from_db()
        self.assertEqual(self.info.title, 'Updated Info')

    def test_information_delete_view(self):
        """お知らせ削除ページのPOSTリクエストをテストします。"""
        response = self.client.post(reverse('information:information_delete', args=[self.info.pk]))
        self.assertEqual(response.status_code, 302) # Redirect on success
        self.assertFalse(InformationFromCompany.objects.filter(pk=self.info.pk).exists())
