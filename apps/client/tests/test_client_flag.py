from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client, ClientFlag
from apps.company.models import CompanyDepartment, CompanyUser
from apps.master.models_other import FlagStatus
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class ClientFlagTest(TestCase):
    def setUp(self):
        # 会社データの作成（TenantManager用）
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123'
        )
        # テナントIDをスレッドローカルに設定
        set_current_tenant_id(self.company.tenant_id)

        # テナントコンテキストの設定（TenantManagerが期待するセッション情報の模擬）
        self.test_client = TestClient()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password',
            tenant_id=self.company.tenant_id
        )
        self.test_client.login(email='admin@example.com', password='password')

        # セッションにテナントIDを設定
        session = self.test_client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # マスターデータの作成
        self.client_obj = Client.objects.create(
            name='テスト取引先',
            name_furigana='テストトリヒキサキ',
            tenant_id=self.company.tenant_id
        )
        self.dept = CompanyDepartment.objects.create(
            name='Test Dept',
            department_code='D001',
            tenant_id=self.company.tenant_id
        )
        self.comp_user = CompanyUser.objects.create(
            name_last='担当',
            name_first='者',
            department_code='D001',
            tenant_id=self.company.tenant_id
        )
        self.status = FlagStatus.objects.create(
            name='Test Status',
            display_order=1,
            tenant_id=self.company.tenant_id
        )

    def test_client_flag_list_view(self):
        """フラッグ一覧画面のテスト"""
        response = self.test_client.get(reverse('client:client_flag_list', kwargs={'client_pk': self.client_obj.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/client_flag_list.html')

    def test_client_flag_create_view(self):
        """フラッグ登録画面のテスト"""
        response = self.test_client.get(reverse('client:client_flag_create', kwargs={'client_pk': self.client_obj.pk}))
        self.assertEqual(response.status_code, 200)

        # 登録処理
        data = {
            'client': self.client_obj.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        }
        response = self.test_client.post(reverse('client:client_flag_create', kwargs={'client_pk': self.client_obj.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientFlag.objects.filter(client=self.client_obj, flag_status=self.status).exists())

    def test_client_flag_update_view(self):
        """フラッグ編集画面のテスト"""
        flag = ClientFlag.objects.create(
            client=self.client_obj,
            company_department=self.dept,
            company_user=self.comp_user,
            flag_status=self.status,
            tenant_id=self.company.tenant_id
        )

        # 編集画面
        response = self.test_client.get(reverse('client:client_flag_update', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 200)

        # 更新処理
        new_status = FlagStatus.objects.create(
            name='New Status',
            display_order=2,
            tenant_id=self.company.tenant_id
        )
        data = {
            'client': self.client_obj.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': new_status.pk,
        }
        response = self.test_client.post(reverse('client:client_flag_update', kwargs={'pk': flag.pk}), data)
        self.assertEqual(response.status_code, 302)
        flag.refresh_from_db()
        self.assertEqual(flag.flag_status, new_status)

    def test_client_flag_delete_view(self):
        """フラッグ削除画面のテスト"""
        flag = ClientFlag.objects.create(
            client=self.client_obj,
            company_department=self.dept,
            company_user=self.comp_user,
            flag_status=self.status,
            tenant_id=self.company.tenant_id
        )

        # 削除確認画面
        response = self.test_client.get(reverse('client:client_flag_delete', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 200)

        # 削除実行
        response = self.test_client.post(reverse('client:client_flag_delete', kwargs={'pk': flag.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientFlag.objects.filter(pk=flag.pk).exists())

    def test_client_flag_validation_required_status(self):
        """フラッグステータス必須バリデーションのテスト"""
        data = {
            'client': self.client_obj.pk,
            'company_department': self.dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': '',
        }
        response = self.test_client.post(reverse('client:client_flag_create', kwargs={'client_pk': self.client_obj.pk}), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'flag_status', 'このフィールドは必須です。')

    def test_client_flag_validation_department_required_for_user(self):
        """担当者入力時の組織必須バリデーションのテスト"""
        data = {
            'client': self.client_obj.pk,
            'company_department': '',
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        }
        response = self.test_client.post(reverse('client:client_flag_create', kwargs={'client_pk': self.client_obj.pk}), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'company_department', '会社担当者を入力するときは、会社組織を必須にしてください。')

    def test_client_flag_validation_department_user_mismatch(self):
        """組織と担当者の所属組織不一致バリデーションのテスト"""
        other_dept = CompanyDepartment.objects.create(
            name='Other Dept',
            department_code='D002',
            tenant_id=self.company.tenant_id
        )
        data = {
            'client': self.client_obj.pk,
            'company_department': other_dept.pk,
            'company_user': self.comp_user.pk,
            'flag_status': self.status.pk,
        }
        response = self.test_client.post(reverse('client:client_flag_create', kwargs={'client_pk': self.client_obj.pk}), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'company_user', '会社組織と、会社担当者の所属する組織が違います。')
