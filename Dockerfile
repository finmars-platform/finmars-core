FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y apt-utils && \
    apt-get upgrade -y && \
    apt-get install -y \
        openssl libssl-dev \
        python3-dev python3-pip python3-venv python3-setuptools python3-wheel \
        libpq-dev libgdal-dev libgeos-dev libproj-dev \
        libtiff5-dev libjpeg-turbo8-dev libzip-dev zlib1g-dev libffi-dev git \
        libgeoip-dev geoip-bin geoip-database \
        uwsgi uwsgi-plugin-python3 uwsgi-plugin-asyncio-python3 uwsgi-plugin-router-access \
        supervisor && \
    rm -rf /var/lib/apt/lists/*


ADD requirements.txt /var/app/
RUN pyvenv-3.5 /var/app-venv
RUN /var/app-venv/bin/pip install -U pip wheel && /var/app-venv/bin/pip install -r /var/app/requirements.txt

#ADD . /var/app/
ADD docker/finmars-run.sh /var/app/docker/finmars-run.sh
#ADD docker/uwsgi-*.sh /var/app/docker/
ADD data/ /var/app/data/
#ADD ext/ /var/app/ext/
ADD poms/ /var/app/poms/
ADD poms_app/ /var/app/poms_app/
ADD manage.py /var/app/manage.py
ADD requirements.txt /var/app/requirements.txt

RUN mkdir -p /var/log/finmars/
RUN mkdir -p /var/app-data/
RUN mkdir -p /var/app-data/media/
RUN mkdir -p /var/app-data/import/configs/
RUN mkdir -p /var/app-data/import/files/
RUN chmod -R 777 /var/app-data/

COPY docker/uwsgi-celery.ini /etc/uwsgi/finmars-vassals/finmars-celery.ini
COPY docker/uwsgi-celerybeat.ini /etc/uwsgi/finmars-vassals/finmars-celerybeat.ini
COPY docker/uwsgi-www.ini /etc/uwsgi/finmars-vassals/finmars-www.ini
COPY docker/uwsgi-emperor.ini /etc/uwsgi/apps-enabled/finmars.ini

RUN chmod +x /var/app/docker/finmars-run.sh

#ENV DJANGO_SETTINGS_MODULE poms_app.settings_standalone

#ENV RDS_DB_NAME postgres
#ENV RDS_USERNAME postgres
#ENV RDS_PASSWORD finmars
#ENV RDS_HOSTNAME finmars-db
#ENV REDIS_HOST finmars-redis:6379
#ENV POMS_DEV False
#ENV POMS_BLOOMBERG_SANDBOX True
#ENV POMS_PRICING_AUTO_DOWNLOAD_DISABLED True

EXPOSE 8080

CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]
#CMD ["/bin/bash"]
