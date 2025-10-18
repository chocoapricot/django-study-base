# context_processors.py
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

