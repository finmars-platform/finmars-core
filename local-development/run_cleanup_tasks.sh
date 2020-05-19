#!/usr/bin/env bash
. ../venv/bin/activate
DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python manage.py cleanup_tasks