# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json

from django.core.management.base import BaseCommand

from passive_data_kit.models import DataPoint

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-branches, too-many-statements
        points_count = DataPoint.objects.all().order_by('-pk').first().pk

        print('%s points' % points_count)

        points_index = 0

        counts = {}

        while points_index < points_count:
            print('%s / %s (%0.6f)' % (points_index, points_count, (points_index / points_count)))

            for source_ref in DataPoint.objects.filter(pk__gte=points_index, pk__lt=(points_index + 100000)).values_list('source', flat=True):
                source_count = counts.get(str(source_ref), 0)

                source_count += 1

                counts[str(source_ref)] = source_count

            points_index += 100000

            if (points_index % 1000000) == 0:
                print(json.dumps(counts, indent=2))

        print(json.dumps(counts, indent=2))
