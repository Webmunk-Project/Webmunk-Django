# pylint: disable=line-too-long

import datetime

from django import template

from django.conf import settings
from django.utils import timezone

register = template.Library()

@register.filter(name='needs_final_upload')
def needs_final_upload(data_request):
    followup_date = data_request.requested + datetime.timedelta(days=settings.WEBMUNK_DATA_FOLLOWUP_DAYS)

    if timezone.now() < followup_date:
        return False

    if data_request.data_files.filter(uploaded__gte=followup_date).count() == 0:
        return True

    return False

@register.filter(name='still_needs_uploads')
def still_needs_uploads(data_request):
    if data_request.data_files.all().count() == 0:
        return True

    if needs_final_upload(data_request):
        return True

    return False
