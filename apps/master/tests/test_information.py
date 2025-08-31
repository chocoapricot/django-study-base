from django.test import TestCase, Client as TestClient
from unittest.mock import patch
from django.test import TestCase, Client as TestClient
from django.urls import reverse
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.master.models import Information, InformationFile
from apps.company.models import Company
from apps.master.forms import InformationForm

User = get_user_model()

class InformationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )

    @patch('django_currentuser.middleware.get_current_user')
    def test_information_creation(self, mock_get_current_user):
        """お知らせ作成テスト"""
        mock_get_current_user.return_value = self.user
        information = Information.objects.create(
            subject='Test Subject',
            content='Test Content',
            corporation_number=self.company.corporate_number
        )

        self.assertEqual(information.subject, 'Test Subject')
        self.assertEqual(information.corporation_number, '1234567890123')
        self.assertEqual(str(information), 'Test Subject')
        self.assertEqual(information.created_by, self.user)


class InformationFormTest(TestCase):
    def test_information_form_valid(self):
        """お知らせフォーム有効データテスト"""
        form_data = {
            'target': 'company',
            'subject': 'Test Subject',
            'content': 'Test Content',
        }
        form = InformationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_information_form_required_fields(self):
        """お知らせフォーム必須フィールドテスト"""
        form = InformationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('subject', form.errors)
        self.assertIn('content', form.errors)


class InformationViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=[
                'add_information', 'view_information',
                'change_information', 'delete_information'
            ]
        )
        self.user.user_permissions.set(permissions)

        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )

        with patch('django_currentuser.middleware.get_current_user') as mock_get_current_user:
            mock_get_current_user.return_value = self.user
            self.information = Information.objects.create(
                subject='Test Subject',
                content='Test Content',
                corporation_number=self.company.corporate_number
            )
        self.test_client = TestClient()
        self.test_client.login(username='testuser', password='testpass123')

    def test_information_list_view(self):
        """お知らせ一覧ビューのテスト"""
        response = self.test_client.get(reverse('master:information_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Subject')

    def test_information_detail_view(self):
        """お知らせ詳細ビューのテスト"""
        response = self.test_client.get(
            reverse('master:information_detail', kwargs={'pk': self.information.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Subject')

    def test_information_create_view(self):
        """お知らせ作成ビューのテスト"""
        response = self.test_client.get(reverse('master:information_create'))
        self.assertEqual(response.status_code, 200)

    def test_information_create_post(self):
        """お知らせ作成POSTのテスト"""
        form_data = {
            'target': 'staff',
            'subject': 'New Information',
            'content': 'This is a new information.',
        }

        response = self.test_client.post(
            reverse('master:information_create'),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        new_info = Information.objects.get(subject='New Information')
        self.assertEqual(new_info.corporation_number, self.company.corporate_number)

    def test_information_update_view(self):
        """お知らせ更新ビューのテスト"""
        response = self.test_client.get(
            reverse('master:information_update', kwargs={'pk': self.information.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_information_update_post(self):
        """お知らせ更新POSTのテスト"""
        form_data = {
            'target': 'client',
            'subject': 'Updated Subject',
            'content': 'Updated Content',
        }

        response = self.test_client.post(
            reverse('master:information_update', kwargs={'pk': self.information.pk}),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.information.refresh_from_db()
        self.assertEqual(self.information.subject, 'Updated Subject')

    def test_information_delete_view(self):
        """お知らせ削除ビューのテスト"""
        response = self.test_client.get(
            reverse('master:information_delete', kwargs={'pk': self.information.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_information_delete_post(self):
        """お知らせ削除POSTのテスト"""
        response = self.test_client.post(
            reverse('master:information_delete', kwargs={'pk': self.information.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Information.objects.filter(pk=self.information.pk).exists()
        )

    def test_information_create_with_files(self):
        """お知らせ作成（ファイル添付あり）のテスト"""
        file1 = SimpleUploadedFile("file1.txt", b"content1")
        file2 = SimpleUploadedFile("file2.txt", b"content2")
        
        form_data = {
            'target': 'company',
            'subject': 'New Info with Files',
            'content': 'Some content',
        }

        response = self.test_client.post(reverse('master:information_create'), {
            **form_data,
            'attachments': [file1, file2]
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Information.objects.count(), 2) # including self.information
        new_info = Information.objects.get(subject='New Info with Files')
        self.assertEqual(new_info.files.count(), 2)
        
        for f in new_info.files.all():
            f.delete()

    def test_information_update_with_files(self):
        """お知らせ更新（ファイル追加・削除）のテスト"""
        file1 = SimpleUploadedFile("file1.txt", b"content1")
        info_file1 = InformationFile.objects.create(information=self.information, file=file1)

        file2 = SimpleUploadedFile("file2.txt", b"content2")
        
        form_data = {
            'target': 'company',
            'subject': 'Updated Subject',
            'content': 'Updated content',
            'delete_attachments': [info_file1.pk]
        }

        response = self.test_client.post(
            reverse('master:information_update', kwargs={'pk': self.information.pk}), {
            **form_data,
            'attachments': [file2]
        })

        self.assertEqual(response.status_code, 302)
        self.information.refresh_from_db()
        self.assertEqual(self.information.subject, 'Updated Subject')
        self.assertEqual(self.information.files.count(), 1)
        self.assertEqual(self.information.files.first().filename, 'file2.txt')
        
        self.assertFalse(os.path.exists(info_file1.file.path))

        for f in self.information.files.all():
            f.delete()
