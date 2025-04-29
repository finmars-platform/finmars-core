FROM python:3.12-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    htop \
    nfs-common \
    postgresql-client \
    supervisor \
    vim \
    wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /var/app

RUN mkdir -p \
    /var/app-data/import/configs/ \
    /var/app-data/import/files/ \
    /var/app-data/media/ \
    /var/app/finmars_data \
    /var/log/celery \
    /var/log/finmars/backend && \
    chmod 777 /var/app/finmars_data

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY data ./data
COPY finmars_standardized_errors ./finmars_standardized_errors
COPY healthcheck ./healthcheck    
COPY poms_app ./poms_app
COPY poms ./poms
COPY manage.py ./

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

EXPOSE 8080

CMD ["gunicorn", "poms_app.wsgi", "--config", "poms_app/gunicorn.py"]
