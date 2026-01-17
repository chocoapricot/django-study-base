import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    """
    パスからファイル名のみを抽出するフィルタ
    文字列またはFileField/FieldFileオブジェクトに対応
    """
    if not value:
        return ""
    if hasattr(value, 'name'):
        return os.path.basename(value.name)
    return os.path.basename(str(value))
