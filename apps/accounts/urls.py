from django.urls import path
from . import views
from allauth.account import views as allauth_views

urlpatterns = [
    path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('password/reset/', views.CustomPasswordResetView.as_view(), name='account_reset_password'),
    path('password/reset/done/', allauth_views.PasswordResetDoneView.as_view(), name='account_reset_password_done'),
    path('password/reset/key/<uidb36>-<key>/', allauth_views.PasswordResetFromKeyView.as_view(), name='account_reset_password_from_key'),
    path('password/reset/key/done/', allauth_views.PasswordResetFromKeyDoneView.as_view(), name='account_reset_password_from_key_done'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
]
