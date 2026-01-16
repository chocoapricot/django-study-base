from .models import UserParameter

def my_user_parameter(key, default=None):
    """キーに対応するユーザーパラメータの値を取得"""
    try:
        param = UserParameter.objects.get(key=key)
        return param.value
    except UserParameter.DoesNotExist:
        return default
