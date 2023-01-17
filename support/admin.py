from django.contrib import admin

from .models import AmazonASINItem

@admin.register(AmazonASINItem)
class AmazonASINItemAdmin(admin.ModelAdmin):
    list_display = ('asin', 'name', 'category', 'added', 'updated',)

    list_filter = ('added', 'updated', 'category',)

    search_fields = ('name', 'category', 'asin',)
