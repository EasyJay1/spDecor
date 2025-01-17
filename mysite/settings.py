from pathlib import Path
import os

# Base directory of the project
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Basic settings
APPEND_SLASH = False
SECRET_KEY = 's_8&hc^&p-k$ac(zwv#6c8n#hzg#)9d548wg)tcrg#16)deca!'
DEBUG = True
ALLOWED_HOSTS = []

# Flutterwave settings
FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-926306b003d0494a2b47b2172cb90b92-X'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.facebook',
    'blogapp',  # Ensure this points to the correct path


]

# Social account providers settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': '630273984994-ae5i9kv8p6v0ik8tqiicupsuu7g01g23.apps.googleusercontent.com',
            'secret': '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',
            'key': ''
        }
    }
}

# Middleware settings
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'blogapp.middleware.EventViewTrackingMiddleware',
]

# URL configuration
ROOT_URLCONF = 'mysite.urls'
SITE_ID = 1

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [],
        },
    },
]

# WSGI application
WSGI_APPLICATION = 'mysite.wsgi.application'

# Database settings (comment out the unused database configuration)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Uncomment if using PostgreSQL
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'railway',
#         'USER': 'postgres',
#         'HOST': 'containers-us-west-178.railway.app',
#         'PORT': '7344',
#     }
# }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files settings
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login and email settings

LOGIN_REDIRECT_URL = 'continue_booking'
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_TIMEOUT = 15
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'jamesstarlit@gmail.com'  # Replace with your Gmail email address
EMAIL_HOST_PASSWORD = 'yzat ihex vbuc cihn'  # Use your Gmail password or App Password
DEFAULT_FROM_EMAIL = 'noreply@jay.com'  # Replace with your sender email address
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[JAY TECHnLOGIC]'

# Allauth email settings
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
# settings.py

AUTH_USER_MODEL = 'blogapp.CustomUser'
# ACCOUNT_FORMS settings
ACCOUNT_FORMS = {
    'signup': 'blogapp.forms.CustomSignupForm',
}