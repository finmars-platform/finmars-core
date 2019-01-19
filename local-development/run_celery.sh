#!/usr/bin/env bash
#export DJANGO_SETTINGS_MODULE=poms_app.settings_dev_ai
export DJANGO_SETTINGS_MODULE=poms_app.settings
RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 celery worker --app poms_app --pool solo --beat --loglevel=DEBUG
