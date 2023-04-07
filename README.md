# oral-history-staff-ui
New staff UI for Oral History (Phase 2)

## Purpose

This is the new staff user interface for the Oral History project.
It allows staff to create & maintain metadata, and upload & process media files,
for UCLA's [Oral History site](https://oralhistory.library.ucla.edu/).

This is the second phase of development.  The first was a temporary solution which
enabled staff to upload files with the old DLCS application.  That functionality 
will be integrated into this new application.

Related repositories:
* [Phase 1](https://github.com/UCLALibrary/dlcs-staff-ui)
* [Public site](https://github.com/UCLALibrary/oral-history)

## Developer Information

### Overview of environment

The development environment requires:
* git (at least version 2)
* docker (current version recommended: 20.10.12)
* docker-compose (at least version 1.25.0; current recommended: 1.29.2)

#### PostgreSQL container

The development database is a Docker container running PostgreSQL 12, which matches our deployment environment.

#### Django container

This uses Django 4.1, in a Debian 11 (Bullseye) container running Python 3.11.  All code 
runs in the container, so local version of Python does not matter.

The container runs via `docker_scripts/entrypoint.sh`, which
* Updates container with any new requirements, if the image hasn't been rebuilt (DEV environment only).
* Waits for the database to be completely available.  This can take 5-10 seconds, depending on your hardware.
* Applies any pending migrations (DEV environment only).
* Creates a generic Django superuser, if one does not already exist (DEV environment only).
* Loads fixtures to populate lookup tables and to add a few sample records.
* Starts the Django application server.

### Setup
1. Clone the repository.

   ```$ git clone git@github.com:UCLALibrary/oral-history-staff-ui.git```

2. Change directory into the project.

   ```$ cd oral-history-staff-ui```

3. Build using docker-compose.

   ```$ docker-compose build```

4. Bring the system up, with containers running in the background.

   ```$ docker-compose up -d```

5. Logs can be viewed, if needed (`-f` to tail logs).

   ```
   $ docker-compose logs -f db
   $ docker-compose logs -f django
   ```

6. Run commands in the containers, if needed.

   ```
   # Open psql client in the dev database container
   $ docker-compose exec db psql -d oral_history -U oral_history
   # Open a shell in the django container
   $ docker-compose exec django bash
   # Django-aware Python shell
   $ docker-compose exec django python manage.py shell
   # Apply new migrations without a restart
   $ docker-compose exec django python manage.py migrate
   # Populate database with seed data (once it exists...)
   $ docker-compose exec django python manage.py loaddata --app oh_staff_ui seed-data
   #
   # Load full set of item data
   $ docker-compose exec django python manage.py import_projectitems oh-projectitems-export-3.csv
   # Load full set of name data
   $ docker-compose exec django python manage.py import_names name-md-export.csv
   ```
7. Connect to the running application via browser

   [Application](http://127.0.0.1:8000) and [Admin](http://127.0.0.1:8000/admin)

8. Edit code locally.  All changes are immediately available in the running container, but if a restart is needed:

   ```$ docker-compose restart django```

9. Shut down the system when done.

   ```$ docker-compose down```

### Resetting the local database

The local docker-based development database can be reset as needed.  This is helpful when switching between branches which involve migrations, or when testing data loading and transformation.

To do this, run:
`docker_scripts/nuke_dev_db.sh`

It does the following:
* Shuts down the application
* Drops the docker volume for the database
* Starts the application
* Reloads data files via management commands.
  * This currently is just `ProjectItem` and `Name` files; others will be added as loaders are finished.

The script warns users, and requires them to confirm their decision.

Developers can opt out of reloading data by adding a specific parameter:
`docker_scripts/nuke_dev_db.sh NOLOAD`

### Connecting to production database

This will not normally need to be done during development, but may be needed for data migration.  It requires the ability to establish a tunneled SSH connection to the production database server, and a file with production database credentials.

1. In a separate terminal window, create a tunneled SSH connection through the `jump` server to the production database server.  This will forward all local connections on port 5433:

   ```$ ssh -NT -L 0.0.0.0:5433:p-d-postgres.library.ucla.edu:5432 jump```

2. If you don't already have it, get `.docker-compose_secrets.env` from a teammate and add it to the top level of your project (same directory as `docker-compose_REMOTE.yml`).

3. Shut down your local application, if running:

   ```$ docker-compose down```

4. Start your local application, using the specially-configured `docker-compose_REMOTE.yml`.  This will start just the Django container, skipping the usual local database container and instead connecting to the remote database via information in `.docker-compose_secrets.env`:

   ```$ docker-compose -f docker-compose_REMOTE.yml up -d```

5. _*Be very careful - your local application is now connected to the production database!*_

6. When finished, shut down your local application as usual.  Switch to your other terminal window and `CTRL-C` or `CMD-C` to stop the tunnel.

### Logging

Basic logging is available, with logs captured in `logs/application.log`.  At present, logs from both the custom application code and Django itself are captured.

Logging level is set to `INFO` via `.docker-compose_django.env`.  If there's a regular need/desire for DEBUG level, we can discuss that.

#### How to log

Logging can be used in any Python file in the project.  For example, in `views.py`:
```
# Include the module with other imports
import logging
# Instantiate a logger, generally before any functions in the file
logger = logging.getLogger(__name__)

def project_table():
    logger.info('This is a log message from project_table')

    query_results = ProjectItems.objects.all()
    for r in query_results:
        logger.info(f'{r.node_title} === {r.item_ark}')

    try:
        1/0
    except Exception as e:
        logger.exception('Example exception')

    logger.debug('This DEBUG message only appears if DJANGO_LOG_LEVEL=DEBUG')
```
#### Log format
The current log format includes:
* Level: DEBUG, INFO, WARNING, ERROR, or CRITICAL
* Timestamp via `asctime`
* Logger name: to distinguish between sources of messages (`django` vs `oral_history` application)
* Module: somewhat redundant with logger name
* Message: The main thing being logged

