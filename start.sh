#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
exec gunicorn config.wsgi:application
