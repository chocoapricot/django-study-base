"""
URL configuration for django_study_base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')), # カスタムURLを先に配置
    path('accounts/', include('allauth.urls')),  # allauthの標準URL
    # path('accounts/', include('django.contrib.auth.urls')),
    path('', include('apps.home.urls')),
    path('api/', include('apps.api.urls')),
    path('staff/', include('apps.staff.urls')),
    path('client/', include('apps.client.urls')),
    path('connect/', include('apps.connect.urls')),
    path('csstest/', include('apps.csstest.urls')),
    path('common/', include('apps.common.urls')),
    path('logs/', include('apps.system.logs.urls')),
    path('company/', include('apps.company.urls')),
    path('master/', include('apps.master.urls')),
    path('contract/', include('apps.contract.urls')),
    path('profile/', include('apps.profile.urls')),
    path('information/', include('apps.information.urls')),
]

# 開発環境でのメディアファイル配信
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)