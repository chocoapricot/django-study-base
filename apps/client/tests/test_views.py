from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.client.models import Client, ClientContacted
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()

class ClientViewsTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # ClientモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(Client)
        # 必要な権限をユーザーに付与
        self.view_client_permission = Permission.objects.get(codename='view_client', content_type=content_type)
        self.add_client_permission = Permission.objects.get(codename='add_client', content_type=content_type)
        self.change_client_permission = Permission.objects.get(codename='change_client', content_type=content_type)
        self.delete_client_permission = Permission.objects.get(codename='delete_client', content_type=content_type)

        self.user.user_permissions.add(self.view_client_permission)
        self.user.user_permissions.add(self.add_client_permission)
        self.user.user_permissions.add(self.change_client_permission)
        self.user.user_permissions.add(self.delete_client_permission)

        # ClientContactedモデルのContentTypeを取得
        contacted_content_type = ContentType.objects.get_for_model(ClientContacted)
        self.view_clientcontacted_permission = Permission.objects.get(codename='view_clientcontacted', content_type=contacted_content_type)
        self.add_clientcontacted_permission = Permission.objects.get(codename='add_clientcontacted', content_type=contacted_content_type)
        self.change_clientcontacted_permission = Permission.objects.get(codename='change_clientcontacted', content_type=contacted_content_type)
        self.delete_clientcontacted_permission = Permission.objects.get(codename='delete_clientcontacted', content_type=contacted_content_type)

        self.user.user_permissions.add(self.view_clientcontacted_permission)
        self.user.user_permissions.add(self.add_clientcontacted_permission)
        self.user.user_permissions.add(self.change_clientcontacted_permission)
        self.user.user_permissions.add(self.delete_clientcontacted_permission)

        from apps.system.dropdowns.models import Dropdowns
        # Create necessary Dropdowns for ClientForm
        Dropdowns.objects.create(category='regist_form_client', value='1', name='Test Regist Form', active=True, disp_seq=1)
        # Create necessary Dropdowns for ClientContactedForm
        Dropdowns.objects.create(category='contact_type', value='1', name='Test Contact Type 1', active=True, disp_seq=1)
        Dropdowns.objects.create(category='contact_type', value='2', name='Test Contact Type 2', active=True, disp_seq=2)

        self.client_obj = Client.objects.create(
            corporate_number='1234567890123',
            name='Test Client',
            name_furigana='テストクライアント',
            regist_form_client=1
        )

    def test_client_list_view(self):
        response = self.client.get(reverse('client:client_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_list.html')
        self.assertContains(response, 'Test Client')

    def test_client_create_view_get(self):
        response = self.client.get(reverse('client:client_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_form.html')

    def test_client_create_view_post(self):
        data = {
            'corporate_number': '9876543210987',
            'name': 'New Client',
            'name_furigana': 'ニュークライアントカキクケコ',
            'regist_form_client': 1
        }
        response = self.client.post(reverse('client:client_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_list
        self.assertTrue(Client.objects.filter(name='New Client').exists())

    def test_client_detail_view(self):
        response = self.client.get(reverse('client:client_detail', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_detail.html')
        self.assertContains(response, 'Test Client')

    def test_client_update_view_get(self):
        response = self.client.get(reverse('client:client_update', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_form.html')
        self.assertContains(response, 'Test Client')

    def test_client_update_view_post(self):
        data = {
            'corporate_number': self.client_obj.corporate_number, # corporate_numberはuniqueなので既存のものを利用
            'name': 'Updated Client',
            'name_furigana': 'アップデートクライアントサシスセソ',
            'regist_form_client': 1
        }
        response = self.client.post(reverse('client:client_update', args=[self.client_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.name, 'Updated Client')

    def test_client_delete_view_get(self):
        response = self.client.get(reverse('client:client_delete', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_confirm_delete.html')
        self.assertContains(response, 'Test Client')

    def test_client_delete_view_post(self):
        response = self.client.post(reverse('client:client_delete', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to client_list
        self.assertFalse(Client.objects.filter(pk=self.client_obj.pk).exists())

    def test_client_contacted_create_view_get(self):
        response = self.client.get(reverse('client:client_contacted_create', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_form.html')

    def test_client_contacted_create_view_post(self):
        data = {
            'content': 'Test Contact',
            'detail': 'This is a test contact detail.',
            'contact_type': 1,
        }
        response = self.client.post(reverse('client:client_contacted_create', args=[self.client_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.assertTrue(ClientContacted.objects.filter(client=self.client_obj, content='Test Contact').exists())

    def test_client_contacted_list_view(self):
        ClientContacted.objects.create(client=self.client_obj, content='Contact 1')
        ClientContacted.objects.create(client=self.client_obj, content='Contact 2')
        response = self.client.get(reverse('client:client_contacted_list', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_list.html')
        self.assertContains(response, 'Contact 1')
        self.assertContains(response, 'Contact 2')

    def test_client_contacted_detail_view(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Detail Test Contact')
        response = self.client.get(reverse('client:client_contacted_detail', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_detail.html')
        self.assertContains(response, 'Detail Test Contact')

    def test_client_contacted_update_view_get(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Original Contact')
        response = self.client.get(reverse('client:client_contacted_update', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_form.html')
        self.assertContains(response, 'Original Contact')

    def test_client_contacted_update_view_post(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Original Contact')
        data = {
            'content': 'Updated Contact',
            'detail': 'Updated detail.',
            'contact_type': 2,
        }
        response = self.client.post(reverse('client:client_contacted_update', args=[contacted_obj.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        contacted_obj.refresh_from_db()
        self.assertEqual(contacted_obj.content, 'Updated Contact')

    def test_client_contacted_delete_view_get(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Delete Test Contact')
        response = self.client.get(reverse('client:client_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_contacted_confirm_delete.html')
        self.assertContains(response, 'Delete Test Contact')

    def test_client_contacted_delete_view_post(self):
        contacted_obj = ClientContacted.objects.create(client=self.client_obj, content='Delete Test Contact')
        response = self.client.post(reverse('client:client_contacted_delete', args=[contacted_obj.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to client_detail
        self.assertFalse(ClientContacted.objects.filter(pk=contacted_obj.pk).exists())

    def test_client_change_history_list_view(self):
        response = self.client.get(reverse('client:client_change_history_list', args=[self.client_obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_change_history_list.html')
        self.assertContains(response, 'Test Client')
