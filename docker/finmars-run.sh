
# /var/app/docker/finmars-run.sh

#source /var/app-venv/bin/activate
#cd /var/app/

echo "Finmars"

echo "Migrating"

/var/app-venv/bin/python /var/app/manage.py migrate

echo "Create cache table"

/var/app-venv/bin/python /var/app/manage.py createcachetable

echo "Clear sessions"

/var/app-venv/bin/python /var/app/manage.py clearsessions

echo "Collect static"

/var/app-venv/bin/python /var/app/manage.py collectstatic -c --noinput

echo "Start celery"

export DJANGO_SETTINGS_MODULE=poms_app.settings

/etc/init.d/celeryd start

echo "Start celerybeat"

export DJANGO_SETTINGS_MODULE=poms_app.settings

/etc/init.d/celerybeat start

#echo "Standalone"
#
#/var/app-venv/bin/python /var/app/manage.py initstandalone

echo "Run uwsgi"

/usr/bin/uwsgi /etc/uwsgi/apps-enabled/finmars.ini

