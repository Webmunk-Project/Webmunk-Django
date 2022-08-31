# pylint: disable=line-too-long, no-member, too-many-lines

import bz2
import csv
import datetime
import gc
import io
import json
import importlib
import os
import sys
import tempfile
import traceback

from io import StringIO

import pytz

from django.conf import settings
from django.core import management
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from passive_data_kit.models import DataPoint, DataSource, DataGeneratorDefinition, DataSourceReference, DataBundle, install_supports_jsonfield


def remove_newlines(text_block):
    return ''.join(text_block.splitlines())

def compile_report(generator, sources, data_start=None, data_end=None, date_type='created'): # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-return-statements
    try:
        generator_module = importlib.import_module('.generators.' + generator.replace('-', '_'), package='support')

        output_file = None

        try:
            output_file = generator_module.compile_report(generator, sources, data_start=data_start, data_end=data_end, date_type=date_type)
        except TypeError:
            print('TODO: Update ' + generator + '.compile_report to support data_start, data_end, and date_type parameters!')

            output_file = generator_module.compile_report(generator, sources)

        if output_file is not None:
            return output_file
    except ImportError:
        pass
    except AttributeError:
        pass

    try:
        if generator == 'webmunk-visibility-export':
            filename = tempfile.gettempdir() + os.path.sep + generator + '.txt'

            show_reference = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-hide')
            hide_reference = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-show')

            with io.open(filename, 'w', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter='\t')

                columns = [
                    'Source',
                    'Date Created',
                    'Date Recorded',
                    'Time Zone',
                    'Tab ID',
                    'Visible',
                    'Element Class',
                    'Top',
                    'Left',
                    'Width',
                    'Height',
                    'URL',
                    'Page Title',
                    'Element HTML',
                ]

                writer.writerow(columns)

                for source in sorted(sources): # pylint: disable=too-many-nested-blocks
                    data_source = DataSource.objects.filter(identifier=source).first()

                    if data_source is not None and data_source.server is None:
                        gc.collect()

                        source_ref = DataSourceReference.reference_for_source(source)

                        query = Q(generator_definition=show_reference) | Q(generator_definition=hide_reference)

                        if data_end is not None and data_start is not None:
                            if (data_end - data_start).days < 1:
                                data_start = data_end - datetime.timedelta(days=1)

                        date_sort = '-created'

                        points = DataPoint.objects.filter(source_reference=source_ref).filter(query)

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

                        point_count = points.count()

                        points_index = 0

                        while points_index < point_count:
                            for point in points[points_index:(points_index + 100)]:
                                properties = point.fetch_properties()

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

                                here_tz = pytz.timezone(tz_str)

                                if point.generator_identifier == 'webmunk-extension-element-show':
                                    row.append(1)
                                else:
                                    row.append(0)

                                row.append(properties.get('element-class', ''))

                                offset = properties.get('offset', {})

                                row.append(offset.get('top', ''))
                                row.append(offset.get('left', ''))

                                size = properties.get('size', {})

                                row.append(size.get('width', ''))
                                row.append(size.get('height', ''))

                                row.append(properties.get('url!', ''))
                                row.append(properties.get('page-title!', ''))

                                content = properties.get('element-content!', '')

                                row.append(remove_newlines(content))

                                writer.writerow(row)
                                outfile.flush()

                            points_index += 100

                            outfile.flush()

            return filename
    except: # pylint: disable=bare-except
        print(generator + ': ' + str(sources))

        traceback.print_exc()

    return None

def load_backup(filename, content):
    prefix = 'webmunk_backup_' + settings.ALLOWED_HOSTS[0]

    if filename.startswith(prefix) is False:
        return

    if 'json-dumpdata' in filename:
        filename = filename.replace('.json-dumpdata.bz2.encrypted', '.json')

        path = os.path.join(tempfile.gettempdir(), filename)

        with open(path, 'wb') as fixture_file:
            fixture_file.write(content)

        management.call_command('loaddata', path)

        os.remove(path)
    elif 'pd-bundle' in filename:
        bundle = DataBundle(recorded=timezone.now())

        if install_supports_jsonfield():
            bundle.properties = json.loads(content)
        else:
            bundle.properties = content

        bundle.save()
    else:
        print('[webmunk.pdk_api.load_backup] Unknown file type: ' + filename)

def incremental_backup(parameters): # pylint: disable=too-many-locals, too-many-statements
    to_transmit = []
    to_clear = []

    prefix = 'webmunk_backup_' + settings.ALLOWED_HOSTS[0]

    if 'start_date' in parameters:
        prefix += '_' + parameters['start_date'].date().isoformat()

    if 'end_date' in parameters:
        prefix += '_' + (parameters['end_date'].date() - datetime.timedelta(days=1)).isoformat()

    dumpdata_apps = (
    )

    backup_staging = tempfile.gettempdir()

    try:
        backup_staging = settings.PDK_BACKUP_STAGING_DESTINATION
    except AttributeError:
        pass

    for app in dumpdata_apps:
        print('[webmunk] Backing up ' + app + '...')
        sys.stdout.flush()

        buf = StringIO.StringIO()
        management.call_command('dumpdata', app, stdout=buf)
        buf.seek(0)

        database_dump = buf.read()

        buf = None

        gc.collect()

        compressed_str = bz2.compress(database_dump)

        database_dump = None

        gc.collect()

        filename = prefix + '_' + slugify(app) + '.json-dumpdata.bz2'

        path = os.path.join(backup_staging, filename)

        with open(path, 'wb') as fixture_file:
            fixture_file.write(compressed_str)

        to_transmit.append(path)

    # Using parameters, only backup matching DataPoint objects. Add PKs to to_clear for
    # optional deletion.

    bundle_size = 500

    try:
        bundle_size = settings.PDK_BACKUP_BUNDLE_SIZE
    except AttributeError:
        print('Define PDK_BACKUP_BUNDLE_SIZE in the settings to define the size of backup payloads.')

    action_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-action')
    click_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-click')
    hide_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-hide')
    show_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-show')
    log_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-log-elements')
    match_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-matched-rule')
    scroll_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-scroll-position')
    class_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-class-added')

    query = Q(generator_definition=action_def) | Q(generator_definition=click_def) | Q(generator_definition=hide_def) | Q(generator_definition=show_def) | Q(generator_definition=log_def) | Q(generator_definition=match_def) | Q(generator_definition=scroll_def) | Q(generator_definition=class_def) # pylint: disable=unsupported-binary-operation

    if 'start_date' in parameters:
        query = query & Q(recorded__gte=parameters['start_date'])

    if 'end_date' in parameters:
        query = query & Q(recorded__lt=parameters['end_date'])

    clear_archived = False

    if 'clear_archived' in parameters and parameters['clear_archived']:
        clear_archived = True

    print('[webmunk] Fetching count of data points...')
    sys.stdout.flush()

    count = DataPoint.objects.filter(query).count()

    index = 0

    while index < count:
        filename = prefix + '_data_points_' + str(index) + '_' + str(count) + '.webmunk-pd-bundle.bz2'

        print('[webmunk] Backing up data points ' + str(index) + ' of ' + str(count) + '...')
        sys.stdout.flush()

        bundle = []

        for point in DataPoint.objects.filter(query).order_by('recorded')[index:(index + bundle_size)]:
            bundle.append(point.fetch_properties())

            if clear_archived:
                to_clear.append('webmunk:' + str(point.pk))

        index += bundle_size

        compressed_str = bz2.compress(json.dumps(bundle).encode('utf-8'))

        path = os.path.join(backup_staging, filename)

        with open(path, 'wb') as compressed_file:
            compressed_file.write(compressed_str)

        to_transmit.append(path)

    return to_transmit, to_clear

def clear_points(to_clear):
    point_count = len(to_clear)

    for i in range(0, point_count):
        if (i % 1000) == 0:
            print('[webmunk] Clearing points ' + str(i) + ' of ' + str(point_count) + '...')
            sys.stdout.flush()

        point_id = to_clear[i]

        point_pk = int(point_id.replace('webmunk:', ''))

        DataPoint.objects.filter(pk=point_pk).delete()
