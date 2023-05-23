# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import re

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from passive_data_kit.decorators import handle_lock
from passive_data_kit.models import DataPoint

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals
        query = None

        latest_asin_item = AmazonASINItem.objects.all().order_by('-pk').first()

        seconds_window = 0

        if latest_asin_item is not None:
            while query is None or DataPoint.objects.filter(query).count() == 0:
                seconds_window = seconds_window + 60

                window_end = latest_asin_item.added + datetime.timedelta(seconds=seconds_window)

                query = Q(secondary_identifier='webmunk-asin-item') | Q(generator_identifier='webmunk-amazon-order')
                query = query & Q(created__gt=latest_asin_item.added)
                query = query & Q(created__lte=window_end)

                if window_end > timezone.now():
                    break
        else:
            query = Q(secondary_identifier='webmunk-asin-item') | Q(generator_identifier='webmunk-amazon-order')

        last_created = None

        for point in DataPoint.objects.filter(query).order_by('created')[:250]:
            asins = []

            props = point.fetch_properties()

            if point.generator_identifier == 'webmunk-amazon-order':
                for item in props.get('items', []):
                    item_asin = item.get('asin', None)

                    if item_asin is not None and (item_asin in asins) is False:
                        # print('ADDED FROM ORDER: %s' % item_asin)
                        asins.append(item_asin)

            else:
                props = point.fetch_properties()

                page_url = props.get('url!', props.get('url*', None))

                if page_url is not None and '/dp/' in page_url:
                    matches = re.findall('.*/dp/(.+?)/.*', page_url)

                    for matched_item in matches:
                        if ('?' in matched_item) is False and (matched_item in asins) is False:
                            # print('ADDED FROM URL: %s' % matched_item)
                            asins.append(matched_item)

                element = props.get('element-content!', props.get('element-content*', None))

                if element is not None:
                    matches = re.findall('.*/dp/(.+?)/.*', element)

                    for matched_item in matches:
                        if ('?' in matched_item) is False and (matched_item in asins) is False:
                            # print('ADDED FROM ELEMENT URL: %s' % matched_item)
                            asins.append(matched_item)

                    matches = re.findall('data-asin="(.+?)"', element)

                    for matched_item in matches:
                        if (matched_item in asins) is False:
                            # print('ADDED FROM ELEMENT DATA-ASIN: %s' % matched_item)
                            asins.append(matched_item)

            for asin in asins:
                if '"' in asin:
                    tokens = asin.split('"')

                    asin = tokens[0]

                if AmazonASINItem.objects.filter(asin=asin).count() == 0:
                    AmazonASINItem.objects.create(asin=asin, added=point.created, updated=point.created)

            if last_created is None or point.created > last_created:
                last_created = point.created

        if last_created is not None:
            # print('SINCE: %s - %d - %d' % (latest_asin_item.added.isoformat(), DataPoint.objects.filter(query).count(), seconds_window))

            AmazonASINItem.objects.filter(asin__startswith='20', asin__contains='T').filter(asin__contains=':').filter(asin__contains='+').delete()

            AmazonASINItem.objects.create(asin=last_created.isoformat(), added=last_created, updated=last_created)
