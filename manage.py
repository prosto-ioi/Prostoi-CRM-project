from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> None:
    """Run an administrative task chosen from ``sys.argv``."""
    # Load .env BEFORE importing anything Django-related — settings depend on it.
    load_dotenv("settings/.env")

    env_id = os.getenv("CRM_ENV_ID", "local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{env_id}")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH? Did you forget to activate a "
            "virtual environment?",
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()