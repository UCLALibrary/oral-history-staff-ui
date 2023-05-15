from datetime import datetime
from pathlib import Path
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

        print("*** WARNING *** DELETING EXISTING DATA DURING TESTING ***")
        MediaFile.objects.all().delete()

        file_count_before = MediaFile.objects.count()
        total_skipped = 0
        for row in dicts_list:
            try:
                # content_type = row["CONTENT_TYPE"]
                create_date = self.format_date(row["CREATE_DATE"])
                # db_file_group_title = row["FILE_GROUP_TITLE"]
                file_location = row["FILE_LOCATION"]
                db_file_name = row["FILE_NAME"]
                file_size = row["FILE_SIZE"]
                file_use = row["FILE_USE"].lower()
                item_ark = row["ITEM_ARK"]
                sequence = row["SEQ"]
                # Some legacy data has empty file size
                if file_size == "":
                    file_size = 0
                # Hundreds of mismatches in DLCS db... make best guess
                file_group_title = self.get_correct_file_group(row)
                # Make legacy data match cleaned-up name in Django
                if file_group_title == "PDF  Résumé":
                    file_group_title = "PDF Résumé"

                # Start database interaction
                file_type = MediaFileType.objects.get(file_type=file_group_title)
                item = ProjectItem.objects.get(ark=item_ark)

                # Use OHF initialization, just for data validation;
                # throws ValueError on failures, caught below.
                ohf = OralHistoryFile(
                    item_id=item.id,
                    file_name=db_file_name,
                    file_type=file_type,
                    file_use=file_use,
                    request=self.get_mock_request(item.created_by),
                )

                # Get full real production path & file name
                # print(f"{ohf.target_dir} ===> {file_name} ===> {file_location}")
                full_file_name = self.get_full_file_name(
                    ohf.target_dir, db_file_name, file_location
                )

                # Create object; can raise FileExistsError
                MediaFile.objects.create(
                    created_by=item.created_by,
                    create_date=create_date,
                    file=full_file_name,
                    file_size=file_size,
                    file_type=file_type,
                    original_file_name="Unknown",
                    sequence=sequence,
                    item=item,
                    # Not trying to set parent for migrated file info
                    parent=None,
                )
                print(f"Migrated {db_file_name} to {full_file_name}")
            except MediaFileType.DoesNotExist:
                print(
                    f"No file type found for {file_group_title} - skipping file {db_file_name}"
                )
                total_skipped += 1
                continue
            except ProjectItem.DoesNotExist:
                print(f"No item found for {item_ark} - skipping file {db_file_name}")
                total_skipped += 1
                continue
            except ValueError as ex:
                print(f"\n{ex}")
                print(row)
                total_skipped += 1
                continue
            except FileExistsError as ex:
                print(f"\n{ex}")
                # List all data from the source file for easy comparison.
                dup_files = [r for r in dicts_list if r["FILE_NAME"] == db_file_name]
                # for dup in sorted(dup_files, key=lambda d: d["CREATE_DATE"]):
                for dup in dup_files:
                    print(dup)
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

    def get_correct_file_group(self, data_row: list[str]) -> str:
        # Trust the filename extension, and use it to correct the file group.
        db_file_group = data_row["FILE_GROUP_TITLE"]
        file_name = data_row["FILE_NAME"]
        extension = Path(file_name).suffix
        # If data mismatch, correct it and print the row for possible future cleanup.
        if extension == ".pdf" and not db_file_group.startswith("PDF"):
            new_file_group = "PDF"
        elif extension in [".html", ".xml"] and not db_file_group.startswith("Text"):
            # Some of these may not be transcripts...
            new_file_group = "Text Transcript"
        elif extension in [".tif", ".tiff"] and db_file_group != "MasterImage1":
            new_file_group = "MasterImage1"
        # Nothing to fix, return the original value
        else:
            new_file_group = db_file_group

        if new_file_group != db_file_group:
            print(
                f"\nWARNING: File/content mismatch for {file_name}, "
                f"changed {db_file_group} to {new_file_group}"
            )
            print(data_row)

        return new_file_group

    def get_full_file_name(
        self, target_dir: str, file_name: str, file_location: str
    ) -> str:
        # Combine file name and target dir for full path, with some corrections.

        # Newer mp3 submasters are in audio/submasters subdirectory, matching target dir;
        # older ones are not, so remove that subdirectory to match.
        if "audio/submasters" not in file_location:
            target_dir = target_dir.replace("/audio/submasters", "")

        # Some legacy filenames have path info already; remove it.
        file_name = Path(file_name).name

        # Finally, combine and return
        return f"{target_dir}/{file_name}"
