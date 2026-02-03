from django.urls import path
from . import views
from .views_master import master_select

app_name = 'common'

urlpatterns = [
    # 旧ログ機能は削除されました
    # 新しいログ機能は /logs/app/ を使用してください
    
    # マスター選択
    path('master-select/', master_select, name='master_select'),
    
    # サイドバーの状態保存
    path('api/set_sidebar_state/', views.set_sidebar_state, name='set_sidebar_state'),
]
