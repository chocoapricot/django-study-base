import datetime
from django.utils import timezone
from .models import ApiCache


def get_api_cache(key: str):
    """
    指定されたキーに一致する有効なAPIキャッシュを取得する。

    Args:
        key (str): キャッシュキー。

    Returns:
        dict | None: キャッシュが存在し、有効期限内の場合はレスポンスボディを返す。
                     それ以外の場合はNoneを返す。
    """
    try:
        cache = ApiCache.objects.get(
            key=key,
            expires_at__gt=timezone.now()
        )
        return cache.response
    except ApiCache.DoesNotExist:
        return None


def set_api_cache(key: str, response: dict, validity_period_seconds: int):
    """
    APIのレスポンスをキャッシュに保存または更新する。

    Args:
        key (str): キャッシュキー。
        response (dict): 保存するレスポンスボディ(JSON)。
        validity_period_seconds (int): キャッシュの有効期間（秒）。
    """
    expires_at = timezone.now() + datetime.timedelta(seconds=validity_period_seconds)
    ApiCache.objects.update_or_create(
        key=key,
        defaults={
            'response': response,
            'expires_at': expires_at
        }
    )
