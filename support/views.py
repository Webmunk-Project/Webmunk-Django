# pylint: disable=line-too-long

import simplejson as json

from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404

from .models import AmazonASINItem

def asin_json(request, asin): # pylint: disable=unused-argument
    asin_item = get_object_or_404(AmazonASINItem, asin__iexact=asin)

    try:
        metadata = json.loads(asin_item.metadata)

        return HttpResponse(json.dumps(metadata, indent=2, ignore_nan=True, default=None), content_type='application/json')
    except TypeError:
        pass

    return HttpResponseNotFound('Item not yet populated')
