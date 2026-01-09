from django.test import TestCase
from unittest.mock import patch, MagicMock
from ..helpers import fetch_company_info, fetch_zipcode
from apps.system.apicache.models import ApiCache
from apps.system.settings.models import Parameter
from apps.master.models import UserParameter

class ApiHelpersCacheTest(TestCase):
    """APIヘルパーのキャッシュ動作テスト"""

    def setUp(self):
        # 必要なパラメータを設定
        Parameter.objects.create(key="GBIZ_API_PATH", value="https://example.com/gbiz/", active=True)
        UserParameter.objects.create(pk="GBIZ_API_TOKEN", value="test_token")
        Parameter.objects.create(key="ZIPCODE_API_PATH", value="https://example.com/zipcode/", active=True)
        Parameter.objects.create(key="API_CACHE_VALIDITY_PERIOD", value="3600", active=True)

    @patch('requests.get')
    def test_fetch_company_info_caching(self, mock_get):
        """企業情報取得時のキャッシュ動作をテスト"""
        corporate_number = "1234567890123"
        mock_response_data = {
            "hojin-infos": [{"name": "テスト企業", "corporate_number": corporate_number}]
        }
        
        # モックのレスポンスを設定
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        # 1回目の呼び出し (APIが呼ばれるはず)
        result1 = fetch_company_info(corporate_number)
        self.assertEqual(result1["name"], "テスト企業")
        self.assertEqual(mock_get.call_count, 1)
        self.assertTrue(ApiCache.objects.filter(key=f"company_info_{corporate_number}").exists())

        # 2回目の呼び出し (キャッシュから取得されるため、APIは呼ばれないはず)
        result2 = fetch_company_info(corporate_number)
        self.assertEqual(result2["name"], "テスト企業")
        self.assertEqual(mock_get.call_count, 1)  # カウントが増えていないことを確認

    @patch('requests.get')
    def test_fetch_zipcode_caching(self, mock_get):
        """郵便番号取得時のキャッシュ動作をテスト"""
        zipcode = "1234567"
        mock_response_data = {
            "results": [{"address1": "東京都", "address2": "新宿区", "address3": "西新宿"}]
        }
        
        # モックのレスポンスを設定
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        # 1回目の呼び出し (APIが呼ばれるはず)
        result1 = fetch_zipcode(zipcode)
        self.assertEqual(result1["address1"], "東京都")
        self.assertEqual(mock_get.call_count, 1)
        self.assertTrue(ApiCache.objects.filter(key=f"zipcode_{zipcode}").exists())

        # 2回目の呼び出し (キャッシュから取得されるため、APIは呼ばれないはず)
        result2 = fetch_zipcode(zipcode)
        self.assertEqual(result2["address1"], "東京都")
        self.assertEqual(mock_get.call_count, 1)  # カウントが増えていないことを確認
