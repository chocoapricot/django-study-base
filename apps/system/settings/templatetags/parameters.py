from django import template
from ..utils import my_parameter

register = template.Library()
# 
# htmlで最初に{% load parameters %}を定義して
# {% parameter 'SYSTEM_NAME' %}のように利用する。
# 
@register.simple_tag
def parameter(key, default=None):
    return my_parameter(key, default)
