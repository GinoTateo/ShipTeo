release: python manage.py migrate
web: gunicorn MerchManagerV1.wsgi


worker: celery -A MerchManagerV1 worker --loglevel=info

