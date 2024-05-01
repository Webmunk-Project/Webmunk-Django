# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import logging
import os
import random
import time

import boto3

from botocore.config import Config

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from passive_data_kit.models import DataPoint

def upload_point(client, upload_path, contents, s3_bucket):
    client.put_object(Body=contents, Bucket=s3_bucket, Key=upload_path)

class Command(BaseCommand):
    help = 'Pushes raw data points to Amazon S3'

    def add_arguments(self, parser):
        parser.add_argument('username')

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

        last_point = DataPoint.objects.all().order_by('-pk').first()

        last_pk = last_point.pk

        logging.info('Fetched %s.', last_pk)

        count_index = 0

        while True:
            point_pk = random.randrange(last_pk) # nosec

            point = DataPoint.objects.filter(pk=point_pk).only('generator_identifier', 'source', 'created', 'pk', 'properties').first()

            if (count_index % 100) == 0:
                logging.info('[%s - %s] %s / %s', timezone.now(), point_pk, count_index, last_pk)

            if point is not None and point.generator_identifier != 'pdk-system-status':
                upload_path = '%s/%s/%s/%s-%s.json' % (settings.ALLOWED_HOSTS[0], point.source, point.created.date().isoformat(), point.generator_identifier, point.pk)

                response = client.get_object(Bucket=s3_bucket, Key=upload_path)

                obj_str = response['Body'].read().decode('utf-8')

                obj_dict = json.loads(obj_str)

                if obj_dict != point.properties:
                    logging.info('%s[%s]: %s', upload_path, point_pk, obj_str)

            count_index += 1

            time.sleep(1)
