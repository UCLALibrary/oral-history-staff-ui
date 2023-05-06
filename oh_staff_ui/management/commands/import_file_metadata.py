from datetime import datetime
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.http import HttpRequest  # for mock requests
from django.utils import timezone
from oh_staff_ui.classes.OralHistoryFile import (
    OralHistoryFile,
)  # for TZ in Django's context
from oh_staff_ui.models import MediaFile, MediaFileType, ProjectItem
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports file metadata from a TSV file"

    def add_arguments(self, parser) -> None:
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options) -> None:
        dicts_list = get_dicts_from_tsv(options["filepath"])
        print(f"Found {len(dicts_list)} rows of file metadata to import.")

        # TODO: REMOVE THIS - DO NOT DELETE NORMALLY!
        print("*** WARNING *** DELETING EXISTING DATA DURING TESTING ***")
        MediaFile.objects.all().delete()

        file_count_before = MediaFile.objects.count()
        total_skipped = 0
        for row in dicts_list:
            try:
                content_type = row["CONTENT_TYPE"]
                create_date = self.format_date(row["CREATE_DATE"])
                file_group_title = row["FILE_GROUP_TITLE"]
                file_location = row["FILE_LOCATION"]
                # TODO: GET REAL PATH
                file_name = row["FILE_NAME"]
                file_size = row["FILE_SIZE"]
                file_use = row["FILE_USE"].lower()
                item_ark = row["ITEM_ARK"]
                sequence = row["SEQ"]
                # Make legacy data match cleaned-up name in Django
                if file_group_title == "PDF  Résumé":
                    file_group_title = "PDF Résumé"

                # Start database
                file_type = MediaFileType.objects.get(file_type=file_group_title)
                item = ProjectItem.objects.get(ark=item_ark)

                # experimenting
                ohf = OralHistoryFile(
                    item_id=item.id,
                    file_name=file_name,
                    file_type=file_type,
                    file_use=file_use,
                    request=self.get_mock_request(item.created_by),
                )
                print(f"\nOHF says: {ohf.content_type=}, {ohf.target_dir=}")

                mf = MediaFile.objects.create(
                    created_by=item.created_by,
                    create_date=create_date,
                    file=file_name,
                    file_size=file_size,
                    file_type=file_type,
                    original_file_name="Unknown",
                    sequence=sequence,
                    item=item,
                    # Not trying to set parent for migrated file info
                    parent=None,
                )
                print(f"{content_type=}, {mf.file.name=}, {file_location=}")
            except MediaFileType.DoesNotExist:
                print(
                    f"No file type found for {file_group_title} - skipping file {file_name}"
                )
                total_skipped += 1
                continue
            except ProjectItem.DoesNotExist:
                print(f"No item found for {item_ark} - skipping file {file_name}")
                total_skipped += 1
                continue

        file_count_after = MediaFile.objects.count()
        print("Finished importing file metadata.")
        print(f"Added {file_count_after - file_count_before} rows of file metadata.")
        # print(f"Total Item Language Usages in database: {total_language_usage}")
        print(f"Total rows skipped: {total_skipped}")

    def format_date(self, date: str) -> str:
        converted_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        tz = timezone.get_current_timezone()
        date_with_tz = timezone.make_aware(converted_date, tz, True)
        return date_with_tz

    def get_mock_request(self, user: User) -> HttpRequest:
        # Get mock request with generic user info for command-line processing.
        mock_request = HttpRequest()
        mock_request.user = user
        return mock_request
