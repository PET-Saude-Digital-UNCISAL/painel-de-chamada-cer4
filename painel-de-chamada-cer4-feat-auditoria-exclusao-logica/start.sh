#!/usr/bin/env bash
set -o errexit

python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec daphne config.asgi:application --bind "0.0.0.0" --port "${PORT:-8000}"
