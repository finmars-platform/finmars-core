#!/usr/bin/env bash
docker exec -i backend-db-1 /bin/bash -c "PGPASSWORD=postgres pg_dump --username postgres finmars_dev"  > dump.sql