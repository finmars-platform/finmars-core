# Getting started (Local)

* Install NPM
* Install Python 3
* Install Docker and Docker Compose

* Create Virtual Environment (VENV)

`python3 -m venv venv`
* Activate VENV

`source venv/bin/activate`

* Start Postgres Database and Redis in docker

`docker-compose -f docker-compose-dev.yml up`

* Start Celery Server

`./local-develoment/run_celery.sh`

* Start Django Server

`./local-develoment/run_server.sh`

Success!