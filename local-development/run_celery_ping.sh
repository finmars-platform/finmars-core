#!/usr/bin/env bash
celery inspect ping -b redis://0.0.0.0:6379 -d celery@$$HOSTNAME
