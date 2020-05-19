#!/usr/bin/env bash
. ../venv/bin/activate
REGISTER_ACCESS_KEY=B5A9ZCHA \
REDIS_HOST=0.0.0.0:6379 \
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5434 \
DEBUG=True \
MEDIATOR_URL=http://localhost:8082/ \
LOGSTASH_HOST=18.185.108.86 \
BACKEND_ROLES="ALL" python manage.py runserver
