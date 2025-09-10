from django.urls import path
from .views import TableListView, TableDataView

app_name = 'system_tables'

urlpatterns = [
    path('', TableListView.as_view(), name='table_list'),
    path('data/<str:table_name>/', TableDataView.as_view(), name='table_data'),
]
