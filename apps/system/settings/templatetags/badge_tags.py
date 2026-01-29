"""
バッジ用テンプレートフィルタ
"""
from django import template
from apps.common.constants import Constants

register = template.Library()

# staff_regist_status_codeや文字列の値に応じてバッジの色名を返すフィルタ
@register.filter
def badge_color(value):
    # 値がNoneの場合はデフォルト
    if value is None:
        return 'light'

    # 整数に変換して範囲でチェック
    try:
        code = int(value)
        if code < 10:
            return "primary"
        elif code < 20:
            return "success"
        elif code < 30:
            return "info"
        elif code < 40:
            return "warning"
        elif code < 50:
            return "danger"
        elif code >= 90:
            return "dark"
        else:
            return "light"
    except (ValueError, TypeError):
        # 整数に変換できない場合はデフォルト
        return "secondary"

# staff_regist_status_codeや文字列の値に応じてバッジのクラス名を返すフィルタ
@register.filter
def badge_class(value):
    color = badge_color(value)
    return f"bg-{color}"

# 通知種別に応じてバッジのクラス名を返すフィルタ
@register.filter
def notification_type_badge_class(notification_type):
    """通知種別に応じたバッジクラスを返す"""
    if notification_type == Constants.NOTIFICATION_TYPE.ALERT:
        return 'bg-danger'
    elif notification_type == Constants.NOTIFICATION_TYPE.WARNING:
        return 'bg-warning text-dark'
    elif notification_type == Constants.NOTIFICATION_TYPE.INFO:
        return 'bg-info'
    else:  # GENERAL
        return 'bg-primary'
