# pylint: disable=line-too-long

import datetime

from django import template

from django.conf import settings

register = template.Library()

@register.filter(name='needs_final_upload')
def needs_final_upload(data_request):
    followup_date = data_request.requested + datetime.timedelta(days=settings.WEBMUNK_DATA_FOLLOWUP_DAYS)

    if data_request.data_files.filter(uploaded__gte=followup_date).count() == 0:
        return True

    return False
