"""Gunicorn *development* config file"""

# The granularity of Error log outputs
loglevel = "info"
# The number of worker processes for handling requests
workers = 2
threads = 6
# The socket to bind
bind = "0.0.0.0:8000"
# PID file so you can easily fetch process ID
pidfile = "/var/run/gunicorn/prod.pid"
# Daemonize the Gunicorn process (detach & enter background)
daemon = True