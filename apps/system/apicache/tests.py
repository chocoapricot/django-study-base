import time
from django.test import TestCase
from .utils import get_api_cache, set_api_cache
from .models import ApiCache


class ApiCacheUtilsTestCase(TestCase):
    """
    APIキャッシュユーティリティ関数のテストケース
    """

    def test_set_and_get_cache(self):
        """
        キャッシュが正しく保存され、取得できることをテストする。
        """
        key = "test_key_1"
        response_data = {"data": "test_data"}
        validity_period = 60  # 60秒

        # キャッシュを設定
        set_api_cache(key, response_data, validity_period)

        # キャッシュを取得
        cached_response = get_api_cache(key)

        # 取得したデータが正しいか検証
        self.assertEqual(cached_response, response_data)

    def test_get_expired_cache(self):
        """
        有効期限が切れたキャッシュが取得されないことをテストする。
        """
        key = "test_key_expired"
        response_data = {"data": "expired_data"}
        validity_period = 1  # 1秒

        # キャッシュを設定
        set_api_cache(key, response_data, validity_period)

        # キャッシュが期限切れになるのを待つ
        time.sleep(2)

        # キャッシュを取得
        cached_response = get_api_cache(key)

        # キャッシュが存在しないこと（Noneが返されること）を検証
        self.assertIsNone(cached_response)

    def test_get_nonexistent_cache(self):
        """
        存在しないキーでキャッシュを取得しようとした場合にNoneが返ることをテストする。
        """
        key = "nonexistent_key"

        # 存在しないキーでキャッシュを取得
        cached_response = get_api_cache(key)

        # Noneが返されることを検証
        self.assertIsNone(cached_response)

    def test_update_existing_cache(self):
        """
        既存のキーでキャッシュを更新できることをテストする。
        """
        key = "test_key_update"
        initial_response = {"data": "initial_data"}
        updated_response = {"data": "updated_data"}
        validity_period = 60

        # 最初のキャッシュを設定
        set_api_cache(key, initial_response, validity_period)

        # 更新前のデータを検証
        cached_response_before = get_api_cache(key)
        self.assertEqual(cached_response_before, initial_response)

        # 同じキーでキャッシュを更新
        set_api_cache(key, updated_response, validity_period)

        # 更新後のデータを検証
        cached_response_after = get_api_cache(key)
        self.assertEqual(cached_response_after, updated_response)

        # レコードが1つだけ存在することを確認
        self.assertEqual(ApiCache.objects.filter(key=key).count(), 1)
