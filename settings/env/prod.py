from settings.base import *  
DEBUG = False
 
ALLOWED_HOSTS = [h.strip() for h in os.getenv("CRM_ALLOWED_HOSTS", "").split(",") if h.strip()]
 
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["CRM_DB_NAME"],
        "USER": os.environ["CRM_DB_USER"],
        "PASSWORD": os.environ["CRM_DB_PASSWORD"],
        "HOST": os.getenv("CRM_DB_HOST", "localhost"),
        "PORT": os.getenv("CRM_DB_PORT", "5432"),
    },
}
 
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CRM_CORS_ORIGINS", "").split(",") if o.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True