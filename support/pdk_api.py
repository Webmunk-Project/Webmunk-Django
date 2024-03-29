# pylint: disable=line-too-long, no-member, too-many-lines

import bz2
import csv
import datetime
import gc
import gzip
import importlib
import io
import json
import logging
import os
import sys
import tempfile
import traceback

from io import StringIO

import arrow
import pytz
import zipstream

from past.utils import old_div

from django.conf import settings
from django.core import management
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from passive_data_kit.models import DataPoint, DataSource, DataGeneratorDefinition, DataSourceReference, DataBundle, install_supports_jsonfield

from .models import AmazonASINItem

def remove_newlines(text_block):
    results = ''.join(text_block.splitlines())

    return results

def fetch_asin_file_from_pk(asin_pk):
    asin_item = AmazonASINItem.objects.get(pk=asin_pk)

    return asin_item.file_content()

def fetch_asin_file(asin_pk):
    yield fetch_asin_file_from_pk(asin_pk)

def compile_report(generator, sources, data_start=None, data_end=None, date_type='created'): # pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-return-statements
    try:
        generator_module = importlib.import_module('.generators.' + generator.replace('-', '_'), package='support')

        output_file = None

        try:
            output_file = generator_module.compile_report(generator, sources, data_start=data_start, data_end=data_end, date_type=date_type)
        except TypeError:
            logging.error('TODO: Update %s.compile_report to support data_start, data_end, and date_type parameters!', generator)

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
                    'Page ID',
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

                        logging.debug('[%s] Fetching point PKs...', source)

                        point_pks = list(points.values_list('pk', date_sort.replace('-', '')))

                        point_pks.sort(key=lambda pair: pair[1], reverse=True)

                        points_count = len(point_pks)

                        logging.debug('[%s] %d PKs fetched.', source, points_count)

                        # points = points.order_by(date_sort)

                        # points_count = points.count()

                        points_index = 0

                        while points_index < points_count:
                            logging.debug('[%s] %s/%s', source, points_index, points_count)

                            for point_pk in point_pks[points_index:(points_index + 10000)]:
                                point = DataPoint.objects.get(pk=point_pk[0])

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
                                row.append(properties.get('page-id', ''))

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

                                row.append(properties.get('url!', properties.get('url*', '')))
                                row.append(properties.get('page-title!', properties.get('page-title*', '')))

                                content = properties.get('element-content!', properties.get('element-content*', ''))

                                row.append(remove_newlines(content))

                                writer.writerow(row)
                                outfile.flush()

                            points_index += 10000

                            outfile.flush()

            return filename

        if generator == 'webmunk-asin-details':
            now = arrow.get()

            filename = tempfile.gettempdir() + os.path.sep + 'asin_items_' + str(now.timestamp()) + str(old_div(now.microsecond, 1e6)) + '.zip'

            stream = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_BZIP2)

            # with ZipFile(filename, 'w', allowZip64=True) as export_file:
            data_filename = tempfile.gettempdir() + os.path.sep + generator + '.txt'

            with io.open(data_filename, 'w', encoding='utf-8') as outfile:
                writer = csv.writer(outfile, delimiter='\t')

                columns = [
                    'ASIN',
                    'Type',
                    'Brand',
                    'Manufacturer',
                    'Size',
                    'Seller',
                    'Title',
                    'Root Category',
                    'Category Tree',
                    'Category Tree IDs',
                    'Date Added',
                    'Date Updated',
                    'Data URL',
                    'File Path',
                ]

                writer.writerow(columns)

                asin_items_pks = AmazonASINItem.objects.all().order_by('pk').values_list('pk', flat=True)

                logging.info('Fetching count...')

                item_count = len(asin_items_pks) # asin_items.count()
                item_index = 0

                logging.info('Fetched count: %s', item_count)

                here_tz = pytz.timezone(settings.TIME_ZONE)

                items_exported = 0

                while item_index < item_count:
                    for asin_item_pk in asin_items_pks[item_index:(item_index + 100)]:
                        asin_item = AmazonASINItem.objects.get(pk=asin_item_pk)

                        row = []

                        if (items_exported % 500) == 0:
                            logging.info('%s / %s', items_exported, item_count)

                        row.append(asin_item.asin)

                        row.append(asin_item.fetch_item_type())
                        row.append(asin_item.fetch_brand())
                        row.append(asin_item.fetch_manufacturer())
                        row.append(asin_item.fetch_size())

                        row.append(asin_item.fetch_seller())
                        row.append(asin_item.fetch_title())
                        row.append(asin_item.fetch_root_category())
                        row.append(asin_item.fetch_category())
                        row.append(asin_item.fetch_category_ids())

                        added = asin_item.added.astimezone(here_tz)
                        updated = asin_item.updated.astimezone(here_tz)

                        row.append(added.isoformat())
                        row.append(updated.isoformat())

                        if asin_item.asin is not None and asin_item.asin != '':
                            row.append('https://%s%s' % (settings.ALLOWED_HOSTS[0], asin_item.get_absolute_url()))
                        else:
                            row.append('(No URL - missing ASIN)')

                        asin_path = asin_item.file_path()

                        row.append(asin_path)

                        if asin_path != '':
                            stream.write_iter(asin_path, fetch_asin_file(asin_item.pk))

                        writer.writerow(row)

                        items_exported += 1

                    outfile.flush()

                    item_index += 100

                    outfile.flush()

            # export_file.write(data_filename, '%s.txt' % slugify(generator))

            stream.write(data_filename, '%s.txt' % slugify(generator))

            logging.info('Writing %s...', filename)

            with open(filename, 'wb') as export_file:
                for data in stream:
                    export_file.write(data)

            os.remove(data_filename)

            return filename
    except: # pylint: disable=bare-except
        logging.error('%s: %s', generator, sources)

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
        logging.error('[webmunk.pdk_api.load_backup] Unknown file type: %s', filename)

def incremental_backup(parameters): # pylint: disable=too-many-locals, too-many-statements
    to_transmit = []
    to_clear = []

    prefix = 'webmunk_backup_' + settings.ALLOWED_HOSTS[0]

    if 'start_date' in parameters:
        prefix += '_' + parameters['start_date'].date().isoformat()

    if 'end_date' in parameters:
        prefix += '_' + (parameters['end_date'].date() - datetime.timedelta(days=1)).isoformat()

    dumpdata_apps = ()

    backup_staging = tempfile.gettempdir()

    try:
        backup_staging = settings.PDK_BACKUP_STAGING_DESTINATION
    except AttributeError:
        pass

    for app in dumpdata_apps:
        logging.info('[webmunk] Backing up %s...', app)
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
        logging.error('Define PDK_BACKUP_BUNDLE_SIZE in the settings to define the size of backup payloads.')

    action_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-action')
    click_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-click')
    hide_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-hide')
    show_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-element-show')
    log_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-log-elements')
    match_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-matched-rule')
    scroll_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-scroll-position')
    class_def = DataGeneratorDefinition.definition_for_identifier('webmunk-extension-class-added')

    data_types = [
        action_def,
        click_def,
        hide_def,
        show_def,
        log_def,
        match_def,
        scroll_def,
        class_def,
    ]

    for data_type in data_types:
        query = Q(generator_definition=data_type)

        if 'start_date' in parameters:
            query = query & Q(recorded__gte=parameters['start_date'])

        if 'end_date' in parameters:
            query = query & Q(recorded__lt=parameters['end_date'])

        clear_archived = False

        if 'clear_archived' in parameters and parameters['clear_archived']:
            clear_archived = True

        logging.info('[webmunk] Fetching count of data points (%s)...', data_type)
        sys.stdout.flush()

        point_pks = DataPoint.objects.filter(query).values_list('pk', flat=True)

        # count = DataPoint.objects.filter(query).count()

        count = len(point_pks)

        index = 0

        while index < count:
            filename = '%s_%s_data_points_%s_%s.webmunk-pd-bundle.gz' % (prefix, data_type, index, count)

            logging.info('[webmunk] Backing up data points %s of %s (%s)...', index, count, data_type)
            sys.stdout.flush()

            bundle = []

            # for point in DataPoint.objects.filter(query).order_by('pk')[index:(index + bundle_size)]:
            for point_pk in point_pks[index:(index + bundle_size)]:
                point = DataPoint.objects.get(pk=point_pk)

                bundle.append(point.fetch_properties())

                if clear_archived:
                    to_clear.append('webmunk:' + str(point.pk))

            index += bundle_size

            # print('[webmunk] Dumping %s...' % len(bundle))
            # sys.stdout.flush()

            to_compress = json.dumps(bundle) # .encode('utf-8')

            # print('[webmunk] Compressing %s...' % len(to_compress))
            # sys.stdout.flush()

            compressed_str = gzip.compress(bytes(to_compress, 'utf-8'), compresslevel=1)

            # compressed_str = bz2.compress(to_compress, compresslevel=1)

            path = os.path.join(backup_staging, filename)

            # print('[webmunk] Writing %s...' % len(compressed_str))
            # sys.stdout.flush()

            with open(path, 'wb') as compressed_file:
                compressed_file.write(compressed_str)

            to_transmit.append(path)

    return to_transmit, to_clear

def clear_points(to_clear):
    points_count = len(to_clear)

    for i in range(0, points_count):
        if (i % 1000) == 0:
            logging.info('[webmunk] Clearing points %d of %d...', i, points_count)
            sys.stdout.flush()

        point_id = to_clear[i]

        point_pk = int(point_id.replace('webmunk:', ''))

        DataPoint.objects.filter(pk=point_pk).delete()

def postgres_additions():
    return (
        'CREATE INDEX passive_data_kit_source_reference_id_datapoint_generator_definition_id_created_recorded_id_custom ON public.passive_data_kit_datapoint USING btree (source_reference_id, generator_definition_id, created, recorded, id);',
        'CREATE INDEX passive_data_kit_datapoint_id_recorded_created_generator_definition_id_source_reference_id_custom ON public.passive_data_kit_datapoint USING btree (id, recorded, created, generator_definition_id, source_reference_id);',
        'CREATE INDEX passive_data_kit_datapoint_id_recorded_created_custom ON public.passive_data_kit_datapoint USING btree (id, recorded, created);',
    )
