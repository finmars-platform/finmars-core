FROM python:3.10-buster

RUN apt-get update && apt-get install -y --no-install-recommends \
    vim htop wget \
    supervisor

# Filebeat
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
RUN echo "deb https://artifacts.elastic.co/packages/oss-8.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-8.x.list
RUN apt-get update && apt-get install filebeat

RUN rm -rf /var/app
COPY requirements.txt /var/app/requirements.txt
RUN pip install -r /var/app/requirements.txt

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
RUN mkdir -p /var/log/finmars
RUN chown -R www-data:www-data /var/log/finmars/
RUN chown -R www-data:www-data /var/app
RUN chown -R www-data:www-data /var/app-data

COPY docker/supervisor/celery.conf /etc/supervisor/conf.d/celery.conf
COPY docker/supervisor/celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf

COPY docker/uwsgi-www.ini /etc/uwsgi/apps-enabled/finmars.ini

COPY docker/filebeat-config /etc/filebeat/filebeat.yml
RUN chmod 501 /etc/filebeat/filebeat.yml

RUN chmod +x /var/app/docker/finmars-run.sh

# create celery user
RUN useradd -N -M --system -s /bin/bash celery  && \
# celery perms
    groupadd grp_celery && usermod -a -G grp_celery celery && mkdir -p /var/run/celery/ /var/log/celery/  && \
    chown -R celery:grp_celery /var/run/celery/ /var/log/celery/

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 8080

CMD ["/bin/bash", "/var/app/docker/finmars-run.sh"]