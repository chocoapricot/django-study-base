from django.urls import path
from . import views

app_name = 'system_flags'

urlpatterns = [
    path('', views.flag_list, name='flag_list'),
]
