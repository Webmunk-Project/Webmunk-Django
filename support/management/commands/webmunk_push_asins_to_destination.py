# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from passive_data_kit.decorators import handle_lock

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--start_pk', type=int)

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-locals, too-many-statements

        upload_user = get_user_model().objects.get(username=options['username'])

        asin_items_pks = AmazonASINItem.objects.all().order_by('pk').values_list('pk', flat=True)

        asins_uploaded = 0
        asins_total = len(asin_items_pks)

        for asin_item_pk in asin_items_pks:
            asin_item = AmazonASINItem.objects.get(pk=asin_item_pk)

            file_path = asin_item.file_path()

            if file_path != '':
                for destination in upload_user.pdk_report_destinations.all():
                    upload_path = '%s/%s/%s' % ('asin_direct_uploads', settings.ALLOWED_HOSTS[0], file_path)

                    if (asins_uploaded % 100) == 0:
                        logging.warning('Uploading %s (%s) [%s / %s / %s]...', upload_path, asin_item_pk, asins_uploaded, asins_total, timezone.now())

                    destination.upload_file_contents(upload_path, asin_item.file_content())

                    asins_uploaded  += 1
            else:
                logging.warning('Skipping %s (%s). No content to upload.', asin_item.asin, asin_item_pk)
