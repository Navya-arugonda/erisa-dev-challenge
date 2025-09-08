#!/usr/bin/env bash
set -euo pipefail

# 1) Migrations
python manage.py migrate --noinput

# 2) Seed data (only if there are no claims yet)
python manage.py shell <<'PYCODE'
from claims.models import Claim
from django.core.management import call_command
from django.conf import settings
import os

if not Claim.objects.exists():
    list_csv   = os.getenv('SEED_LIST',   str((settings.BASE_DIR/'claim_list_data.csv')))
    detail_csv = os.getenv('SEED_DETAIL', str((settings.BASE_DIR/'claim_detail_data.csv')))
    call_command('import_erisa_data', '--list', list_csv, '--detail', detail_csv, '--mode', 'skip')
PYCODE

# 3) Ensure an admin user exists
python manage.py shell <<'PYCODE'
from django.contrib.auth import get_user_model
import os
U = get_user_model()
u = os.getenv('ADMIN_USER',  'admin')
p = os.getenv('ADMIN_PASS',  'admin123')
e = os.getenv('ADMIN_EMAIL', 'admin@example.com')
U.objects.filter(username=u).exists() or U.objects.create_superuser(u, e, p)
PYCODE

# 4) Start Gunicorn
exec gunicorn core.wsgi:application --log-file -
