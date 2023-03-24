#!/bin/bash
# Removes local docker-based development database for the Oral History staff UI application.
# The database is recreated automatically when docker-compose starts the application.
# nuke_dev_db.sh

# Optionally, loads full data files to repopulate the database, which can take a few minutes.
# Opt out of reloading by adding NOLOAD as the only parameter:
# nuke_dev_db.sh NOLOAD

echo "*** WARNING: THIS WILL COMPLETELY DESTROY YOUR CURRENT DEV DATABASE! ***"
echo ""
echo "Are you SURE you want to do this?  Choose 1) to continue, anything else to exit."
select yn in "YES" "NO, EXIT!"; do
  case $yn in 
    YES ) break;;
    * ) echo "Cancelled - exiting"; exit;;
  esac
done

# Capture parameter, if any.
# If no parameter, data will be reloaded.
if [ -z "$1" ]; then
  RELOAD=Y
else
  if [ "$1" = "NOLOAD" ]; then
    RELOAD=N
  else
    RELOAD=Y
  fi
fi

echo "Shutting down local docker-compose system..."
docker-compose down
sleep 5

echo "Removing local docker database volume..."
docker volume rm oral-history-staff-ui_pg_data

echo "Starting local docker-compose system in background..."
docker-compose up -d
sleep 5

# Currently, only support reloading all data; may be more specific later.
if [ "${RELOAD}" = "Y" ]; then
  echo "=================================="
  echo "Reloading all data, please wait..."
  docker-compose exec django python manage.py import_projectitems oh-projectitems-export-3.csv
  docker-compose exec django python manage.py import_names name-md-export.csv
fi

echo "All done.  Check container logs by running:"
echo "    docker-compose logs django"
