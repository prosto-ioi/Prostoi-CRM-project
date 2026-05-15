#!/usr/bin/env bash

set -euo pipefail

#colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
NC = "\033[0m"

ok() { echo -e "${GREEN} $1${NC}"; }
fail() {echo -e "${RED} $1${NC}"; exit 1;}

# 1) Check required environment variables from settings/.env.
if [ ! -f "settings/.env" ]; then
    fail "settings/.env not found. Create it before running this script."
fi

source settings/.env

REQUIRED_VARS=("CRM_SECRET_KEY" "CRM_ENV_ID")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}"]; then 
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

pip install --upgrade pip
pip install -r requirements/dev.txt

ok "Dependencies installed from requirements/dev.txt."
