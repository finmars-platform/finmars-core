#!/usr/bin/env bash
export DJANGO_SETTINGS_MODULE=poms_app.settings
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5434 \
DEBUG=True \
SECRET_KEY=mv83o5mq \
python manage.py update_ttype_input_context_property