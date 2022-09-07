# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime

import arrow

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from passive_data_kit.decorators import handle_lock
from passive_data_kit.models import ReportJobBatchRequest, DataSource

class Command(BaseCommand):
    help = 'Creates a nightly job to upload data to Dropbox.'

    def add_arguments(self, parser):
        parser.add_argument('--date',
                            type=str,
                            dest='date',
                            help='Date of app usage in YYY-MM-DD format')

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        now = timezone.now()

        if options['date'] is not None:
            now = arrow.get(options['date'] + 'T23:59:59+00:00').datetime

        requester = get_user_model().objects.get(username='s3-backup')

        yesterday = now.date() - datetime.timedelta(days=1)

        active_users = []

        for source in DataSource.objects.all().order_by('identifier'):
            if (source.identifier in active_users) is False:
                if source.should_suppress_alerts() is False:
                    active_users.append(source.identifier)

        parameters = {}
        parameters['sources'] = active_users

        parameters['generators'] = [
            'pdk-external-amazon-item',
            'webmunk-extension-class-added',
            'webmunk-extension-element-click',
            'webmunk-extension-matched-rule',
            'webmunk-extension-element-show',
            'webmunk-extension-element-hide',
            'webmunk-extension-log-elements',
            'webmunk-extension-scroll-position',
            'webmunk-visibility-export',
            'webmunk-extension-action',
        ]

        parameters['export_raw'] = False
        parameters['data_start'] = yesterday.strftime('%m/%d/%Y')
        parameters['data_end'] = yesterday.strftime('%m/%d/%Y')
        parameters['date_type'] = 'recorded'
        parameters['path'] = yesterday.strftime('%Y-%m-%d/')

        request = ReportJobBatchRequest(requester=requester, requested=now, parameters=parameters)
        request.save()
