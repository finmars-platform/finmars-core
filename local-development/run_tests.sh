#!/usr/bin/env bash
. ./venv/bin/activate
DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 coverage run --omit='*/venv/*,*/migrations/*' manage.py test --keepdb

# coverage report --omit='*/venv/*,*/migrations/*'