#export DJANGO_SETTINGS_MODULE=poms_app.settings_dev_ai
export DJANGO_SETTINGS_MODULE=poms_app.settings
celery worker --app poms_app --pool solo --beat --loglevel=DEBUG
