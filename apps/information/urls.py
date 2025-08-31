from django.urls import path
from . import views

app_name = 'information'

urlpatterns = [
    path('', views.InformationListView.as_view(), name='information_list'),
    path('<int:pk>/', views.InformationDetailView.as_view(), name='information_detail'),
    path('new/', views.InformationCreateView.as_view(), name='information_create'),
    path('<int:pk>/edit/', views.InformationUpdateView.as_view(), name='information_update'),
    path('<int:pk>/delete/', views.InformationDeleteView.as_view(), name='information_delete'),
]
