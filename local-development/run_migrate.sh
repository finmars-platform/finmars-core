#!/usr/bin/env bash
. ../venv/bin/activate
#DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python manage.py migrate users 0016
DJANGO_LOG_LEVEL=DEBUG \
DB_NAME=finmars_dev \
DB_USER=postgres \
DB_PASSWORD=postgres \
DB_HOST=localhost \
DB_PORT=5434 \
AWS_STORAGE_BUCKET_NAME=finmars-client00000local \
AWS_S3_ACCESS_KEY_ID=AKIAZFI7MO4TROTNDZWN \
AWS_S3_SECRET_ACCESS_KEY=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 \
SECRET_KEY=mv83o5mq python manage.py migrate_all_schemes

#DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python manage.py migrate --fake complex_import zero