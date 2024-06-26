"""extension URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
import sys

from django.conf import settings
from django.contrib import admin

if sys.version_info[0] > 2:
    from django.urls import re_path as url, path, include # pylint: disable=no-name-in-module
else:
    from django.conf.urls import url, path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^data/', include('passive_data_kit.urls')),
    url(r'^data/external/', include('passive_data_kit_external_data.urls')),
    url(r'^monitor/', include('nagios_monitor.urls')),
    url(r'^support/', include('support.urls')),
]

if 'enrollment' in settings.ADDITIONAL_APPS:
    urlpatterns.append(url(r'^enroll/', include('enrollment.urls')))
