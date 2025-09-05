from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import MailTemplate
from django.contrib.auth.models import Permission

User = get_user_model()


class MailTemplateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Grant permissions
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=[
                'view_mailtemplate',
                'change_mailtemplate',
            ]
        )
        self.user.user_permissions.set(permissions)

        self.client = TestClient()
        self.client.login(username='testuser', password='testpass123')

        self.template = MailTemplate.objects.create(
            name='テストテンプレート',
            template_key='test_template',
            subject='Test Subject',
            body='Test Body'
        )

    def test_mail_template_list_view(self):
        """Test the list view."""
        response = self.client.get(reverse('master:mail_template_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.name)
        self.assertNotContains(response, '新規作成')

    def test_mail_template_detail_view(self):
        """Test the detail view."""
        response = self.client.get(reverse('master:mail_template_detail', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.subject)
        self.assertNotContains(response, 'delete/')

    def test_mail_template_update_view(self):
        """Test the update view (GET)."""
        response = self.client.get(reverse('master:mail_template_update', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 200)

    def test_mail_template_update_post(self):
        """Test the update view (POST)."""
        data = {
            'subject': 'Updated Subject',
            'body': 'Updated Body',
            'remarks': 'Updated remarks.'
        }
        response = self.client.post(reverse('master:mail_template_update', kwargs={'pk': self.template.pk}), data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.template.refresh_from_db()
        self.assertEqual(self.template.subject, 'Updated Subject')
        self.assertEqual(self.template.body, 'Updated Body')

    def test_create_view_is_removed(self):
        """Test that the create view returns 404."""
        with self.assertRaises(Exception):
            reverse('master:mail_template_create')

    def test_delete_view_is_removed(self):
        """Test that the delete view returns 404."""
        with self.assertRaises(Exception):
            reverse('master:mail_template_delete', kwargs={'pk': self.template.pk})
