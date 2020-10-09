#!/usr/bin/env bash
. ../venv/bin/activate
REGISTER_ACCESS_KEY=B5A9ZCHA \
REDIS_HOST=0.0.0.0:6379 \
DB_NAME=finmars_db \
DB_USER=root \
DB_PASSWORD=t564J3T8My \
DB_HOST=18.197.22.7 \
DB_PORT=5432 \
DEBUG=True \
LOCAL=True \
PROFILER=True \
ENV_CSRF_TRUSTED_ORIGINS=0.0.0.0:8080 \
SFTP_HOST=sftp.finmars.com \
SFTP_USERNAME=finmars \
SFTP_PASSWORD=97cZgv1pL2pz \
MEDIATOR_URL=http://localhost:8082/ \
BACKEND_ROLES="ALL" python manage.py migrate

