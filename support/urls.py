import sys

if sys.version_info[0] > 2:
    from django.urls import re_path as url # pylint: disable=no-name-in-module
else:
    from django.conf.urls import url

from .views import asin_json, asins_json

urlpatterns = [
    url(r'^asins.json$', asins_json, name='asins_json'),
    url(r'^asin/(?P<asin>.+).json$', asin_json, name='asin_json'),
]
