# pylint: disable=line-too-long, no-member

import simplejson as json

from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404

from .models import AmazonASINItem

PAGE_SIZE = 1000

def asin_json(request, asin): # pylint: disable=unused-argument
    asin_item = get_object_or_404(AmazonASINItem, asin__iexact=asin)

    try:
        metadata = json.loads(asin_item.metadata)

        return HttpResponse(json.dumps(metadata, indent=2, ignore_nan=True, default=None), content_type='application/json')
    except TypeError:
        pass

    return HttpResponseNotFound('Item not yet populated')

def asins_json(request): # pylint: disable=unused-argument
    asins = []

    page = request.GET.get('page', '0')

    start = int(page) * PAGE_SIZE
    end = start + PAGE_SIZE

    for asin_pk in AmazonASINItem.objects.all().order_by('pk')[start:end]:
        asin_item = AmazonASINItem.objects.get(pk=asin_pk.pk)

        asin = {
            'asin': asin_item.asin,
            'product_name': asin_item.name,
            'product_type': asin_item.category,
            'product_brand': asin_item.fetch_brand(),
            'added': asin_item.added.isoformat(),
        }

        asins.append(asin)

    return HttpResponse(json.dumps(asins, indent=2, ignore_nan=True, default=None), content_type='application/json')
