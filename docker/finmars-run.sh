#!/bin/sh

USE_CELERY="${USE_CELERY:-False}"
USE_FILEBEATS="${USE_FILEBEATS:-False}"
USE_FLOWER="${$USE_FLOWER:-False}"
BASE_API_URL="${$BASE_API_URL:-False}"
RABBITMQ_HOST="${$RABBITMQ_HOST:-False}"

echo "Finmars initialization"

echo "Create Finmars log folder /var/log/finmars/"

mkdir /var/log/finmars/

echo "set chmod 777 /var/log/finmars/"

chmod 777 /var/log/finmars/

echo "Create django log file /var/log/finmars/django.log"

touch /var/log/finmars/django.log

echo "set chmod 777 /var/log/finmars/django.log"

chmod 777 /var/log/finmars/django.log


echo "Create known_hosts for SFTP"

mkdir /var/app/.ssh
touch /var/app/.ssh/known_hosts
chmod 777 /var/app/.ssh
chmod 777 /var/app/.ssh/known_hosts

############################################

echo "Migrating"

/var/app-venv/bin/python /var/app/manage.py migrate

#echo "Create cache table"
#
#/var/app-venv/bin/python /var/app/manage.py createcachetable

echo "Clear sessions"

/var/app-venv/bin/python /var/app/manage.py clearsessions

echo "Collect static"

/var/app-venv/bin/python /var/app/manage.py collectstatic -c --noinput

if [ $USE_CELERY == "True" ];
then

    echo "Start celery"

    export DJANGO_SETTINGS_MODULE=poms_app.settings

    /etc/init.d/celeryd start

    echo "Start celerybeat"

    export DJANGO_SETTINGS_MODULE=poms_app.settings

    /etc/init.d/celerybeat start

fi

if [ $USE_FILEBEATS == "True" ];
then

    echo "Run Filebeat"

    service filebeat start

fi


if [ $USE_FLOWER == "True" ];
then

    echo "Run Flower"

    cd /var/app && nohup /var/app-venv/bin/celery --app poms_app --broker=amqp://guest:guest@$RABBITMQ_HOST// flower  --url-prefix=$BASE_API_URL/flower --port=5566 &

fi

echo "Create admin user"

/var/app-venv/bin/python /var/app/manage.py generate_super_user

echo "Run uwsgi"

/var/app-venv/bin/uwsgi /etc/uwsgi/apps-enabled/finmars.ini

echo "Initialized"