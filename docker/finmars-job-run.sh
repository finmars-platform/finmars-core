#!/bin/sh

echo "Migrating"
python /var/app/manage.py migrate_all_schemes

# echo "Collect static"
# python /var/app/manage.py collectstatic -c --noinput