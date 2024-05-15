#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
ADMIN_USERNAME=admin_realm00000 \
ADMIN_PASSWORD=d798nf0rgpp6g8qp \
DB_PORT=5434 SECRET_KEY=mv83o5mq python manage.py generate_super_user