release: python LinkAround/LinkAround_app/manage.py migrate --noinput
web: gunicorn LinkAround_app.wsgi --chdir LinkAround/LinkAround_app --bind 0.0.0.0:$PORT --workers 3 --log-file -
