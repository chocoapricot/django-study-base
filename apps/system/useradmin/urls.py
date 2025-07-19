from django.urls import path
from . import views

app_name = 'useradmin'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
]
