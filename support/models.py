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
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            try:
                for keepa in metadata.get('keepa', []):
                    self.brand = keepa.get('brand', '')
                    self.updated = timezone.now()
            except AttributeError:
                pass

            self.save()

        return self.brand

    def fetch_root_category(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    return keepa.get('rootCategory', None)
                except AttributeError:
                    pass

        return None

    def fetch_category(self):
        category = ''

        if self.metadata is not None: # pylint: disable=too-many-nested-blocks
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    if keepa.get('categoryTree', None) is not None:
                        for category_item in keepa.get('categoryTree', []):
                            if category != '':
                                category = category + ' > '

                            category = category + category_item['name']
                except AttributeError:
                    pass

        return category

    def fetch_category_ids(self):
        category = ''

        if self.metadata is not None: # pylint: disable=too-many-nested-blocks
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    if keepa.get('categoryTree', None) is not None:
                        for category_item in keepa.get('categoryTree', []):
                            if category != '':
                                category = category + ' > '

                            category = category + str(category_item['catId'])
                except AttributeError:
                    pass

        return category

    def fetch_item_type(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    return keepa.get('type', None)
                except AttributeError:
                    pass

        return None

    def fetch_manufacturer(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    return keepa.get('manufacturer', None)
                except AttributeError:
                    pass

        return None

    def fetch_seller(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    seller_id = keepa.get('sellerIds', None)

                    if seller_id is None:
                        seller_id = keepa.get('buyBoxSellerId', None)

                    return seller_id
                except AttributeError:
                    pass

        return None

    def fetch_size(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    return keepa.get('size', None)
                except AttributeError:
                    pass

        return None

    def fetch_title(self):
        if self.metadata is not None:
            metadata = None

            try:
                metadata = self.cached_metadata
            except: # pylint: disable=bare-except
                metadata = json.loads(self.metadata)
                self.cached_metadata = metadata # pylint: disable=attribute-defined-outside-init

            for keepa in metadata.get('keepa', []):
                try:
                    return keepa.get('title', None)
                except AttributeError:
                    pass

        return None

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
