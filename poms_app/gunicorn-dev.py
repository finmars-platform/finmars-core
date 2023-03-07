"""Gunicorn *development* config file"""

# The granularity of Error log outputs
loglevel = "info"
# The number of worker processes for handling requests
workers = 1
threads = 6
# The socket to bind
bind = "0.0.0.0:8000"
# Restart workers when code changes (development only!)
reload = True
# PID file so you can easily fetch process ID
# pidfile = "/var/run/gunicorn/dev.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
accesslog = "/var/log/finmars/backend/gunicorn.access.log"
errorlog = "/var/log/finmars/backend/gunicorn.error.log"
