#!/bin/bash
# Clears all data (including users) from central production database,
# then loads all available data from external files, previously exported
# from legacy database.
#
# Must be run from within Django container.

echo "*** WARNING: THIS WILL COMPLETELY DESTROY YOUR CURRENT PRODUCTION DATABASE! ***"
echo ""
echo "Are you SURE you want to do this?  Choose 1) to continue, anything else to exit."
select yn in "YES" "NO, EXIT!"; do
  case $yn in 
    YES ) break;;
    * ) echo "Cancelled - exiting"; exit;;
  esac
done

# Get full absolute path to this running script.
SCRIPT_PATH=$(dirname $(realpath -s $0))
# Assumes Django's manage.py is in parent directory; exit if not found.
PROJECT_ROOT=$(realpath -s ${SCRIPT_PATH}/..)
cd ${PROJECT_ROOT}
if [ ! -f manage.py ]; then
  echo "ERROR: manage.py not found - exiting"
  exit 1
fi

# Run Django's "flush":
# Removes ALL DATA from the database, including data added during migrations. Does not achieve a "fresh install" state.
# This truncates all tables at once, resetting sequences.
echo "Deleting all existing data..."
python manage.py flush --no-input

# Load fixtures, which contain values for lookup tables needed by the main data.
# Order does not matter.
echo "Loading fixtures..."
FIXTURE_DIR=${PROJECT_ROOT}/oh_staff_ui/fixtures
for FIXTURE in ${FIXTURE_DIR}/*data.json; do
  # Full path to fixture is OK
  python manage.py loaddata ${FIXTURE}
done

# Load main data files.
echo "=================================="
echo "Reloading all data, please wait..."

# Files are TSV, in export_scripts directory.
DATA_DIR=${PROJECT_ROOT}/export_scripts
python manage.py import_projectitems ${DATA_DIR}/project-items-export.tsv
python manage.py import_altids ${DATA_DIR}/Alt_ID.tsv
python manage.py import_alttitles ${DATA_DIR}/AltTitle.tsv
python manage.py import_copyrights ${DATA_DIR}/Copyright.tsv
python manage.py import_dates ${DATA_DIR}/Date.tsv
python manage.py import_descriptions ${DATA_DIR}/Description.tsv
python manage.py import_formats ${DATA_DIR}/'Format_(Length,_pages).tsv'
python manage.py import_languages ${DATA_DIR}/Language.tsv
python manage.py import_names ${DATA_DIR}/Name.tsv
python manage.py import_publishers ${DATA_DIR}/Publisher.tsv
python manage.py import_resources ${DATA_DIR}/Type_of_Resource_.tsv
python manage.py import_subjects ${DATA_DIR}/Subject.tsv
