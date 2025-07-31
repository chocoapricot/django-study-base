from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('password/reset/', views.CustomPasswordResetView.as_view(), name='account_reset_password'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
]
