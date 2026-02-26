import os
import sys
from dotenv import load_dotenv

def main():
    load_dotenv('settings/.env')
    
    env_id = os.getenv('CRM_ENV_ID', 'local')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'settings.env.{env_id}')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()