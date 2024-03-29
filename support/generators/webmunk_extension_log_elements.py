# pylint: disable=line-too-long

import csv
import datetime
import gc
import io
import logging
import os
import tempfile

from zipfile import ZipFile

import arrow
import pytz

from past.utils import old_div

from django.conf import settings
from django.utils.text import slugify

from passive_data_kit.models import DataPoint, DataSource, DataGeneratorDefinition, DataSourceReference

from ..pdk_api import remove_newlines


def generator_name(identifier): # pylint: disable=unused-argument
    return 'Webmunk: Static Page Elements Log'

def compile_report(generator, sources, data_start=None, data_end=None, date_type='created'): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    now = arrow.get()

    zip_filename = tempfile.gettempdir() + os.path.sep + 'webmunk_log_elements_' + str(now.timestamp()) + str(old_div(now.microsecond, 1e6)) + '.zip'

    with ZipFile(zip_filename, 'w', allowZip64=True) as export_file:
        for source in sorted(sources): # pylint: disable=too-many-nested-blocks
            data_source = DataSource.objects.filter(identifier=source).first()

            if data_source is not None and data_source.server is None:
                gc.collect()

                source_ref = DataSourceReference.reference_for_source(source)

                secondary_filename = tempfile.gettempdir() + os.path.sep + generator + '__' + source + '.txt'

                log_elements_reference = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-log-elements')

                with io.open(secondary_filename, 'w', encoding='utf-8') as outfile:
                    writer = csv.writer(outfile, delimiter='\t')

                    columns = [
                        'Source',
                        'Date Created',
                        'Date Recorded',
                        'Time Zone',
                        'Tab ID',
                        'Page ID',
                        'URL',
                        'Page Title',
                        'Pattern',
                        'Top',
                        'Left',
                        'Width',
                        'Height',
                        'Element HTML',
                    ]

                    writer.writerow(columns)

                    if data_end is not None and data_start is not None:
                        if (data_end - data_start).days < 1:
                            data_start = data_end - datetime.timedelta(days=1)

                    date_sort = '-created'

                    points = DataPoint.objects.filter(source_reference=source_ref, generator_definition=log_elements_reference)

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

                    # points = points.order_by(date_sort)

                    # point_pks = points.values_list('pk', flat=True)

                    # points_count = len(point_pks)

                    logging.debug('[%s] Fetching point PKs...', source)

                    point_pks = list(points.values_list('pk', date_sort.replace('-', '')))

                    point_pks.sort(key=lambda pair: pair[1], reverse=True)

                    points_count = len(point_pks)

                    logging.debug('[%s] %d PKs fetched.', source, points_count)

                    points_index = 0

                    while points_index < points_count:
                        logging.debug('[%s] %s/%s', source, points_index, points_count)

                        for point_pk in point_pks[points_index:(points_index + 10000)]:
                            point = DataPoint.objects.get(pk=point_pk[0])

                            properties = point.fetch_properties()

                            for pattern in properties.get('pattern-matches', {}).keys():
                                for pattern_match in properties.get('pattern-matches', {}).get(pattern, []):
                                    try:
                                        row = []

                                        row.append(point.source)

                                        tz_str = properties['passive-data-metadata'].get('timezone', settings.TIME_ZONE)

                                        here_tz = pytz.timezone(tz_str)

                                        created = point.created.astimezone(here_tz)
                                        recorded = point.recorded.astimezone(here_tz)

                                        row.append(created.isoformat())
                                        row.append(recorded.isoformat())

                                        row.append(tz_str)

                                        row.append(properties.get('tab-id', ''))
                                        row.append(properties.get('page-id', ''))

                                        here_tz = pytz.timezone(tz_str)

                                        row.append(properties.get('url*', ''))
                                        row.append(properties.get('page-title*', properties.get('page-title!', '')))

                                        row.append(pattern)

                                        size = pattern_match.get('size', {})
                                        offset = pattern_match.get('offset', {})

                                        row.append(offset.get('top', ''))
                                        row.append(offset.get('left', ''))
                                        row.append(size.get('width', ''))
                                        row.append(size.get('height', ''))

                                        row.append(remove_newlines(pattern_match.get('element-content*', properties.get('element-content!', ''))))

                                        writer.writerow(row)
                                        outfile.flush()

                                    except TypeError:
                                        pass
                                    except AttributeError:
                                        pass

                        points_index += 10000

                        outfile.flush()

                export_file.write(secondary_filename, slugify(generator) + '/' + slugify(source) + '.txt')

                os.remove(secondary_filename)

    return zip_filename
