#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5441 SECRET_KEY=mv83o5mq python manage.py makemigrations