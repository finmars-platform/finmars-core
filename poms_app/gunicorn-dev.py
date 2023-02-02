"""Gunicorn *development* config file"""

# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = 2
threads = 6
# The socket to bind
bind = "0.0.0.0:8000"
# Restart workers when code changes (development only!)
reload = True
# PID file so you can easily fetch process ID
# pidfile = "/var/run/gunicorn/dev.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
