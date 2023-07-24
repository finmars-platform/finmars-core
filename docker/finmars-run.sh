#!/bin/sh

if [ -f /etc/ssl/certs/ca-certificate/ca.crt ]; then
    cat /etc/ssl/certs/ca-certificate/ca.crt >> /etc/ssl/certs/ca-certificates.crt
else
    echo "CA certificate file does not exist"
fi

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Finmars initialization"

if [ -z "$VAULT_TOKEN" ]; then
    echo "Warning! $VAULT_TOKEN is not set"
fi

# TODO refactor settings permissions
#echo "set chmod 777 /var/log/finmars/"

chmod 777 /var/log/finmars/

#echo "set chmod 777 /var/log/finmars/backend"

chmod 777 /var/log/finmars/backend

#echo "Create django log file /var/log/finmars/backend/django.log"

touch /var/log/finmars/backend/django.log

#echo "set chmod 777 /var/log/finmars/backend/django.log"

chmod 777 /var/log/finmars/backend/django.log

#mkdir /var/app/finmars_data
#chmod 777 /var/app/finmars_data

############################################

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Migrating..."
python /var/app/manage.py migrate
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Migration Done 💚"


#
#/var/app-venv/bin/python /var/app/manage.py createcachetable

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Clear sessions"

python /var/app/manage.py clearsessions

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Collect static"

python /var/app/manage.py collectstatic -c --noinput



export DJANGO_SETTINGS_MODULE=poms_app.settings
export C_FORCE_ROOT='true'

echo "[${timestamp}] Start celery"
supervisord

#supervisorctl start worker1
#supervisorctl start worker2
#supervisorctl start celerybeat

python manage.py clear_celery
python manage.py download_init_configuration

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Create admin user"

python /var/app/manage.py generate_super_user

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "[${timestamp}] Run Gunicorn Web Server"

python /var/app/poms_app/print_finmars.py

#uwsgi /etc/uwsgi/apps-enabled/finmars.ini
gunicorn --config /var/app/poms_app/gunicorn-prod.py poms_app.wsgi
