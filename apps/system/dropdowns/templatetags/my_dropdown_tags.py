from django import template
from django.shortcuts import get_object_or_404
from ..models import Dropdowns

register = template.Library()

@register.simple_tag
def my_name(category, value):
    try:
        # categoryとvalueでDropdownsオブジェクトを検索し、見つかればnameを返す
        dropdown = Dropdowns.objects.get(category=category, value=value, active=True)
        return dropdown.name
    except Dropdowns.DoesNotExist:
        # 該当するオブジェクトがない場合は「未設定」を返す
        return "未設定"
