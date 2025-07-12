# urls.py
from django.urls import path
from .views import (
    staff_list, staff_create, staff_detail, staff_update, staff_delete, staff_face, staff_rirekisho, staff_fuyokojo, staff_kyushoku,
    staff_contacted_create, staff_contacted_list, staff_contacted_update, staff_contacted_delete
)

urlpatterns = [
    path('', staff_list, name='staff_list'),
    path('staff/create/', staff_create, name='staff_create'),
    path('staff/detail/<int:pk>/', staff_detail, name='staff_detail'),
    path('staff/face/<int:pk>/'  , staff_face  , name='staff_face'),
    path('staff/update/<int:pk>/', staff_update, name='staff_update'),
    path('staff/delete/<int:pk>/', staff_delete, name='staff_delete'),
    path('staff/rirekisho/<int:pk>/', staff_rirekisho, name='staff_rirekisho'),
    path('staff/kyushoku/<int:pk>/', staff_kyushoku, name='staff_kyushoku'),
    path('staff/fuyokojo/<int:pk>/', staff_fuyokojo, name='staff_fuyokojo'),

    # 連絡履歴
    path('staff/<int:staff_pk>/contacted/create/', staff_contacted_create, name='staff_contacted_create'),
    path('staff/<int:staff_pk>/contacted/list/', staff_contacted_list, name='staff_contacted_list'),
    path('staff/contacted/<int:pk>/update/', staff_contacted_update, name='staff_contacted_update'),
    path('staff/contacted/<int:pk>/delete/', staff_contacted_delete, name='staff_contacted_delete'),
]
