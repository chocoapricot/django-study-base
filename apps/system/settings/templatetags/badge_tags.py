"""
バッジ用テンプレートフィルタ
"""
from django import template
from apps.common.constants import Constants

register = template.Library()

# staff_regist_status_codeや文字列の値に応じてバッジのクラス名を返すフィルタ
@register.filter
def badge_class(value):
    # 値がNoneの場合はデフォルト
    if value is None:
        return 'bg-light'

    # 整数に変換して範囲でチェック
    try:
        code = int(value)
        if code < 10:
            return "bg-primary"
        elif code < 20:
            return "bg-success"
        elif code < 30:
            return "bg-info"
        elif code < 40:
            return "bg-warning"
        elif code < 50:
            return "bg-danger"
        elif code >= 90:
            return "bg-dark"
        else:
            return "bg-light"
    except (ValueError, TypeError):
        # 整数に変換できない場合はデフォルト
        return "bg-secondary"

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

# 通知種別に応じてアイコンクラスを返すフィルタ
@register.filter
def notification_type_icon(notification_type):
    """通知種別に応じたアイコンクラスを返す"""
    if notification_type == Constants.NOTIFICATION_TYPE.ALERT:
        return 'bi-exclamation-triangle-fill'
    elif notification_type == Constants.NOTIFICATION_TYPE.WARNING:
        return 'bi-exclamation-circle-fill'
    elif notification_type == Constants.NOTIFICATION_TYPE.INFO:
        return 'bi-info-circle-fill'
    else:  # GENERAL
        return 'bi-bell-fill'
