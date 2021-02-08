FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y apt-utils && \
    apt-get upgrade -y && \
    apt-get install -y \
        htop \
        curl \
        build-essential \
        openssl libssl-dev \
        python3-dev python3-pip python3-venv python3-setuptools python3-wheel \
        libpq-dev libgdal-dev libgeos-dev libproj-dev \
        libtiff5-dev libjpeg-turbo8-dev libzip-dev zlib1g-dev libffi-dev git \
        libgeoip-dev geoip-bin geoip-database \
        uwsgi uwsgi-plugin-python3 uwsgi-plugin-asyncio-python3 uwsgi-plugin-router-access \
        supervisor && \
    rm -rf /var/lib/apt/lists/*

RUN curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.6.2-amd64.deb && \
    dpkg -i filebeat-7.6.2-amd64.deb

ADD requirements.txt /var/app/
RUN python3 -m venv /var/app-venv
RUN /var/app-venv/bin/pip install -U pip wheel uwsgitop
RUN /var/app-venv/bin/pip install -r /var/app/requirements.txt

ADD docker/finmars-run.sh /var/app/docker/finmars-run.sh
ADD data/ /var/app/data/
ADD poms/ /var/app/poms/
ADD healthcheck/ /var/app/healthcheck/
ADD poms_app/ /var/app/poms_app/
ADD manage.py /var/app/manage.py
ADD requirements.txt /var/app/requirements.txt

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

RUN chmod +x /var/app/docker/finmars-run.sh
RUN chmod +x /etc/init.d/celeryd
RUN chmod +x /etc/init.d/celerybeat

RUN chmod 640 /etc/default/celeryd
RUN chmod 640 /etc/default/celerybeat

# create celery user
RUN useradd -N -M --system -s /bin/bash celery
# celery perms
RUN groupadd grp_celery && usermod -a -G grp_celery celery && mkdir -p /var/run/celery/ /var/log/celery/
RUN chown -R celery:grp_celery /var/run/celery/ /var/log/celery/

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 8080

CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]