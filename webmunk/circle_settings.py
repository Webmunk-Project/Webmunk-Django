import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'CHANGE-ME' # nosec

DEBUG = True

ALLOWED_HOSTS = [
	'webmunk.example.com'
]

ADMINS = [
	('Chris Karr', 'chris@audacious-software.com')
]

DATABASES = {
    'default': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'NAME':     'circle_test',
        'USER':     'root',
        'PASSWORD': '',
        'HOST':     'localhost',
        'PORT':     '',
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR + '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR + '/media/'

PDK_DASHBOARD_ENABLED = True

SITE_URL = 'https://' + ALLOWED_HOSTS[0]

ADDITIONAL_APPS = []
