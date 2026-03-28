"""
Django settings for GreenCred — production-ready.
Local dev: DEBUG=True, SQLite, local media
Production (Railway): DEBUG=False, Cloudinary images, env-var Firebase
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-greencred-local-dev-change-me-in-production-12345'
)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.railway.app',
    'greencred-production.up.railway.app',
]

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'greencredapp',
]

# Cloudinary — only add if credentials are present
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
if CLOUDINARY_CLOUD_NAME:
    INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # MUST be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'greencredapp.middleware.FirebaseAuthMiddleware',
]

ROOT_URLCONF = 'greencred.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'greencred.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# On Railway, DATABASE_URL is set automatically when you add a PostgreSQL plugin.
# Falls back to SQLite locally.
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://greencred.web.app',
    'https://greencred.firebaseapp.com',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG   # open in local dev only

# ── Static Files ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media / Image Storage ──────────────────────────────────────────────────────
if CLOUDINARY_CLOUD_NAME:
    # Production: Cloudinary
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
        'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
    }
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/'
else:
    # Local dev: disk
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# ── Firebase Admin SDK ─────────────────────────────────────────────────────────
# Priority 1: FIREBASE_SERVICE_ACCOUNT env var (JSON string — for Railway)
# Priority 2: serviceAccountKey.json file (local dev)
# Priority 3: Demo mode (no Firebase)

FIREBASE_ENABLED = False

_firebase_sa_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT', '')
_firebase_sa_file = BASE_DIR / 'serviceAccountKey.json'

try:
    import firebase_admin
    from firebase_admin import credentials as fb_credentials

    if _firebase_sa_env:
        _cred_dict = json.loads(_firebase_sa_env)
        _cred = fb_credentials.Certificate(_cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(_cred)
        FIREBASE_ENABLED = True
        print('✅ Firebase: initialised from FIREBASE_SERVICE_ACCOUNT env var')

    elif _firebase_sa_file.exists():
        _cred = fb_credentials.Certificate(str(_firebase_sa_file))
        if not firebase_admin._apps:
            firebase_admin.initialize_app(_cred)
        FIREBASE_ENABLED = True
        print('✅ Firebase: initialised from serviceAccountKey.json')

    else:
        print('⚠️  Firebase: no credentials found — running in demo mode')

except ImportError:
    print('⚠️  firebase-admin not installed — running in demo mode')
except Exception as e:
    print(f'⚠️  Firebase init failed: {e} — running in demo mode')

# ── Production-only Security Headers ──────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True   # Railway's proxy handles HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Trust Railway's proxy for HTTPS detection
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
