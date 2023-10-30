# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import logging
import re

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from passive_data_kit.decorators import handle_lock
from passive_data_kit.models import DataPoint, DataGeneratorDefinition

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals
        latest_asin_item = AmazonASINItem.objects.all().order_by('-pk').first()

        orders = DataGeneratorDefinition.definition_for_identifier('webmunk-amazon-order')
        elements = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-log-elements')

        point_query = Q(generator_definition=orders)
        point_query = point_query | Q(generator_definition=elements)
        # point_query = point_query | Q(secondary_identifier='webmunk-asin-item')

        query = None

        point_count = 0

        if latest_asin_item is not None:
            window_start = latest_asin_item.added

            while query is None or point_count == 0:
                window_end = window_start + datetime.timedelta(seconds=300)

                logging.info('COUNTING BETWEEN %s -- %s -- %s' % (window_start, window_end, timezone.now()))

                query = point_query & Q(created__gt=window_start)
                query = query & Q(created__lte=window_end)

                if window_end > timezone.now():
                    break

                point_count = DataPoint.objects.filter(query).count()

                logging.info('FOUND BETWEEN %s -- %s --> %s -- %s' % (window_start, window_end, point_count, timezone.now()))

                window_start = window_end
        else:
            query = point_query

        last_created = None

        index = 0

        points = DataPoint.objects.filter(query).order_by('created')

        point_pks = points.values_list('pk', flat=True)

        saved = 0

        for point_pk in point_pks:
            point = DataPoint.objects.get(pk=point_pk)

            if (index % 100 == 0):
                logging.debug('INDEX: %s / %s -- %s -- %s' % (index, point_count, point.generator_identifier, timezone.now()))

            index += 1

            asins = []

            props = point.fetch_properties()

            if point.generator_identifier == 'webmunk-amazon-order':
                for item in props.get('items', []):
                    item_asin = item.get('asin', None)

                    if item_asin is not None and (item_asin in asins) is False:
                        # print('ADDED FROM ORDER: %s' % item_asin)
                        asins.append(item_asin)

            elif point.generator_identifier == 'webmunk-extension-log-elements':
                page_url = props.get('url!', props.get('url*', None))

                if page_url is not None and '/dp/' in page_url:
                    matches = re.findall('.*/dp/(.+?)/.*', page_url)

                    for matched_item in matches:
                        if ('?' in matched_item) is False and (matched_item in asins) is False:
                            # print('ADDED FROM URL: %s' % matched_item)
                            asins.append(matched_item)

                for key, ele_matches in props.get('pattern-matches', {}).items():
                    for ele_match in ele_matches:
                        element = ele_match.get('element-content!', ele_match.get('element-content*', None))

                        # print('ELEMENT LEN: %s' % len(element))

                        if element is not None:
                            matches = re.findall('/dp/(.+?)/', element)

                            for matched_item in matches:
                                if ('?' in matched_item) is False and (matched_item in asins) is False:
                                    # print('ADDED FROM ELEMENT URL: %s' % matched_item)
                                    asins.append(matched_item)

                            matches = re.findall('data-asin="(.+?)"', element)

                            for matched_item in matches:
                                if (matched_item in asins) is False:
                                    # print('ADDED FROM ELEMENT DATA-ASIN: %s' % matched_item)
                                    asins.append(matched_item)
            else:
                props = point.fetch_properties()

                page_url = props.get('url!', props.get('url*', None))

                if page_url is not None and '/dp/' in page_url:
                    matches = re.findall('/dp/(.+?)/', page_url)

                    for matched_item in matches:
                        if ('?' in matched_item) is False and (matched_item in asins) is False:
                            # print('ADDED FROM URL: %s' % matched_item)
                            asins.append(matched_item)

                element = props.get('element-content!', props.get('element-content*', None))

                if element is not None:
                    matches = re.findall('/dp/(.+?)/', element)

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

                if ')' in asin:
                    tokens = asin.split(')')

                    asin = tokens[0]

                if '&' in asin:
                    tokens = asin.split('&')

                    asin = tokens[0]

                if '<' in asin:
                    tokens = asin.split('<')

                    asin = tokens[0]

                # print('CHECKING ASIN: %s' % asin)

                if AmazonASINItem.objects.filter(asin=asin).count() == 0:
                    AmazonASINItem.objects.create(asin=asin, added=point.created, updated=point.created)

                    # print('SAVED ASIN: %s' % asin)

                    saved += 1

            if last_created is None or point.created > last_created:
                last_created = point.created

        if last_created is not None:
            # print('SINCE: %s - %d - %d' % (latest_asin_item.added.isoformat(), DataPoint.objects.filter(query).count(), seconds_window))

            AmazonASINItem.objects.filter(asin__startswith='20', asin__contains='T').filter(asin__contains=':').filter(asin__contains='+').delete()

            AmazonASINItem.objects.create(asin=last_created.isoformat(), added=last_created, updated=last_created)

        # if saved > 0:
        #    print('Saved: %s' % saved)
