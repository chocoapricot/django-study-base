from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.master.models import StaffAgreement
from apps.master.forms import StaffAgreementForm
from django.contrib.auth.models import Permission
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from apps.staff.models import Staff
from apps.connect.models import ConnectStaffAgree
import time

User = get_user_model()


class StaffAgreementModelTest(TestCase):
    """スタッフ同意文言モデルのテスト"""

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", corporate_number="1234567890123")
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123", tenant_id=self.company.tenant_id
        )

    def test_str_method(self):
        """__str__メソッドのテスト"""
        agreement = StaffAgreement.objects.create(
            name="テスト同意文言",
            agreement_text="これはテスト用の同意文言です。",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(str(agreement), "テスト同意文言")

    def test_default_values(self):
        """デフォルト値のテスト"""
        agreement = StaffAgreement.objects.create(
            name="デフォルト値テスト",
            agreement_text="テキスト",
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(agreement.display_order, 0)
        self.assertTrue(agreement.is_active)

    def test_successful_creation(self):
        """正常な作成のテスト"""
        agreement = StaffAgreement.objects.create(
            name="作成テスト",
            agreement_text="作成テスト用のテキストです。",
            display_order=10,
            is_active=False,
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(agreement.name, "作成テスト")
        self.assertEqual(agreement.agreement_text, "作成テスト用のテキストです。")
        self.assertEqual(agreement.display_order, 10)
        self.assertFalse(agreement.is_active)

    def test_save_method_no_change(self):
        """変更がない場合にupdated_atが更新されないことをテスト"""
        agreement = StaffAgreement.objects.create(
            name="保存テスト",
            agreement_text="テキスト",
            created_by=self.user,
            updated_by=self.user,
        )
        first_updated_at = agreement.updated_at

        time.sleep(0.01)

        agreement.save()

        agreement.refresh_from_db()
        second_updated_at = agreement.updated_at

        self.assertEqual(
            first_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            second_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )


class StaffAgreementViewTest(TestCase):
    """スタッフ同意文言ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(
            name="テスト会社", corporate_number="1234567890123"
        )
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_staff=True,
            tenant_id=self.company.tenant_id
        )
        # Grant all permissions for the model
        permissions = Permission.objects.filter(
            content_type__app_label="master", content_type__model="staffagreement"
        )
        self.user.user_permissions.set(permissions)
        self.client.login(username="testuser", password="testpass123")

        self.agreement = StaffAgreement.objects.create(
            name="テスト同意文言",
            agreement_text="テスト用のテキストです。",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_list_view(self):
        """一覧表示ビューのテスト"""
        response = self.client.get(reverse("master:staff_agreement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "スタッフ同意文言一覧")
        self.assertContains(response, self.agreement.name)
        self.assertTemplateUsed(response, "master/staffagreement_list.html")

    def test_detail_view(self):
        """詳細表示ビューのテスト"""
        response = self.client.get(
            reverse("master:staff_agreement_detail", kwargs={"pk": self.agreement.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "スタッフ同意文言詳細")
        self.assertContains(response, self.agreement.name)
        self.assertTemplateUsed(response, "master/staffagreement_detail.html")

    def test_create_view_get(self):
        """作成ビュー(GET)のテスト"""
        response = self.client.get(reverse("master:staff_agreement_create"))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], StaffAgreementForm)
        self.assertTemplateUsed(response, "master/staffagreement_form.html")

    def test_create_view_post(self):
        """作成ビュー(POST)のテスト"""
        data = {
            "name": "新規同意文言",
            "agreement_text": "新しいテキスト",
            "display_order": 10,
            "is_active": True,
        }
        response = self.client.post(reverse("master:staff_agreement_create"), data)
        self.assertRedirects(response, reverse("master:staff_agreement_list"))
        new_agreement = StaffAgreement.objects.get(name="新規同意文言")
        self.assertEqual(
            new_agreement.corporation_number, self.company.corporate_number
        )

    def test_update_view_post(self):
        """更新ビュー(POST)のテスト"""
        data = {
            "name": "更新された同意文言",
            "agreement_text": self.agreement.agreement_text,
            "display_order": self.agreement.display_order,
            "is_active": self.agreement.is_active,
        }
        response = self.client.post(
            reverse("master:staff_agreement_update", kwargs={"pk": self.agreement.pk}),
            data,
        )
        self.assertRedirects(response, reverse("master:staff_agreement_list"))
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.name, "更新された同意文言")

    def test_delete_view_post(self):
        """削除ビュー(POST)のテスト"""
        response = self.client.post(
            reverse("master:staff_agreement_delete", kwargs={"pk": self.agreement.pk})
        )
        self.assertRedirects(response, reverse("master:staff_agreement_list"))
        self.assertFalse(StaffAgreement.objects.filter(pk=self.agreement.pk).exists())


class StaffAgreementDetailViewAgreedStaffListTest(TestCase):
    """スタッフ同意文言詳細ビューの同意済みスタッフ一覧機能のテスト"""

    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(
            name="テスト会社", corporate_number="1234567890123"
        )
        set_current_tenant_id(self.company.tenant_id)
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_staff=True,
            tenant_id=self.company.tenant_id
        )
        permissions = Permission.objects.filter(
            content_type__app_label="master", content_type__model="staffagreement"
        )
        self.user.user_permissions.set(permissions)
        self.client.login(username="testuser", password="testpass123")
        self.agreement = StaffAgreement.objects.create(
            name="テスト同意", agreement_text="テキスト"
        )

        self.staff1 = Staff.objects.create(
            email="aaa@example.com", name_first="Alice", name_last="Liddell"
        )
        self.staff2 = Staff.objects.create(
            email="bbb@example.com", name_first="Bob", name_last="Marley"
        )
        self.staff3 = Staff.objects.create(
            email="ccc@example.com", name_first="Charlie", name_last="Chaplin"
        )

        self.agree1 = ConnectStaffAgree.objects.create(
            email=self.staff1.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )
        time.sleep(0.01)
        self.agree2 = ConnectStaffAgree.objects.create(
            email=self.staff2.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )
        time.sleep(0.01)
        self.agree3 = ConnectStaffAgree.objects.create(
            email=self.staff3.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )

        self.url = reverse(
            "master:staff_agreement_detail", kwargs={"pk": self.agreement.pk}
        )

    def test_agreed_staff_list_present(self):
        """同意済みスタッフ一覧がコンテキストに含まれていることをテスト"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("agreed_staff_list", response.context)
        self.assertEqual(len(response.context["agreed_staff_list"]), 3)

    def test_filter_by_name(self):
        """氏名によるフィルタリングをテスト"""
        response = self.client.get(self.url, {"q": "Alice"})
        self.assertEqual(len(response.context["agreed_staff_list"]), 1)
        self.assertEqual(response.context["agreed_staff_list"][0]["staff"], self.staff1)

    def test_filter_by_email(self):
        """メールアドレスによるフィルタリングをテスト"""
        response = self.client.get(self.url, {"q": "bbb@example.com"})
        self.assertEqual(len(response.context["agreed_staff_list"]), 1)
        self.assertEqual(response.context["agreed_staff_list"][0]["staff"], self.staff2)

    def test_sort_by_name_asc(self):
        """氏名昇順でのソートをテスト"""
        response = self.client.get(self.url, {"sort": "staff__name", "dir": "asc"})
        agreed_staff_list = response.context["agreed_staff_list"]
        self.assertEqual(agreed_staff_list[0]["staff"], self.staff3)  # Chaplin
        self.assertEqual(agreed_staff_list[1]["staff"], self.staff1)  # Liddell
        self.assertEqual(agreed_staff_list[2]["staff"], self.staff2)  # Marley

    def test_sort_by_email_desc(self):
        """メールアドレス降順でのソートをテスト"""
        response = self.client.get(self.url, {"sort": "staff__email", "dir": "desc"})
        agreed_staff_list = response.context["agreed_staff_list"]
        self.assertEqual(agreed_staff_list[0]["staff"], self.staff3)
        self.assertEqual(agreed_staff_list[1]["staff"], self.staff2)
        self.assertEqual(agreed_staff_list[2]["staff"], self.staff1)

    def test_sort_by_agreed_at_asc(self):
        """同意日時昇順でのソートをテスト"""
        response = self.client.get(self.url, {"sort": "agreed_at", "dir": "asc"})
        agreed_staff_list = response.context["agreed_staff_list"]
        self.assertEqual(agreed_staff_list[0]["staff"], self.staff1)
        self.assertEqual(agreed_staff_list[1]["staff"], self.staff2)
        self.assertEqual(agreed_staff_list[2]["staff"], self.staff3)

    def test_combined_filter(self):
        """複合フィルタリングをテスト"""
        response = self.client.get(
            self.url, {"q": "Bob"}
        )
        self.assertEqual(len(response.context["agreed_staff_list"]), 1)
        self.assertEqual(response.context["agreed_staff_list"][0]["staff"], self.staff2)
