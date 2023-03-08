# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from django.core.management.base import BaseCommand
from django.db.models.functions import Length

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-statements
        class_items = AmazonASINItem.objects.filter(asin__icontains='"')

        print('Remaining: %s' % class_items.count())

        to_delete = []

        for class_item in class_items[:2500]:
            tokens = class_item.asin.split('"')

            asin_value = tokens[0]

            asin_value = asin_value.replace('/ref=dp_atch_dss_w_lm_', '').replace('&amp;ref_=ab_bps_ext_card', '').replace('_', '').replace('&quot;}', '')

            if '?' in asin_value:
                tokens = class_item.asin.split('?')

                asin_value = tokens[0]

            if '#' in asin_value:
                tokens = class_item.asin.split('#')

                asin_value = tokens[0]

            if len(tokens) > 1 and len(asin_value) == 10:
                if AmazonASINItem.objects.filter(asin__iexact=asin_value).count() > 0:
                    to_delete.append(class_item)
                    print('Deleting %s' % class_item.asin)
                else:
                    class_item.asin = asin_value
                    class_item.metadata = None
                    class_item.save()
                    print('Updating %s' % class_item.asin)
            if len(asin_value) >= 32:
                to_delete.append(class_item)
                print('Deleting %s' % class_item.asin)
            else:
                print('Skipping %s' % class_item.asin)

        for class_item in to_delete:
            class_item.delete()

        class_items = AmazonASINItem.objects.filter(asin__icontains='<')

        print('Remaining: %s' % class_items.count())

        to_delete = []

        for class_item in class_items[:2500]:
            asin_value = class_item.asin.replace('<', '')

            if len(asin_value) == 10:
                if AmazonASINItem.objects.filter(asin__iexact=asin_value).count() > 0:
                    to_delete.append(class_item)
                    print('Deleting %s' % class_item.asin)
                else:
                    class_item.asin = asin_value
                    class_item.metadata = None
                    class_item.save()
                    print('Updating %s' % class_item.asin)
            else:
                print('Skipping %s' % class_item.asin)

        for class_item in to_delete:
            class_item.delete()

        class_items = AmazonASINItem.objects.filter(asin__icontains='&quot;')

        print('Remaining: %s' % class_items.count())

        to_delete = []

        for class_item in class_items[:2500]:
            tokens = class_item.asin.split('&quot;')

            asin_value = tokens[0]

            if len(asin_value) == 10:
                if AmazonASINItem.objects.filter(asin__iexact=asin_value).count() > 0:
                    to_delete.append(class_item)
                    print('Deleting %s' % class_item.asin)
                else:
                    class_item.asin = asin_value
                    class_item.metadata = None
                    class_item.save()
                    print('Updating %s' % class_item.asin)
            else:
                print('Skipping %s' % class_item.asin)

        for class_item in to_delete:
            class_item.delete()

        to_delete = []

        for class_item in to_delete:
            class_item.delete()

        class_items = AmazonASINItem.objects.filter(asin__icontains='/ref=dp_atch_dss_w_lm_')

        print('Remaining: %s' % class_items.count())

        to_delete = []

        for class_item in class_items[:2500]:
            asin_value = class_item.asin.replace('/ref=dp_atch_dss_w_lm_', '')
            asin_value = asin_value.replace('_', '')

            if len(asin_value) == 10:
                if AmazonASINItem.objects.filter(asin__iexact=asin_value).count() > 0:
                    to_delete.append(class_item)
                    print('Deleting %s' % class_item.asin)
                else:
                    class_item.asin = asin_value
                    class_item.metadata = None
                    class_item.save()
                    print('Updating %s' % class_item.asin)
            else:
                print('Skipping %s' % class_item.asin)

        for class_item in to_delete:
            class_item.delete()

        to_delete = []

        long_asins = AmazonASINItem.objects.annotate(asin_length=Length('asin')).filter(asin_length__gte=32)

        print('Remaining: %s' % long_asins.count())

        for class_item in long_asins[:2500]:
            print('Deleting %s' % class_item.asin)
            to_delete.append(class_item)

        for class_item in to_delete:
            class_item.delete()
