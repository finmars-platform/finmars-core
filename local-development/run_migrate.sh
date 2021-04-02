#!/usr/bin/env bash
. ../venv/bin/activate
#DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python manage.py migrate users 0016
DJANGO_LOG_LEVEL=DEBUG DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 SECRET_KEY=mv83o5mq python manage.py migrate

#DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python manage.py migrate --fake complex_import zero