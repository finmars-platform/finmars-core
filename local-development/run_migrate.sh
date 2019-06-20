#!/usr/bin/env bash
. ../venv/bin/activate
#RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python manage.py migrate users 0016
RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python manage.py migrate

#RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python manage.py migrate --fake complex_import zero