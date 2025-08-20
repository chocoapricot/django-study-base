"""
バッジ用テンプレートフィルタ
"""
from django import template

register = template.Library()

# regist_form_codeに応じてバッジのクラス名を返すフィルタ
@register.filter
def badge_class(code):
    try:
        code = int(code)
    except (ValueError, TypeError):
        return "bg-light"
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
