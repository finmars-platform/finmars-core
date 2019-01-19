# Getting started (Local) 

**Works for python 3.5.0**

* Install NPM
* Install Python 3
* Install Docker and Docker Compose

* Create Virtual Environment (VENV)

`python3 -m venv venv`
* Activate VENV

`source venv/bin/activate`

* Install Dependencies

`pip install -r requirements.txt`

* Install Celery

`pip install celery`

* Start Postgres Database and Redis in docker

`docker-compose -f docker-compose-dev.yml up`

* Run Migrations

`./local-develoment/run_migrate.sh`

* Start Celery Server

`./local-develoment/run_celery.sh`

* Start Django Server

`./local-develoment/run_server.sh`

Success!