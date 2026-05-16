from __future__ import annotations

import logging
import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# settings/celery_app.py -> settings/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

logger.info("Celery is trying to load .env from: %s", ENV_FILE)

load_dotenv(dotenv_path=ENV_FILE, override=False)

if os.getenv("CRM_SECRET_KEY"):
    logger.info("Celery .env load success: CRM_SECRET_KEY is available.")
else:
    logger.warning(
        "Celery .env load warning: CRM_SECRET_KEY was not found after reading %s",
        ENV_FILE,
    )

env_id = os.getenv("CRM_ENV_ID", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{env_id}")

app = Celery("prostoi_crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
