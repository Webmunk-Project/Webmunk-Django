# pylint: disable=line-too-long

import csv
import datetime
import gc
import io
import os
import tempfile

import pytz

from django.conf import settings

from passive_data_kit.models import DataPoint, DataSource, DataGeneratorDefinition, DataSourceReference


def extract_secondary_identifier(properties):
    return properties.get('111-5181787-4027412', None)

def generator_name(identifier): # pylint: disable=unused-argument
    return 'Webmunk: Amazon Order Items'

def compile_report(generator, sources, data_start=None, data_end=None, date_type='created'): # pylint: disable=too-many-locals, too-many-statements
    filename = tempfile.gettempdir() + os.path.sep + generator + '.txt'

    with io.open(filename, 'w', encoding='utf-8') as outfile:
        writer = csv.writer(outfile, delimiter='\t')

        columns = [
            'Source',
            'Date Created',
            'Date Created UTC',
            'Date Recorded',
            'Date Recorded UTC',
            'Time Zone',
            'Order Number',
            'Order Date',
            'Item ASIN',
            'Item Title',
            'Item Seller',
            'Item Condition',
            'Item Price',
            'Item URL',
            'Order Subtotal',
            'Order Pretax Total',
            'Order Tax',
            'Order Shipping',
            'Order Total',
            'Destination',
            'Delivery Date',
        ]

        writer.writerow(columns)

        order_reference = DataGeneratorDefinition.definition_for_identifier('webmunk-amazon-order')

        for source in sorted(sources): # pylint: disable=too-many-nested-blocks
            data_source = DataSource.objects.filter(identifier=source).first()

            if data_source is not None and data_source.server is None:
                gc.collect()

                source_ref = DataSourceReference.reference_for_source(source)

                if data_end is not None and data_start is not None:
                    if (data_end - data_start).days < 1:
                        data_start = data_end - datetime.timedelta(days=1)

                date_sort = '-created'

                points = DataPoint.objects.filter(source_reference=source_ref, generator_definition=order_reference)

                if date_type == 'created':
                    if data_start is not None:
                        points = points.filter(created__gte=data_start)

                    if data_end is not None:
                        points = points.filter(created__lte=data_end)

                if date_type == 'recorded':
                    if data_start is not None:
                        points = points.filter(recorded__gte=data_start)

                    if data_end is not None:
                        points = points.filter(recorded__lte=data_end)

                    date_sort = '-recorded'

                points = points.order_by(date_sort)

                for point in points:
                    properties = point.fetch_properties()

                    for item in properties.get('items', []):
                        row = []

                        row.append(point.source)

                        tz_str = properties['passive-data-metadata'].get('timezone', settings.TIME_ZONE)

                        here_tz = pytz.timezone(tz_str)

                        created = point.created.astimezone(here_tz)
                        recorded = point.recorded.astimezone(here_tz)

                        row.append(created.isoformat())
                        row.append(created.astimezone(pytz.utc).isoformat())
                        row.append(recorded.isoformat())
                        row.append(recorded.astimezone(pytz.utc).isoformat())

                        row.append(tz_str)

                        here_tz = pytz.timezone(tz_str)

                        row.append(properties.get('order-number', ''))
                        row.append(properties.get('order-date', '').split('T')[0])

                        row.append(item.get('asin', ''))
                        row.append(item.get('title', ''))
                        row.append(item.get('seller', ''))
                        row.append(item.get('condition', ''))
                        row.append(item.get('price', ''))
                        row.append(item.get('url', ''))

                        row.append(properties.get('order-subtotal', ''))
                        row.append(properties.get('order-pretax-total', ''))
                        row.append(properties.get('order-tax', properties.get('order-Tax', '')))
                        row.append(properties.get('order-shipping', ''))
                        row.append(properties.get('order-total', ''))
                        row.append(properties.get('"order-destination', ''))
                        row.append(properties.get('order-delivered', ''))

                        writer.writerow(row)

    return filename
