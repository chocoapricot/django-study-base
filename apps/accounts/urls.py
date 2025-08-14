from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path('profile/', views.profile, name='profile'),
    # すべてallauthの標準URLを使用
]
