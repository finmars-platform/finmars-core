#!/usr/bin/env bash
. ../venv/bin/activate
RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python manage.py migrate transactions 0024