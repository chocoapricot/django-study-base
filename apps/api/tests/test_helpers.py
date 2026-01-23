import requests
from django.test import TestCase
from unittest.mock import patch
from ..helpers import fetch_company_info


class FetchCompanyInfoTest(TestCase):
    """gBizINFO API連携のテスト"""
    
    @patch('apps.api.helpers.requests.get')
    def test_fetch_company_info_success(self, mock_get):
        """有効な法人番号で企業情報取得が成功することをテスト"""
        # モックの設定
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hojin-infos": [
                {
                    "name": "トヨタ自動車株式会社",
                    # 他の必要なフィールドもここに追加
                }
            ]
        }

        # トヨタ自動車の法人番号を使用
        corporate_number = "1180301018771"
        response = fetch_company_info(corporate_number)
        
        # 期待する結果の確認
        self.assertIsNotNone(response)
        self.assertIn("name", response)
        self.assertEqual(response["name"], "トヨタ自動車株式会社")

    @patch('apps.api.helpers.requests.get')
    def test_fetch_company_info_failure(self, mock_get):
        """JSONデコードエラー時にNoneが返されることをテスト"""
        # モックの設定
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        # .json() が JSONDecodeError を送出するように設定
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)

        # 存在しない法人番号を使用
        corporate_number = "0000000000000"
        response = fetch_company_info(corporate_number)
        
        # 失敗時の動作を確認
        self.assertIsNone(response)