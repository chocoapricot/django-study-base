"""
バッジ用テンプレートフィルタ
"""
from django import template

register = template.Library()

# regist_form_codeや文字列の値に応じてバッジのクラス名を返すフィルタ
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
