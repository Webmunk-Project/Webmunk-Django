import json

from django.db import models
from django.urls import reverse
from django.utils import timezone

class AmazonASINItem(models.Model):
    class Meta(object): # pylint: disable=old-style-class, no-init, too-few-public-methods, bad-option-value, useless-object-inheritance
        verbose_name = 'Amazon ASIN item'

    asin = models.CharField(max_length=1024, unique=True)

    name = models.CharField(max_length=1024, null=True, blank=True)
    category = models.CharField(max_length=1024, null=True, blank=True)
    brand = models.CharField(max_length=1024, null=True, blank=True)
    seller = models.CharField(max_length=1024, null=True, blank=True)

    added = models.DateTimeField()
    updated = models.DateTimeField()

    metadata = models.TextField(null=True, blank=True, max_length=(16 * 1024 * 1024))

    def __str__(self):
        return str(self.asin)

    def get_absolute_url(self):
        return reverse('asin_json', kwargs={'asin': self.asin})

    def fetch_brand(self):
        if self.brand is None and self.metadata is not None:
            metadata = json.loads(self.metadata)

            try:
                for keepa in metadata.get('keepa', []):
                    self.brand = keepa.get('brand', '')
                    self.updated = timezone.now()
            except AttributeError:
                pass

            self.save()

        return self.brand

    def file_path(self):
        try:
            json.loads(self.metadata)

            return '%s/%s.json' % (self.asin[:4], self.asin) # pylint: disable=unsubscriptable-object
        except: # pylint: disable=bare-except # nosec
            pass

        return ''

    def file_content(self):
        try:
            metadata = json.loads(self.metadata)

            return json.dumps(metadata, indent=2, ignore_nan=True, default=None)
        except: # pylint: disable=bare-except # nosec
            pass

        return ''
