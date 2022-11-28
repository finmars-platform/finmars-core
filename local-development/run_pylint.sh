#!/usr/bin/env bash
export DJANGO_SETTINGS_MODULE=poms_app.settings
export PYTHONPATH=$PYTHONPATH:$PWD
#pylint --load-plugins pylint_django --django-settings-module=poms_app.settings poms/**/*.py
pylint --load-plugins pylint_django poms/**/*.py --output-format=json:pylint_result.json,colorized