# tests.py

from django.test import TestCase
from .helpers import fetch_company_info

class FetchCompanyInfoTest(TestCase):
    def test_fetch_company_info_success(self):
        # トヨタ自動車の法人番号を使用
        corporate_number = "1180301018771"
        response = fetch_company_info(corporate_number)
        
        # レスポンスの中身を確認
        print("Response:", response)  # デバッグ用にレスポンス内容を表示
        
        # 期待する結果の確認
        self.assertIsNotNone(response)
        self.assertIn("name", response)  # name フィールドが含まれていることを確認
        self.assertEqual(response["name"], "トヨタ自動車株式会社")  # name が一致するか確認

    def test_fetch_company_info_failure(self):
        # 存在しない法人番号を使用
        corporate_number = "0000000000000"
        response = fetch_company_info(corporate_number)
        
        # 失敗時の動作を確認
        self.assertIsNone(response)
