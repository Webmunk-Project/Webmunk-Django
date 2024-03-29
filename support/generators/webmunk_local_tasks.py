# pylint: disable=line-too-long

import csv
import datetime
import gc
import logging
import io
import os
import tempfile

import pytz

from django.conf import settings

from passive_data_kit.models import DataPoint, DataSource, DataGeneratorDefinition, DataSourceReference


def generator_name(identifier): # pylint: disable=unused-argument
    return 'Webmunk: Visible Tasks'

def compile_report(generator, sources, data_start=None, data_end=None, date_type='created'): # pylint: disable=too-many-locals, too-many-statements, too-many-branches
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
            'Task Count',
            'Task Name(s)',
        ]

        writer.writerow(columns)

        order_reference = DataGeneratorDefinition.definition_for_identifier('webmunk-local-tasks')

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

                point_pks = points.values_list('pk', flat=True)

                points_count = len(point_pks)

                points_index = 0

                while points_index < points_count:
                    logging.debug('[%s] %s/%s', source, points_index, points_count)

                    for point_pk in point_pks[points_index:(points_index + 10000)]:
                        point = DataPoint.objects.get(pk=point_pk)

                        row = []

                        properties = point.fetch_properties()

                        tasks = []

                        for task in properties.get('pending-tasks', []):
                            tasks.append(task.get('message', ''))

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

                        row.append(len(tasks))
                        row.append(';'.join(tasks))

                        writer.writerow(row)

                    points_index += 10000

    return filename
