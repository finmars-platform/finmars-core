#!/usr/bin/env bash
docker run \
--env RDS_DB_NAME=finmars_dev \
--env RDS_USERNAME=postgres \
--env RDS_PASSWORD=postgres \
--env RDS_HOSTNAME=localhost \
--env RDS_PORT=5434  finmars