#!/usr/bin/env bash
celery flower --broker=amqp://guest:guest@localhost:5672/
