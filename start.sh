#!/usr/bin/env bash

set -euo pipefail

#colors
GREEN='\033[0;32m'
RED="\033[0;31m"
NC="\033[0m"

ok() { echo -e "${GREEN} $1${NC}"; }
fail() { echo -e "${RED} $1${NC}"; exit 1;}

# 1) Check required environment variables from settings/.env.
if [ ! -f "settings/.env" ]; then
    fail "settings/.env not found. Create it before running this script."
fi

source settings/.env
export DJANGO_SETTINGS_MODULE="settings.env.${CRM_ENV_ID}"

REQUIRED_VARS=("CRM_SECRET_KEY" "CRM_ENV_ID")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        fail "$var is not set in settings/.env"
    fi
done

ok "Environment variables checked."

# 2) Create virtualenv if not exists and install dependencies.

if [ ! -d "venv" ]; then 
    python3 -m venv venv 
    ok "Virtualenv created."
else 
    ok "Virtualenv already exists, skipping."
fi

source venv/bin/activate 

pip install --quiet --upgrade pip
pip install --quiet -r requirements/dev.txt

ok "Dependencies installed from requirements/dev.txt."

# 3) run migrations 
python manage.py migrate --noinput
ok "Migrations applied."

# 4) collect ststic files 
python manage.py collectstatic --noinput --clear
ok "Static files collected."

# 5) Compile messages (i18n)
if find locale -name "*.po" 2>/dev/null | grep -q "."; then
    python manage.py compilemessages -v 0
    ok "Messages compiled."
else 
    ok "no .po files found, skipping compilemessages"
fi

# 6) create superuser if not exists

python manage.py shell <<'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email="admin@crm.com").exists():
    User.objects.create_superuser(
        email = "admin@crm.com",
        first_name = "Admin",
        last_name = "Admin",
        password = "admin123",
    )
    print("Superuser created: admin@crm.com / admin123")
else:
    print("Superuser already exists, skipping.")
EOF
ok "Superuser check done."

# 7) populate database
python manage.py fill_db
ok "Database populated."

# 8) THE END
echo " python manage.py runserver"
echo " API:     http://127.0.0.1:8000/api/ "
echo " Swagger: http://127.0.0.1:8000/api/docs/"
echo " ReDoc:   http://127.0.0.1:8000/api/redoc/"
echo " Admin:   http://127.0.0.1:8000/admin/"
echo " Start complete"