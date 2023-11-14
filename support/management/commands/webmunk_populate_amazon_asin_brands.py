# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import logging

from django.core.management.base import BaseCommand

from passive_data_kit.decorators import handle_lock

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals
        missing = AmazonASINItem.objects.filter(brand=None).exclude(metadata=None)

        logging.info('Pending items (brand): %s', missing.count())

        for item in missing[0:1000]:
            logging.debug(' %s: %s', item.asin, item.fetch_brand())

#        missing = AmazonASINItem.objects.filter(seller=None).exclude(metadata=None)
#
#        logging.info('Pending items (brand): %s' % missing.count())
#
#        for item in missing:
#            logging.info(' %s: %s' % (item.asin, item.fetch_brand()))
