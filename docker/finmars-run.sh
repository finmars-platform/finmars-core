#!/bin/sh

echo "Finmars initialization"

echo "set chmod 777 /var/log/finmars/"

chmod 777 /var/log/finmars/

echo "set chmod 777 /var/log/finmars/backend"

chmod 777 /var/log/finmars/backend

echo "Create django log file /var/log/finmars/backend/django.log"

touch /var/log/finmars/backend/django.log

echo "set chmod 777 /var/log/finmars/backend/django.log"

chmod 777 /var/log/finmars/backend/django.log

#mkdir /var/app/finmars_data
#chmod 777 /var/app/finmars_data

############################################

echo "Migrating"
python /var/app/manage.py migrate

#echo "Create cache table"
#
#/var/app-venv/bin/python /var/app/manage.py createcachetable

echo "Clear sessions"

python /var/app/manage.py clearsessions

echo "Collect static"

python /var/app/manage.py collectstatic -c --noinput

echo "Start celery"

export DJANGO_SETTINGS_MODULE=poms_app.settings
export C_FORCE_ROOT='true'

supervisord

supervisorctl start worker1
supervisorctl start worker2
supervisorctl start celerybeat

echo "Create admin user"

python /var/app/manage.py generate_super_user

echo "Run gunicorn"

python poms_app/print_finmars.py

#uwsgi /etc/uwsgi/apps-enabled/finmars.ini
gunicorn --config /var/app/poms_app/gunicorn-prod.py poms_app.wsgi

echo "Initialized"