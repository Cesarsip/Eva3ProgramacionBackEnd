"""
Configuración del proyecto PetCare - Clínica Veterinaria.

Los valores sensibles se leen desde variables de entorno (archivo .env en
desarrollo y variables del sistema/servidor en AWS EC2).
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga .env si existe (desarrollo local). En producción se usan variables
# de entorno definidas en systemd o exportadas por el sistema.
load_dotenv(BASE_DIR / '.env')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cambiar-esta-clave-en-produccion-petcare-2026'
)

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

# =====================================================================
# APLICACIONES
# =====================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # API REST, autenticación JWT y documentación OpenAPI
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',

    # Dominio PetCare
    'petcare.apps.PetcareConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'petcare_project.urls'

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
                'petcare.context_processors.student_footer_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'petcare_project.wsgi.application'

# =====================================================================
# BASE DE DATOS: POSTGRESQL
# =====================================================================
# La configuración real se toma de .env (desarrollo) o de variables de
# entorno (EC2). USE_SQLITE=1 solo se usa para pruebas aisladas rápidas.
if os.environ.get('USE_SQLITE', '').lower() in ('1', 'true', 'yes'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME', 'petcare_db'),
            'USER': os.environ.get('DB_USER', 'petcare_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }

AUTH_USER_MODEL = 'petcare.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# =====================================================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# =====================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

# =====================================================================
# SEGURIDAD PARA EL DESPLIEGUE DETRÁS DE NGINX (AWS EC2)
# =====================================================================
DJANGO_USE_HTTPS = os.environ.get('DJANGO_USE_HTTPS', '').lower() in ('1', 'true', 'yes')
if DJANGO_USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# =====================================================================
# DJANGO REST FRAMEWORK
# =====================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'petcare.serializers.CustomTokenObtainPairSerializer',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'PetCare | Gestión Veterinaria',
    'DESCRIPTION': (
        'API REST para la gestión de tutores, mascotas, citas médicas, fichas '
        'clínicas, vacunas y recordatorios de la clínica veterinaria PetCare.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'TAGS': [
        {'name': 'Autenticación', 'description': 'Registro e inicio de sesión con JWT.'},
        {'name': 'Tutores', 'description': 'CRUD de tutores responsables de las mascotas.'},
        {'name': 'Mascotas', 'description': 'CRUD de pacientes veterinarios.'},
        {'name': 'Profesionales', 'description': 'Veterinarios y horarios de atención.'},
        {'name': 'Citas', 'description': 'Agendamiento, disponibilidad y estados de citas.'},
        {'name': 'Fichas clínicas', 'description': 'Diagnósticos, tratamientos, recetas y exámenes.'},
        {'name': 'Vacunas', 'description': 'Aplicaciones de vacunas y próximas dosis.'},
        {'name': 'Recordatorios', 'description': 'Controles periódicos y avisos de vacunación.'},
    ],
}

# Datos del estudiante visibles en el footer de las plantillas.
STUDENT_DATA = {
    'NOMBRE_COMPLETO': 'CESAR ANTONIO AEDO ALVAREZ',
    'SECCION': 'IEC-N4-C2',
    'ANIO': '2026',
    'ASIGNATURA': 'Desarrollo Backend',
    'DOCENTE': 'Marcelo Alvarado',
    'PROYECTO': 'PetCare - Sistema de Gestión de Citas y Fichas Médicas',
}
