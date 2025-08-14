from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """辞書から指定されたキーの値を取得"""
    return dictionary.get(key)