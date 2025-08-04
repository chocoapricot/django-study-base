from django.urls import path
from . import views

urlpatterns = [
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    # すべてallauthの標準URLを使用
]
