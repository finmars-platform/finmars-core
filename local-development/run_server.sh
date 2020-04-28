#!/usr/bin/env bash
. ../venv/bin/activate
REGISTER_ACCESS_KEY=B5A9ZCHA \
REDIS_HOST=0.0.0.0:6379 \
RDS_DB_NAME=finmars_dev \
RDS_USERNAME=postgres \
RDS_PASSWORD=postgres \
RDS_HOSTNAME=localhost \
RDS_PORT=5434 \
POMS_PRICING_AUTO_DOWNLOAD_DISABLED=False \
DEBUG=True \
MEDIATOR_URL=http://localhost:8082/ \
LOGSTASH_HOST=18.185.108.86 \
BACKEND_ROLES="ALL" python manage.py runserver
