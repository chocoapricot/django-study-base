from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('applog/', views.applog_list, name='applog_list'),
]
