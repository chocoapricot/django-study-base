from django import template

register = template.Library()

@register.filter
def my_menu_active(menu, request_path):
    """メニューがアクティブかどうかを判定"""
    return menu.is_active_for_path(request_path)