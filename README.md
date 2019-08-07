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


How to compile django app

1) Activate venv

    `source venv/bin/activate`

2) Install PyInstaller==3.4

    `pip install pyinstaller==3.4.`
    
3) Execute following command to build

   `REDIS_HOST=localhost RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python3 -m PyInstaller backend.spec -y --debug --log-level TRACE`
    
4) Execute following command to runserver

   `REDIS_HOST=localhost RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 dist/backend/backend manage.py runserver 8080`
   


`docker-compose.yml` - Сейчас нигде не используется

`docker-compose-dev.yml` - Используется для локальной разработки

`Dokerfile` - тот файл который использует Jenkins для сборки итогового билда

`docker` - набор скриптов которые использует Dokerfile для итогового image


Что можно сделать
1) Сделать сборки локальной версии и той что на серверах максимально похожими (Сейчас очень сильно олтичаются Celery)