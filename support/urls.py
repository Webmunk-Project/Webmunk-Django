from django.conf.urls import url

from .views import asin_json, asins_json

urlpatterns = [
    url(r'^asins.json$', asins_json, name='asins_json'),
    url(r'^asin/(?P<asin>.+).json$', asin_json, name='asin_json'),
]
