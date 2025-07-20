from .models import Parameter

def my_parameter(key, default=None):
    """キーに対応するパラメータの値を取得"""
    try:
        param = Parameter.objects.get(key=key, active=True)
        return param.value
    except Parameter.DoesNotExist:
        print('Parameter.DoesNotExist -> {}'.format(default))
        return default