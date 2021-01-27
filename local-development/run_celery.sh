#!/usr/bin/env bash
#export DJANGO_SETTINGS_MODULE=poms_app.settings_dev_ai
export DJANGO_SETTINGS_MODULE=poms_app.settings
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5434 \
DEBUG=True \
SFTP_HOST=sftp.finmars.com \
SFTP_USERNAME=finmars \
SFTP_PASSWORD=97cZgv1pL2pz \
DJANGO_LOG_LEVEL=DEBUG \
USE_WEBSOCKETS=True \
WEBSOCKET_HOST=ws://0.0.0.0:6969 \
celery worker --app poms_app --beat --loglevel=DEBUG --logfile=/var/log/finmars/celery.log
