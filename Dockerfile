FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# install python3.9

RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.9

RUN apt-get update && \
    apt-get install -y apt-utils && \
    apt-get upgrade -y && \
    apt-get install -y \
        wget htop curl \
        build-essential \
        openssl libssl-dev \
        python3.9-dev python3-pip python3.9-venv python3-setuptools python3-wheel \
        libpq-dev libgdal-dev libgeos-dev libproj-dev \
        libtiff5-dev libjpeg-turbo8-dev libzip-dev zlib1g-dev libffi-dev git \
        libgeoip-dev geoip-bin geoip-database \
        supervisor

RUN rm -rf /var/lib/apt/lists/*
# Filebeat
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
RUN echo "deb https://artifacts.elastic.co/packages/oss-8.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-8.x.list
RUN apt-get update && apt-get install filebeat


RUN apt-get update && apt-get install ca-certificates


RUN rm -rf /var/app
COPY requirements.txt /var/app/requirements.txt
RUN python3.9 -m venv /var/app-venv
RUN /var/app-venv/bin/pip install "setuptools<58.0.0"
RUN /var/app-venv/bin/pip install -U pip wheel uwsgitop
RUN /var/app-venv/bin/pip install -U pip boto3
RUN /var/app-venv/bin/pip install -U pip azure-storage-blob
RUN /var/app-venv/bin/pip install -r /var/app/requirements.txt
RUN /var/app-venv/bin/pip install -U pip flower
RUN /var/app-venv/bin/pip install -U pip uwsgi


COPY docker/finmars-run.sh /var/app/docker/finmars-run.sh
COPY data/ /var/app/data/
COPY poms/ /var/app/poms/
COPY healthcheck/ /var/app/healthcheck/
COPY poms_app/ /var/app/poms_app/
COPY manage.py /var/app/manage.py

RUN mkdir -p /var/app-data/
RUN mkdir -p /var/app-data/media/
RUN mkdir -p /var/app-data/import/configs/
RUN mkdir -p /var/app-data/import/files/
RUN chmod -R 777 /var/app-data/

RUN mkdir -p /var/log/finmars
RUN chown -R www-data:www-data /var/log/finmars/

COPY docker/celeryd /etc/init.d/celeryd
COPY docker/celeryd-config /etc/default/celeryd

COPY docker/celerybeat /etc/init.d/celerybeat
COPY docker/celerybeat-config /etc/default/celerybeat

COPY docker/uwsgi-www.ini /etc/uwsgi/apps-enabled/finmars.ini

COPY docker/filebeat-config /etc/filebeat/filebeat.yml
RUN chmod 501 /etc/filebeat/filebeat.yml

RUN chmod +x /var/app/docker/finmars-run.sh  && \
    chmod +x /etc/init.d/celeryd  && \
    chmod +x /etc/init.d/celerybeat  && \
    chmod 640 /etc/default/celeryd  && \
    chmod 640 /etc/default/celerybeat

# create celery user
RUN useradd -N -M --system -s /bin/bash celery  && \
# celery perms
    groupadd grp_celery && usermod -a -G grp_celery celery && mkdir -p /var/run/celery/ /var/log/celery/  && \
    chown -R celery:grp_celery /var/run/celery/ /var/log/celery/

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 8080

CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]