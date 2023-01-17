# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import AmazonASINItem

class Command(BaseCommand):
    help = 'Populates Amazon ASIN item metadata'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        for asin_item in AmazonASINItem.objects.filter(name=None).order_by('updated')[:25]:
            amazon_url = 'https://amazon.com/dp/%s' % asin_item.asin

            chrome_options = Options()
            chrome_options.add_argument("--headless")

            capabilities = webdriver.DesiredCapabilities.CHROME.copy()
            capabilities['goog:loggingPrefs'] = { 'browser':'ALL' }

            driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)

            driver.get(amazon_url)

            time.sleep(5)

            try:
                title_div = driver.find_element(By.ID, 'productTitle')

                asin_item.name = title_div.text

                category_div = driver.find_element(By.ID, 'wayfinding-breadcrumbs_container')

                asin_item.category = category_div.text

                while '\n' in asin_item.category:
                    asin_item.category = asin_item.category.replace('\n', ' ')

                while '\r' in asin_item.category:
                    asin_item.category = asin_item.category.replace('\r', ' ')

                while '  ' in asin_item.category:
                    asin_item.category = asin_item.category.replace('  ', ' ')

                print('FOUND: %s - %s / %s' % (asin_item.asin, asin_item.name, asin_item.category))

            except NoSuchElementException:
                print('FIELD NOT FOUND: %s' % asin_item.asin)

            asin_item.updated = timezone.now()
            asin_item.save()
