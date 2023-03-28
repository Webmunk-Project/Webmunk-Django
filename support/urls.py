from django.conf.urls import url

from .views import asin_json

urlpatterns = [
    url(r'^asin/(?P<asin>.+).json$', asin_json, name='asin_json'),
]
