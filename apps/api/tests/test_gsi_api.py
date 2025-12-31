from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.api.helpers import fetch_gsi_address
from apps.system.settings.models import Dropdowns, Parameter
from apps.system.apicache.models import ApiCache

class GsiApiTest(TestCase):
    def setUp(self):
        # APIパスの設定
        Parameter.objects.create(
            category='api',
            key='GSI_REVERSE_GEOCODER_API_PATH',
            value='https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress',
            active=True
        )
        # キャッシュ有効期間の設定
        Parameter.objects.create(
            category='api',
            key='API_CACHE_VALIDITY_PERIOD',
            value='86400',
            active=True
        )
        # 都道府県マスター（Dropdowns）の設定
        Dropdowns.objects.create(category='pref', name='東京都', value='13', disp_seq=13)

    @patch('requests.get')
    def test_fetch_gsi_address_success(self, mock_get):
        """正常に住所が取得できることをテスト"""
        lat = "35.681236"
        lon = "139.767125"
        
        # mockの戻り値を設定
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": {"muniCd": "13101", "lv01Nm": "千代田区永田町一丁目"}}
        mock_get.return_value = mock_response

        address = fetch_gsi_address(lat, lon)
        self.assertEqual(address, "東京都千代田区永田町一丁目")

    @patch('requests.get')
    def test_fetch_gsi_address_caching(self, mock_get):
        """キャッシュが機能していることをテスト"""
        lat = "35.6812"
        lon = "139.7671"
        
        # 1回目の呼び出し用モックレスポンス (住所検索API + muni.js)
        # fetch_municipality_name が呼ばれる可能性があるため、mock_getは複数回呼ばれることを想定
        
        mock_response_address = MagicMock()
        mock_response_address.status_code = 200
        mock_response_address.json.return_value = {"results": {"muniCd": "13101", "lv01Nm": "千代田区"}}
        
        mock_response_muni = MagicMock()
        mock_response_muni.status_code = 200
        mock_response_muni.text = "GSI.MUNI_ARRAY[\"13101\"] = '13,東京都,13101,千代田区';"

        # side_effectでURLに応じて返すレスポンスを変える、または順序で変える
        def side_effect(url, **kwargs):
            if "muni.js" in url:
                return mock_response_muni
            return mock_response_address
            
        mock_get.side_effect = side_effect

        # 1回目の呼び出し
        address1 = fetch_gsi_address(lat, lon)
        self.assertEqual(address1, "東京都千代田区千代田区") # 重複部分は気ニシナイ（テストデータ依存）
        
        # 呼び出し回数を保存
        first_call_count = mock_get.call_count
        self.assertTrue(first_call_count >= 1)

        # 2回目の呼び出し（キャッシュから取得されるはず）
        address2 = fetch_gsi_address(lat, lon)
        self.assertEqual(address2, "東京都千代田区千代田区")
        
        # 回数が増えていないことを確認
        self.assertEqual(mock_get.call_count, first_call_count)

    @patch('requests.get')
    def test_fetch_gsi_address_failure(self, mock_get):
        """APIエラー時にNoneを返すことをテスト"""
        lat = "35.6812"
        lon = "139.7671"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        address = fetch_gsi_address(lat, lon)
        self.assertIsNone(address)
