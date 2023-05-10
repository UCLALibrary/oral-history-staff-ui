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
# Make sure system is fully available and all fixtures have loaded.
sleep 15

# Currently, only support reloading all data; may be more specific later.
if [ "${RELOAD}" = "Y" ]; then
  echo "=================================="
  echo "Reloading all data, please wait..."

  # Files are TSV, in migration_data directory
  docker-compose exec django python manage.py import_projectitems migration_data/project-items-export.tsv
  docker-compose exec django python manage.py import_altids migration_data/Alt_ID.tsv
  docker-compose exec django python manage.py import_alttitles migration_data/AltTitle.tsv
  docker-compose exec django python manage.py import_copyrights migration_data/Copyright.tsv
  docker-compose exec django python manage.py import_dates migration_data/Date.tsv
  docker-compose exec django python manage.py import_descriptions migration_data/Description.tsv
  docker-compose exec django python manage.py import_formats migration_data/'Format_(Length,_pages).tsv'
  docker-compose exec django python manage.py import_languages migration_data/Language.tsv
  docker-compose exec django python manage.py import_names migration_data/Name.tsv
  docker-compose exec django python manage.py import_publishers migration_data/Publisher.tsv
  docker-compose exec django python manage.py import_resources migration_data/Type_of_Resource_.tsv
  docker-compose exec django python manage.py import_subjects migration_data/Subject.tsv
  # This has a lot of output...
  docker-compose exec django python manage.py import_file_metadata migration_data/file_metadata.tsv
fi

echo "All done.  Check container logs by running:"
echo "    docker-compose logs django"
