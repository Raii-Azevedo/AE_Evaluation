web: python manage.py collectstatic --noinput && python manage.py migrate --run-syncdb && gunicorn ae_project.wsgi:application
