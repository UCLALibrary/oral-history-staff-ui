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
  
  # Files are TSV, in export_scripts directory
  docker-compose exec django python manage.py import_projectitems export_scripts/project-items-export.tsv
  docker-compose exec django python manage.py import_altids export_scripts/Alt_ID.tsv
  docker-compose exec django python manage.py import_alttitles export_scripts/AltTitle.tsv
  docker-compose exec django python manage.py import_copyrights export_scripts/Copyright.tsv
  docker-compose exec django python manage.py import_coverages export_scripts/Chronological_period_covered.tsv
  docker-compose exec django python manage.py import_dates export_scripts/Date.tsv
  docker-compose exec django python manage.py import_descriptions export_scripts/Description.tsv
  docker-compose exec django python manage.py import_formats export_scripts/'Format_(Length,_pages).tsv'
  docker-compose exec django python manage.py import_languages export_scripts/Language.tsv
  docker-compose exec django python manage.py import_names export_scripts/Name.tsv
  docker-compose exec django python manage.py import_publishers export_scripts/Publisher.tsv
  docker-compose exec django python manage.py import_relations export_scripts/Relation.tsv
  docker-compose exec django python manage.py import_resources export_scripts/Type_of_Resource_.tsv
  docker-compose exec django python manage.py import_subjects export_scripts/Subject.tsv
fi

echo "All done.  Check container logs by running:"
echo "    docker-compose logs django"
