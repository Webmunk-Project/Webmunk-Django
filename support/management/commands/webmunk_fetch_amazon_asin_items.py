# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import re

from django.core.management.base import BaseCommand
from django.db.models import Q

from passive_data_kit.models import DataPoint

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-branches
        query = None

        latest_asin_item = AmazonASINItem.objects.all().order_by('-added').first()

        seconds_window = 0

        if latest_asin_item is not None:
            while query is None or DataPoint.objects.filter(query).count() == 0:
                seconds_window = seconds_window + 60

                query = Q(secondary_identifier='webmunk-asin-item')
                query = query & Q(created__gt=latest_asin_item.added)
                query = query & Q(created__lte=latest_asin_item.added + datetime.timedelta(seconds=seconds_window))

            print('SINCE: %s - %d - %d' % (latest_asin_item.added.isoformat(), DataPoint.objects.filter(query).count(), seconds_window))
        else:
            query = Q(secondary_identifier='webmunk-asin-item').order_by('created')[:250]

        last_created = None

        for point in DataPoint.objects.filter(query):
            asins = []

            props = point.fetch_properties()

            page_url = props.get('url!', None)

            if page_url is not None and '/dp/' in page_url:
                matches = re.findall('.*/dp/(.+?)/.*', page_url)

                for matched_item in matches:
                    if ('?' in matched_item) is False and (matched_item in asins) is False:
                        # print('ADDED FROM URL: %s' % matched_item)

                        asins.append(matched_item)

            element = props.get('element-content!', None)

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
                if AmazonASINItem.objects.filter(asin=asin).count() == 0:
                    AmazonASINItem.objects.create(asin=asin, added=point.created, updated=point.created)

            if last_created is None or point.created > last_created:
                last_created = point.created

        AmazonASINItem.objects.filter(asin__startswith='20', asin__contains='T').filter(asin__contains=':').filter(asin__contains='+').delete()

        AmazonASINItem.objects.create(asin=last_created.isoformat(), added=last_created, updated=last_created)
