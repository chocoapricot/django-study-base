from django import template

register = template.Library()

@register.filter
def my_menu_active(menu, request_path):
    """メニューがアクティブかどうかを判定"""
    return menu.is_active_for_path(request_path)

@register.filter
def has_menu_permission(menu, user):
    """ユーザーがメニューにアクセスする権限があるかチェック"""
    return menu.has_permission(user)