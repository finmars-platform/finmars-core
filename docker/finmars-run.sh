#!/bin/sh

USE_CELERY="${USE_CELERY:-False}"
USE_FILEBEATS="${USE_FILEBEATS:-False}"
USE_FLOWER="${$USE_FLOWER:-False}"
BASE_API_URL="${$BASE_API_URL:-False}"
RABBITMQ_HOST="${$RABBITMQ_HOST:-False}"
FAKE_MIGRATE="${FAKE_MIGRATE:-False}"

echo "Finmars initialization"


echo "set chmod 777 /var/log/finmars/"

chmod 777 /var/log/finmars/

echo "Create django log file /var/log/finmars/django.log"

touch /var/log/finmars/django.log

echo "set chmod 777 /var/log/finmars/django.log"

chmod 777 /var/log/finmars/django.log


############################################

if [ $FAKE_MIGRATE == "True" ];
then
  echo "Fake Migrating"
  python /var/app/manage.py drop_django_migrations
  echo "Drop table django_migrations"
  python /var/app/manage.py migrate --fake
else
  echo "Migrating"
  python /var/app/manage.py migrate
fi
#echo "Create cache table"
#
#/var/app-venv/bin/python /var/app/manage.py createcachetable

echo "Clear sessions"

python /var/app/manage.py clearsessions

echo "Collect static"

python /var/app/manage.py collectstatic -c --noinput

if [ $USE_CELERY == "True" ];
then

    echo "Start celery"

    export DJANGO_SETTINGS_MODULE=poms_app.settings

    supervisord

    supervisorctl start celery
    supervisorctl start celerybeat

fi

if [ $USE_FILEBEATS == "True" ];
then

    echo "Run Filebeat"

    service filebeat start

fi


if [ $USE_FLOWER == "True" ];
then

    echo "Run Flower"

    cd /var/app && nohup celery --app poms_app --broker=amqp://guest:guest@$RABBITMQ_HOST:5672// flower --broker_api=http://guest:guest@$RABBITMQ_HOST:15672/api/  --url-prefix=$BASE_API_URL/flower --port=5566 &

fi

echo "Create admin user"

python /var/app/manage.py generate_super_user

echo "Run uwsgi"

uwsgi /etc/uwsgi/apps-enabled/finmars.ini

echo "Initialized"