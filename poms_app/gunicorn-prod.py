"""Gunicorn *development* config file"""

import os

from poms_app.utils import ENV_INT

import time
gunicorn_start_time = time.time()

# The granularity of Error log outputs
chdir = "/var/app/"
loglevel = "info"
# The number of worker processes for handling requests
workers = ENV_INT("GUNICORN_WORKERS", 1)  # to reduce memory usage, increase number of workers on Galaxy Level customers
# threads = ENV_INT("GUNICORN_THREADS", 2)  # Max of CPU Cores
timeout = 180
# The socket to bind
bind = "0.0.0.0:8080"
# PID file so you can easily fetch process ID
# pidfile = "/var/run/gunicorn/prod.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
accesslog = "/var/log/finmars/backend/gunicorn.access.log"
errorlog = "/var/log/finmars/backend/gunicorn.error.log"
