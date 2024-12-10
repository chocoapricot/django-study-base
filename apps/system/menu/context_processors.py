# context_processors.py
from .models import Menu

def menu_items(request):
    menus = Menu.objects.filter(active=True).order_by('disp_seq')
    return {'menus': menus}

