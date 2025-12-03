# context_processors.py
from django.conf import settings
from .models import Menu
from apps.common.constants import Constants

def menu_items(request):
    menus = Menu.objects.filter(active=True).order_by('disp_seq')
    return {'menus': menus}

def constants(request):
    """
    Constantsクラスをテンプレートで使用できるようにする
    """
    return {'Constants': Constants}

def ui_settings(request):
    """
    UI設定をテンプレートで使用できるようにする
    """
    return {
        'BASE_FONT_SIZE': getattr(settings, 'BASE_FONT_SIZE', '16px'),
    }
