# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import logging
import json
import time

import keepa
import numpy
import pandas

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from passive_data_kit.decorators import handle_lock

from ...models import AmazonASINItem

class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, numpy.ndarray):
            return o.tolist()

        if isinstance(o, datetime.datetime):
            return o.isoformat()

        if isinstance(o, pandas.DataFrame):
            json_str = o.to_json()

            return json.loads(json_str)

        return json.JSONEncoder.default(self, o)

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata using Keepa API'

    def add_arguments(self, parser):
        pass

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches
        verbosity = options.get('verbosity', 0)

        if verbosity == 0:
            level = logging.ERROR
        elif verbosity == 1:
            level = logging.WARN
        elif verbosity == 2:
            level = logging.INFO
        else:
            level = logging.DEBUG

        loggers = [logging.getLogger(name) for name in ('keepa.interface', 'keepa')]

        for logger in loggers:
            logger.setLevel(level)

        api = keepa.Keepa(settings.KEEPA_API_KEY)

        for asin_item in AmazonASINItem.objects.filter(metadata=None).order_by('updated')[:250]: # pylint: disable=too-many-nested-blocks
            metadata = {}

            if len(asin_item.asin) <= 10:
                time.sleep(settings.KEEPA_API_SLEEP_SECONDS)

                try:
                    products = api.query(asin_item.asin, progress_bar=False)

                    # print('%s: %s' % (asin_item.asin, json.dumps(products, indent=2, cls=NumpyEncoder)))

                    if len(products) > 0 and products[0] is not None:
                        product = products[0]

                        if product['title'] is not None:
                            asin_item.name = product['title']

                            category = ''

                            if product.get('categoryTree', None) is not None:
                                for category_item in product.get('categoryTree', []):
                                    if category != '':
                                        category = category + ' > '

                                    category = category + category_item['name']

                                asin_item.category = category

                                print('FOUND: %s - %s / %s' % (asin_item.asin, asin_item.name, asin_item.category))

                            metadata['keepa'] = products
                        else:
                            print('NULL ITEM: %s' % asin_item.asin)
                            metadata['keepa'] = 'Null item'
                    else:
                        print('NOT FOUND: %s' % asin_item.asin)
                        metadata['keepa'] = 'Not found'
                except: # pylint: disable=bare-except
                    print('Invalid identifier: %s' % asin_item.asin)
                    metadata['keepa'] = 'Invalid identifier'

            asin_item.metadata = json.dumps(metadata, indent=2, cls=NumpyEncoder)
            asin_item.updated = timezone.now()
            asin_item.save()
