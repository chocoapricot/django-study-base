from django.test import TestCase
from apps.information.models import InformationFromCompany

class InformationFromCompanyModelTest(TestCase):

    def test_create_information(self):
        """InformationFromCompanyモデルのインスタンスが正しく作成されることをテストします。"""
        info = InformationFromCompany.objects.create(
            title="Test Information",
            content="This is a test.",
            target="staff",
        )
        self.assertEqual(info.title, "Test Information")
        self.assertEqual(info.content, "This is a test.")
        self.assertEqual(info.target, "staff")
        self.assertEqual(str(info), "Test Information")

    def test_str_representation(self):
        """__str__メソッドがタイトルを返すことをテストします。"""
        info = InformationFromCompany(title="A More Detailed Title")
        self.assertEqual(str(info), "A More Detailed Title")
