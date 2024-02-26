# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import json
import logging
import os
import re

from multiprocessing.pool import ThreadPool

import boto3

from botocore.config import Config

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from passive_data_kit.decorators import handle_lock
from passive_data_kit.models import DataPoint, DataGeneratorDefinition

def upload_point(client, upload_path, contents, s3_bucket):
    client.put_object(Body=contents, Bucket=s3_bucket, Key=upload_path)

    return None


class Command(BaseCommand):
    help = 'Pushes raw data points to Amazon S3'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--start_pk', type=int)

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals, too-many-statements
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

        last_point = DataPoint.objects.all().order_by('-pk').first()

        last_pk = last_point.pk

        logging.info('Fetched %s.' % last_pk)

        count_index = 0

        pool = ThreadPool(processes=25)

        async_results = []

        while count_index <= last_pk:
            if (count_index % 1000) == 0:
                logging.info('[%s] %s / %s', timezone.now(), count_index, last_pk)

            point = DataPoint.objects.filter(pk=count_index).only('generator_identifier', 'source', 'created', 'pk', 'properties').first()

            if point is not None:
                upload_path = '%s/%s/%s/%s-%s.json' % (settings.ALLOWED_HOSTS[0], point.source, point.created.date().isoformat(), point.generator_identifier, point.pk)
                contents = json.dumps(point.properties, indent=2).encode('utf-8')

                async_results.append(pool.apply_async(upload_point, [client, upload_path, contents, s3_bucket]))

            count_index += 1

            if len(async_results) >= 100:
                for result in async_results:
                    result.get()

                async_results = []

        pool.close()

        pool.join()
