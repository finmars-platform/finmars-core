#!/usr/bin/env bash
. ../venv/bin/activate
DJANGO_LOG_LEVEL=DEBUG DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 SECRET_KEY=mv83o5mq python manage.py shell --space-code=space00000