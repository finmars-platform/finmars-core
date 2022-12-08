#!/usr/bin/env bash
. ../venv/bin/activate
REDIS_HOST=0.0.0.0:6379 \
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5441 \
DEBUG=True \
LOCAL=True \
PROFILER=True \
ENV_CSRF_TRUSTED_ORIGINS=http://0.0.0.0:8080 \
SFTP_HOST=sftp.finmars.com \
SFTP_USERNAME=finmars \
SFTP_PASSWORD=97cZgv1pL2pz \
SECRET_KEY=mv83o5mq \
MEDIATOR_URL=http://localhost:8082/ \
BACKEND_ROLES="ALL" python manage.py migrate

