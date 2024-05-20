import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from oh_staff_ui.models import MediaFile


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django management command to audit media files."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "mode",
            type=str,
            help="Mode: one of DB|FILES|BOTH",
        )

    def handle(self, *args, **options) -> None:
        mode = options["mode"]
        if mode == "DB":
            self._compare_db_to_files()
        elif mode == "FILES":
            self._compare_files_to_db()
        elif mode == "ALL":
            self._compare_db_to_files()
            self._compare_files_to_db()
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _compare_db_to_files(self) -> None:
        """Compares MediaFile data with files on disk and
        reports differences.
        """
        media_files = MediaFile.objects.all().order_by("id")
        for mf in media_files:
            db_file_name = mf.file.name
            db_file_path = Path(settings.MEDIA_ROOT).joinpath(db_file_name)
            db_file_size = mf.file_size
            # If file does exist, get info for comparison
            if db_file_path.exists():
                disk_file_size = db_file_path.stat().st_size
            else:
                disk_file_size = None
                disk_file_path = "NOT FOUND"
            # Report on differences only, for now.
            if not db_file_path.exists():
                logger.warning(
                    f"FILE MISSING:\t{db_file_path}\t{disk_file_path}\t"
                    f"{db_file_size}\t{disk_file_size}"
                )
            elif db_file_size != disk_file_size:
                logger.warning(
                    f"SIZE DIFFERENCE:\t{db_file_path}\t{disk_file_path}\t"
                    f"{db_file_size}\t{disk_file_size}"
                )

    def _compare_files_to_db(self) -> None:
        """Compares files on disk with MediaFile data and
        reports differences.
        """
        # Build this once, as it will be used many times.
        media_root = settings.MEDIA_ROOT + "/"
        # rglob returns directory and file names.
        for path in Path(media_root).rglob("*"):
            if path.is_file():
                # MediaFile file.name does not have MEDIA_ROOT prefix, so remove it.
                disk_file_path = str(path).replace(media_root, "")
                disk_file_size = path.stat().st_size
                media_files = MediaFile.objects.filter(file=disk_file_path)
                media_file_count = len(media_files)

                if media_file_count == 0:
                    # File not found in database
                    db_file_size = None
                    db_file_path = "NOT FOUND"
                    logger.warning(
                        f"DB MISSING:\t{db_file_path}\t{disk_file_path}\t"
                        f"{db_file_size}\t{disk_file_size}"
                    )
                elif media_file_count > 1:
                    # Shouldn't happen due to custom MediaFile.save()...
                    # but check for file found multiple times in database.
                    # Some/all/none may actually be right, so report all.
                    for mf in media_files:
                        logger.warning(
                            f"MULTIPLE:\t{mf.file.name}\t{disk_file_path}\t"
                            f"{mf.file_size}\t{disk_file_size}"
                        )
