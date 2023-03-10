#!/bin/bash

# Write python output in real time without buffering
export PYTHONUNBUFFERED=1

# Pick up any local changes to requirements.txt, which do *not* automatically get re-installed when starting the container.
# Do this only in dev environment!
if [ "$DJANGO_RUN_ENV" = "dev" ]; then
  pip install --no-cache-dir -r requirements.txt --user --no-warn-script-location
fi

# Check when database is ready for connections
echo "Checking database connectivity..."
until python -c 'import os, psycopg2 ; conn = psycopg2.connect(host=os.environ.get("DJANGO_DB_HOST"),user=os.environ.get("DJANGO_DB_USER"),password=os.environ.get("DJANGO_DB_PASSWORD"),dbname=os.environ.get("DJANGO_DB_NAME"))' ; do
  echo "Database connection not ready - waiting"
  sleep 5
done

# Run database migrations
python manage.py migrate

if [ "$DJANGO_RUN_ENV" = "dev" ]; then
  # Create default superuser for dev environment, using django env vars.
  # Logs will show error if this exists, which is OK.
  python manage.py createsuperuser --no-input

  # Make sure necessary lookup tables have at least sample data.
  # seed-data has ItemType, ItemStatus, and 3 sample ProjectItem records.
  python manage.py loaddata seed-data
  python manage.py loaddata authority-source-data language-data
  python manage.py loaddata name-type-data name-data
  python manage.py loaddata subject-type-data subject-data
  python manage.py loaddata altid-type-data alttitle-type-data
  python manage.py loaddata altid-data alttitle-data
  python manage.py loaddata description-type-data publisher-type-data
  python manage.py loaddata description-data publisher-data
  python manage.py loaddata copyright-type-data copyright-data
  python manage.py loaddata relation-type-data relation-data
  python manage.py loaddata coverage-data
  python manage.py loaddata format-data
fi

if [ "$DJANGO_RUN_ENV" = "dev" ]; then
  python manage.py runserver 0.0.0.0:8000
else
  # Build static files directory, starting fresh each time - do we really need this?
  python manage.py collectstatic --no-input

  # Start the Gunicorn web server
  # Gunicorn cmd line flags:
  # -w number of gunicorn worker processes
  # -b IPADDR:PORT binding
  # -t timeout in seconds.  
  # --access-logfile where to send HTTP access logs (- is stdout)
  export GUNICORN_CMD_ARGS="-w 3 -b 0.0.0.0:8000 -t 60 --access-logfile -"
  gunicorn project.wsgi:application
fi
