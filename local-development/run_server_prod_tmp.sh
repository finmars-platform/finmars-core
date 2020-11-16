#!/usr/bin/env bash
. ../venv/bin/activate
REGISTER_ACCESS_KEY=B5A9ZCHA \
REDIS_HOST=0.0.0.0:6379 \
DB_NAME=finmars_db \
DB_USER=root \
DB_PASSWORD=t564J3T8My \
DB_HOST=35.158.132.200  \
DB_PORT=5432 \
DEBUG=True \
LOCAL=True \
PROFILER=True \
ENV_CSRF_TRUSTED_ORIGINS=0.0.0.0:8080 \
SFTP_HOST=3.127.37.108 \
SFTP_ROOT=/home/finmars/ \
SFTP_USERNAME=finmars \
SFTP_PKEY_PATH=/home/szhitenev/Downloads/sftp_key/aws_id_rsa \
MEDIATOR_URL=http://localhost:8082/ \
DJANGO_LOG_LEVEL=DEBUG \
BACKEND_ROLES="ALL" python manage.py runserver

