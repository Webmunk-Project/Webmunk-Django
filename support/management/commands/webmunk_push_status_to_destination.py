# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import logging
import os
import sys

from multiprocessing.pool import ThreadPool

import boto3

from botocore.config import Config

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from passive_data_kit.models import DataPoint, DataGeneratorDefinition

def upload_point(client, upload_path, contents, s3_bucket):
    client.put_object(Body=contents, Bucket=s3_bucket, Key=upload_path)

class Command(BaseCommand):
    help = 'Pushes raw data points to Amazon S3'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--start-pk', type=int, default=0)
        parser.add_argument('--end-pk', type=int, default=-1)

    # @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        verbosity = options.get('verbosity', 0)

        if verbosity == 0:
            level = logging.ERROR
        elif verbosity == 1:
            level = logging.WARN
        elif verbosity == 2:
            level = logging.INFO
        else:
            level = logging.DEBUG

        logging.basicConfig(level=level, format='%(message)s')

        upload_user = get_user_model().objects.get(username=options['username'])

        destination = upload_user.pdk_report_destinations.first()

        parameters = destination.fetch_parameters()

        aws_config = Config(
            region_name=parameters['region'],
            retries={'max_attempts': 10, 'mode': 'standard'},
            max_pool_connections=25
        )

        os.environ['AWS_ACCESS_KEY_ID'] = parameters['access_key_id']
        os.environ['AWS_SECRET_ACCESS_KEY'] = parameters['secret_access_key']

        client = boto3.client('s3', config=aws_config)

        s3_bucket = parameters['bucket']

        logging.info('Fetching last point...')

        definition = DataGeneratorDefinition.definition_for_identifier('pdk-system-status')

        point_pks = DataPoint.objects.filter(generator_definition=definition).values_list('pk', flat=True)

        logging.info('Fetched %s.', len(point_pks))

        pool = ThreadPool(processes=25)

        async_results = []

        sys.stdout.flush()

        count_index = 0

        for point_pk in point_pks:
            if (count_index % 1000) == 0:
                logging.info('[%s] %s / %s', timezone.now(), count_index, len(point_pks))

            point = DataPoint.objects.filter(pk=point_pk).only('generator_identifier', 'source', 'created', 'pk', 'properties').first()

            upload_path = '%s/%s/%s/%s-%s.json' % (settings.ALLOWED_HOSTS[0], point.source, point.created.date().isoformat(), point.generator_identifier, point.pk)
            contents = json.dumps(point.properties, indent=2).encode('utf-8')

            async_results.append(pool.apply_async(upload_point, [client, upload_path, contents, s3_bucket]))

            count_index += 1

            if len(async_results) >= 100:
                for result in async_results:
                    result.get()

                async_results = []

        for result in async_results:
            result.get()

        pool.close()

        pool.join()
