# urls.py
from django.urls import path
from .views import list

urlpatterns = [
    # たぶん、URLでname='list'に該当したら、views.pyのlistを呼ぶ
    path('', list, name='list'),
]
