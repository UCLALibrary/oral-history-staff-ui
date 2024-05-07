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
   $ docker-compose exec django python manage.py import_projectitems export_scripts/project-items-export.tsv
   # Load full set of name data
   $ docker-compose exec django python manage.py import_names export_scripts/Name.tsv
   ```
7. Connect to the running application via browser

   * [Application](http://127.0.0.1:8000) and [Admin](http://127.0.0.1:8000/admin)
     * Username: `dev_admin`
     * Password: `dev_admin`

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

### Resetting the production database

For data migration, it's necessary to clear out existing data from the production database before doing the final load.  Doing this via a tunneled connection is possible, but very slow (8+ hours for a full load), so it's better to do this while connected directly to the production container, which only DevSupport staff can currently do.

Once connected (either directly, or via tunnel as documented above), run either:
```
# If connected directly
$ docker_scripts/reset_prod_db.sh

# If connected from local system via tunnel
$ docker-compose exec django docker_scripts/reset_prod_db.sh
```

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

#### Viewing the log
Local development environment: `view logs/application.log`.

In deployed container:
* `/logs/`: see latest 200 lines of the log
* `/logs/nnn`: see latest `nnn` lines of the log

### Testing

Tests focus on code which has significant side effects, like creating & changing files.  
Run tests in the container:

```$ docker-compose exec django python manage.py test```

### File management

In the local development environment, samples files for testing are in the `samples` directory.  This directory and its files are under version control, so only add small files, and be sure any real files have no copyright restrictions.

As files are processed locally, they go into subdirectories of `MEDIA_ROOT` - for developers, `/tmp/media_dev` **in the container**. 
The top-level subdirectories are defined via environment variables:
* `DJANGO_OH_MASTERS`
* `DJANGO_OH_WOWZA`
* `DJANGO_OH_STATIC`

Processed files go into various subdirectories below these top-level ones, depending on file use (master, submaster, thumbnail) and content type (audio, image, pdf, text).  Subdirectories are created automatically by Django as needed.

To check the contents of `/tmp/media_dev`, which is only in the container:
```
# Easiest, but harder to read
$ docker-compose exec django bash -c "ls -lR /tmp/media_dev"

# Extra step needed after container rebuilds, but easier to read
# Install tree utility as root (in container):
$ docker-compose exec -u root django bash -c "apt-get install tree"
# Then run tree (in container) as normal django user
$ docker-compose exec django bash -c "tree /tmp/media_dev"
```

Example, after uploading 1 of each type of file, showing masters and derivatives:
```
/tmp/media_dev
├── oh_masters
│   ├── audio
│   │   └── masters
│   │       └── fake-bdef357512-1-master.wav
│   ├── masters
│   │   └── fake-bdef357512-3-master.tif
│   ├── pdf
│   │   └── masters
│   │       └── fake-bdef357512-4-master.pdf
│   └── text
│       └── masters
│           └── fake-bdef357512-2-master.xml
├── oh_static
│   ├── nails
│   │   └── fake-bdef357512-3-thumbnail.jpg
│   ├── pdf
│   │   └── submasters
│   │       └── fake-bdef357512-4-submaster.pdf
│   ├── submasters
│   │   └── fake-bdef357512-3-submaster.jpg
│   └── text
│       └── submasters
│           └── fake-bdef357512-2-submaster.xml
└── oh_wowza
    └── audio
        └── submasters
            └── fake-bdef357512-1-submaster.mp3

18 directories, 9 files
```

#### File deletion

Currently, there is no support in the application for deleting files - a feature to be added later, once specs are agreed on.

To delete files locally, use the Django shell:
```
$ docker-exec exec django python manage.py shell

>>> from oh_staff_ui.models import MediaFile
>>> for mf in MediaFile.objects.all():
...   mf.file.delete()
...   mf.delete()
...
(1, {'oh_staff_ui.MediaFile': 1})
(1, {'oh_staff_ui.MediaFile': 1})
(1, {'oh_staff_ui.MediaFile': 1})
(1, {'oh_staff_ui.MediaFile': 1})
```
Deleting a `MediaFile` object does _*not*_ currently delete any `FileField` object associated with it, so it's necessary to do a `file.delete()` first.

#### OAI Provider details

A barebones OAI Provider is publically available at [/oai](http://127.0.0.1:8000/oai). 
Only MODS output is supported, Dublin Core is not available.

Two verbs are supported:

* `GetRecord` - Given an ark, will return information about the item related to that ark, a single record.
* `ListRecords` - No arguments are required, all qualified records will be returned, without pagination.

The implementation details are located in the `oh_staff_ui\classes\OralHistoryMods.py` class.
The `populate_fields()` method contains the methods called for each element in the MODS record.

If an item contains the following subjects, the subject value is not included in the MODS subject output:
* `Arts, Literature, Music, and Film`
* `Donated Oral Histories`
* `Latinas and Latinos in Music`
* `Latinas and Latinos in Politics`
* `Mexican American Civil Rights`

Descriptions of following type are *not* included in the MODS Description element:
* `adminnote`
* `tableOfContents`

If a Description is of type `abstract` an `Abstract` MODS element is created for this data, not a Description element.

The human readable label for the Description field can be different than the internal Description type, the mapping is as follows:

| Description Type    | Display Label                          |
| --------------------|----------------------------------------|
| biographicalnote    | Biographical Information               |
| interviewerhistory  | Interviewer Background and Preparation |
| personpresent       | Persons Present                        |
| place               | Place Conducted                        |
| processinterview    | Processing of Interview                |
| supportingdocuments | Supporting Documents                   |

The Location element contains information associated with the file location (url) of files associated with an item.
This also has some label mapping to be aware of based on the internal `file_code`:

| File Code              | Display Label                          |
| -----------------------|----------------------------------------|
| pdf_master             | Interview Full Transcript (PDF)        |
| text_master_transcript (file ends with `.html`) | Interview Full Transcript  (Printable Version)|
| text_master_transcript (all other cases) | Interview Full Transcript  (TEI/P5 XML)
| text_master_biography  | Interviewee Biography                  |
| text_master_interview_history | Interview History               |
| pdf_master_appendix    | Appendix to Interview                  |
| text_master_appendix   | Appendix to Interview                  |
| pdf_master_resume      | Narrator's Resume                      |

  

#### Preparing a release

Our deployment system is triggered by changes to the Helm chart.  Typically, this is done by incrementing `image:tag` (on or near line 9) in `charts/prod-ohstaff-values.yaml`.  We use a simple [semantic versioning](https://semver.org/) system:
* Bug fixes: update patch level (e.g., `v1.0.1` to `v1.0.2`)
* Backward compatible functionality changes: update minor level (e.g., `v1.0.1` to `v1.1.0`)
* Breaking changes: update major level (e.g., `v1.0.1` to `v2.0.0`)

In addition to updating version in the Helm chart, update the Release Notes in `oh_staff_ui/templates/oh_staff_ui/release_notes.html`.  Put the latest changes first, following the established format.
