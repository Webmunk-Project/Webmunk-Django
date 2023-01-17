from django.db import models

class AmazonASINItem(models.Model):
    class Meta(object): # pylint: disable=old-style-class, no-init, too-few-public-methods, bad-option-value, useless-object-inheritance
        verbose_name = 'Amazon ASIN item'

    asin = models.CharField(max_length=1024, unique=True)

    name = models.CharField(max_length=1024, null=True, blank=True)
    category = models.CharField(max_length=1024, null=True, blank=True)

    added = models.DateTimeField()
    updated = models.DateTimeField()

    metadata = models.TextField(null=True, blank=True, max_length=(16 * 1024 * 1024))

    def __str__(self):
        return str(self.asin)
