#!/bin/sh

if [ -f /etc/ssl/certs/finmars-internal-ca-certificate/ca.crt ]; then
    cat /etc/ssl/certs/finmars-internal-ca-certificate/ca.crt >> /usr/local/share/ca-certificates/finmars-internal-ca-certificates.crt
else
    echo "finmars.internal CA certificate file does not exist"
fi

if [ -f /etc/ssl/certs/private-ca-certificate/tls.crt ]; then
    cat /etc/ssl/certs/private-ca-certificate/tls.crt >> /usr/local/share/ca-certificates/private-ca-certificates.crt
else
    echo "Private CA certificate file does not exist"
fi

update-ca-certificates # update ca certs

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



#echo "[${timestamp}] Start celery"

#!/bin/bash

#: "${WORKERS:="2"}"
#
#
#if [ "$WORKERS" = "4" ]
#then
#    rm /etc/supervisor/conf.d/celery_2_workers.conf
#elif [ "$WORKERS" = "2" ]
#then
#    rm /etc/supervisor/conf.d/celery_4_workers.conf
#else
#    echo "Invalid number of workers specified"
#    exit 1
#fi
#
#echo "Number of workers: $WORKERS"
#
#supervisord

#supervisorctl start worker1
#supervisorctl start worker2
#supervisorctl start celerybeat

#uwsgi /etc/uwsgi/apps-enabled/finmars.ini
#gunicorn --config /var/app/poms_app/gunicorn-prod.py poms_app.wsgi

# Default value is "backend"
: "${INSTANCE_TYPE:=backend}"



if [ "$INSTANCE_TYPE" = "backend" ]; then

  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Migrating..."
  python /var/app/manage.py migrate
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Migration Done 💚"

  #/var/app-venv/bin/python /var/app/manage.py createcachetable

  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Clear sessions"

  python /var/app/manage.py clearsessions

  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Collect static"

  python /var/app/manage.py collectstatic -c --noinput

  export DJANGO_SETTINGS_MODULE=poms_app.settings
  export C_FORCE_ROOT='true'

  python manage.py clear_celery
  python manage.py deploy_default_worker

  python manage.py download_init_configuration

  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Create admin user"

  python /var/app/manage.py generate_super_user

  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[${timestamp}] Run Gunicorn Web Server"

  python /var/app/poms_app/print_finmars.py

  gunicorn --config /var/app/poms_app/gunicorn-prod.py poms_app.wsgi

elif [ "$INSTANCE_TYPE" = "worker" ]; then

  # Environment variables for the worker
  : "${WORKER_NAME:=worker1}"
  : "${QUEUES:=backend-general-queue,backend-background-queue}"

  cd /var/app && celery --app poms_app worker  --loglevel=INFO --soft-time-limit=3000 -n "$WORKER_NAME" -Q "$QUEUES"

elif [ "$INSTANCE_TYPE" = "scheduler" ]; then

  cd /var/app && celery --app poms_app beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
  echo "Missing or unsupported value for INSTANCE_TYPE environment variable. Exiting."
  exit 1
fi