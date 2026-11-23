
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv


#Payment Gateway
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR /".env")
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',"127.0.0.1"
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
      "corsheaders",
        "rest_framework_simplejwt.token_blacklist",

    'axes',
    'accounts.apps.AccountsConfig',
    'categories',
    'products',
    'cart',
    'orders',





]

AUTHENTICATION_BACKENDS=[
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware'
]

REST_FRAMEWORK={
    "DEFAULT_AUTHENTICATION_CLASSES":(
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
        
    "DEFAULT_THROTTLE_CLASSES":[
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',

    ],
    "DEFAULT_THROTTLE_RATES":{
        'anon':'15/minute',
        'user':'60/minute',

    },
    "DEFAULT_PAGINATION_CLASS":'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE':10
                    

}

SIMPLE_JWT={
    "ACCESS_TOKEN_LIFETIME":timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME":timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":True,
    "BLACKLIST_AFTER_ROTATION":True
}

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'ecommerce'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",             # default MySQL port
        }  
    } 
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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




# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'


AUTH_USER_MODEL="accounts.User"

MEDIA_URL="/media/"
MEDIA_ROOT=BASE_DIR / "media"

# Email Configurations
EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST=os.getenv("EMAIL_HOST","")
EMAIL_PORT=int(os.getenv("EMAIL_PORT",587))

EMAIL_HOST_USER=os.getenv("EMAIL_HOST_USER","")
EMAIL_HOST_PASSWORD=os.getenv("EMAIL_HOST_PASSWORD","")

EMAIL_USE_TLS=os.getenv("EMAIL_USE_TLS","false").lower()=="true"


EMAIL_USE_SSL=os.getenv("EMAIL_USE_SSL","false").lower()=="true"

DEFAULT_FROM_EMAIL=os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Ecommerce Store <no-reply@example.com>",
)

EMAIL_TIMEOUT=10


AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=timedelta(minutes=30)
AXES_USE_ATTEMPT_EXPIRATION=True
AXES_LOCKOUT_PARAMETERS=[
    ["username","ip_address"]
]
AXES_RESET_ON_SUCCESS=True


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
CORS_ALLOW_CREDENTIALS=True

CSRF_TRUSTED_ORIGINS=[
    "http://localhost:5173",
]
CSRF_COOKIE_SAMESIT="Lax"
CSRF_COOKIE_SECURE=not DEBUG