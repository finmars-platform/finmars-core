#!/usr/bin/env bash
. ../venv/bin/activate
REGISTER_ACCESS_KEY=B5A9ZCHA \
LOGSTASH_HOST=54.93.76.174 \
REDIS_HOST=localhost:6379
RDS_DB_NAME=finmars_dev \
RDS_USERNAME=postgres \
RDS_PASSWORD=postgres \
RDS_HOSTNAME=localhost \
RDS_PORT=5434 \
POMS_PRICING_AUTO_DOWNLOAD_DISABLED=False \
BACKEND_ROLES="ALL" python manage.py runserver
