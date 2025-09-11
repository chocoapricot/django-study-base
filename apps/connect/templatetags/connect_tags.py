from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """辞書から指定されたキーの値を取得"""
    return dictionary.get(key)

@register.simple_tag
def diff_class(val1, val2, class_name='table-warning'):
    """
    2つの値を比較し、異なれば指定されたCSSクラス名を返す。
    Noneと空文字列、数値と文字列の数値を同一とみなすように正規化して比較する。
    """
    # Noneを空文字列に正規化
    v1_norm = str(val1).strip() if val1 is not None else ''
    v2_norm = str(val2).strip() if val2 is not None else ''

    if v1_norm != v2_norm:
        return class_name
    return ''