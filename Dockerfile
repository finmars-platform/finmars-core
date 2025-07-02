FROM python:3.12-alpine

RUN apk update && apk add --no-cache \
    build-base \
    python3-dev \
    postgresql-dev \
    musl-dev \
    openssl-dev \
    libffi-dev \
    gcc \
    libc-dev \
    linux-headers \
    openssl-dev \
    # (and cargo rustc if you see a Rust error) \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/app

RUN mkdir -p \
    /var/app-data/import/configs/ \
    /var/app-data/import/files/ \
    /var/app-data/media/ \
    /var/app/static \
    /var/app/log \
    /var/app/finmars_data \
    /var/log/celery \
    /var/log/finmars/backend && \
    chmod 777 /var/app/finmars_data /var/log/finmars/ /var/app/log/

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY data ./data
COPY templates ./templates
COPY finmars_standardized_errors ./finmars_standardized_errors
COPY healthcheck ./healthcheck
COPY logstash ./logstash
COPY poms_app ./poms_app
COPY poms ./poms
COPY manage.py ./

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Node and npm use a non-root user provided by the base Node image
# Creating a new user "finmars" for running the application
RUN adduser \
    --disabled-password \
    --gecos "" \
    finmars

RUN chown -R finmars:finmars /var/log/finmars & chown -R finmars:finmars /var/app

# Change to non-root privilege
USER finmars

EXPOSE 8080

CMD ["gunicorn", "poms_app.wsgi", "--config", "poms_app/gunicorn.py"]
