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
                'add_mailtemplate', 'view_mailtemplate',
                'change_mailtemplate', 'delete_mailtemplate'
            ]
        )
        self.user.user_permissions.set(permissions)

        self.client = TestClient()
        self.client.login(username='testuser', password='testpass123')

        self.template = MailTemplate.objects.create(
            template_key='test_template',
            subject='Test Subject',
            body='Test Body'
        )

    def test_mail_template_list_view(self):
        """Test the list view."""
        response = self.client.get(reverse('master:mail_template_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.template_key)

    def test_mail_template_detail_view(self):
        """Test the detail view."""
        response = self.client.get(reverse('master:mail_template_detail', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.subject)

    def test_mail_template_create_view(self):
        """Test the create view (GET)."""
        response = self.client.get(reverse('master:mail_template_create'))
        self.assertEqual(response.status_code, 200)

    def test_mail_template_create_post(self):
        """Test the create view (POST)."""
        data = {
            'template_key': 'new_template',
            'subject': 'New Subject',
            'body': 'New Body'
        }
        response = self.client.post(reverse('master:mail_template_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(MailTemplate.objects.filter(template_key='new_template').exists())

    def test_mail_template_update_view(self):
        """Test the update view (GET)."""
        response = self.client.get(reverse('master:mail_template_update', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 200)

    def test_mail_template_update_post(self):
        """Test the update view (POST)."""
        data = {
            'template_key': 'updated_template',
            'subject': 'Updated Subject',
            'body': 'Updated Body'
        }
        response = self.client.post(reverse('master:mail_template_update', kwargs={'pk': self.template.pk}), data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.template.refresh_from_db()
        self.assertEqual(self.template.template_key, 'updated_template')

    def test_mail_template_delete_view(self):
        """Test the delete view (GET)."""
        response = self.client.get(reverse('master:mail_template_delete', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 200)

    def test_mail_template_delete_post(self):
        """Test the delete view (POST)."""
        response = self.client.post(reverse('master:mail_template_delete', kwargs={'pk': self.template.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertFalse(MailTemplate.objects.filter(pk=self.template.pk).exists())
