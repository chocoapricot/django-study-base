from django import template
from ..utils import my_user_parameter

register = template.Library()

@register.simple_tag
def user_parameter(key, default=None, **kwargs):
    val = my_user_parameter(key, default)
    if val and kwargs:
        return val.format(**kwargs)
    return val
