export DJANGO_SETTINGS_MODULE=poms_app.settings
celery --app poms_app worker -E -Q backend-general-queue --loglevel=DEBUG
