# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from django.core.management.base import BaseCommand

from passive_data_kit.models import DataSourceReference, DataGeneratorDefinition, DataPoint

class Command(BaseCommand):
    help = 'Removes duplicate Amazon order items from repeated uploads'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        amazon_items = DataGeneratorDefinition.definition_for_identifier('pdk-external-amazon-item')

        total = 0
        total_duplicates = 0

        for source_reference in DataSourceReference.objects.all():
            print('Inspecting %s...' % source_reference)

            to_delete = []
            seen = {}

            for point in DataPoint.objects.filter(source_reference=source_reference, generator_definition=amazon_items).order_by('recorded'):
                properties = point.fetch_properties()

                asin = properties.get('asin', None)
                quantity = properties.get('quantity', None)
                order_id = properties.get('pdk_hashed_order_id', None)

                if asin is not None and quantity is not None and order_id is not None:
                    key = '%s--%s--%s--%d--%s--%s' % (source_reference, amazon_items, asin, quantity, point.created.isoformat(), order_id)

                    if seen.get(key, False):
                        to_delete.append(point.pk)
                    else:
                        seen[key] = True
                else:
                    print(' Missing ASIN, quantity, or hashed order ID: %s' % point.pk)

                total += 1

            print(' Duplicates: %d' % len(to_delete))

            total_duplicates += len(to_delete)

            for delete_pk in to_delete:
                DataPoint.objects.filter(pk=delete_pk).delete()

        print('Total: %d, Duplicates: %d' % (total, total_duplicates))
