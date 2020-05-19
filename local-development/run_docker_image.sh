#!/usr/bin/env bash
docker run \
--env DB_NAME=finmars_dev \
--env DB_USER=postgres \
--env DB_PASSWORD=postgres \
--env DB_HOST=localhost \
--env DB_PORT=5434  finmars