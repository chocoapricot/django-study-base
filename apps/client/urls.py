from django.urls import path
from .views import (
    client_list, client_create, client_detail, client_update, client_delete,
    client_contacted_create, client_contacted_list, client_contacted_update, client_contacted_delete, client_contacted_detail,
    client_change_history_list
)

app_name = 'client'

urlpatterns = [
    path('', client_list, name='client_list'),
    path('client/create/', client_create, name='client_create'),
    path('client/detail/<int:pk>/', client_detail, name='client_detail'),
    path('client/update/<int:pk>/', client_update, name='client_update'),
    path('client/delete/<int:pk>/', client_delete, name='client_delete'),
    # クライアント連絡履歴
    path('client/<int:client_pk>/contacted/create/', client_contacted_create, name='client_contacted_create'),
    path('client/<int:client_pk>/contacted/list/', client_contacted_list, name='client_contacted_list'),
    path('client/contacted/<int:pk>/detail/', client_contacted_detail, name='client_contacted_detail'),
    path('client/contacted/<int:pk>/update/', client_contacted_update, name='client_contacted_update'),
    path('client/contacted/<int:pk>/delete/', client_contacted_delete, name='client_contacted_delete'),
    # 変更履歴
    path('client/<int:pk>/change_history/', client_change_history_list, name='client_change_history_list'),
]

