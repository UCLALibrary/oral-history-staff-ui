import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandParser
from django.core.management.base import CommandError
from django.http import HttpRequest
from django.db.models.query import QuerySet
from django.conf import settings
from oh_staff_ui.classes.ImageFileHandler import ImageFileHandler
from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile
from oh_staff_ui.models import MediaFile, MediaFileType

# For handling command-line processing
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


def reprocess_derivative_images(master_images: QuerySet) -> None:
    """Reprocess all derivative images from masters."""
    try:
        for master_image in master_images:
            logger.info(f"Processing master image {master_image.file.name}")
            # Get id of newly created MediaFile to use as parent for derivative(s)
            master_id = master_image.id
            # Create an OHF for the master file so we can use ImageFileHandler
            master_file = OralHistoryFile(
                master_image.item.id,
                Path(settings.MEDIA_ROOT).joinpath(master_image.file.name),
                master_image.file_type,
                "master",
                get_mock_request(),
            )
            handler = ImageFileHandler(master_file)

            # Submaster - generate and save
            submaster_file_name = handler.create_submaster()
            submaster_file = OralHistoryFile(
                item_id=master_image.item.id,
                file_name=submaster_file_name,
                file_type=MediaFileType.objects.get(file_code="image_submaster"),
                file_use="submaster",
                request=get_mock_request(),
            )
            submaster_file.process_media_file(parent_id=master_id)
            logger.info(f"Submaster image {submaster_file_name} created")

            # Thumbnail - generate and save
            thumbnail_file_name = handler.create_thumbnail()
            thumbnail_file = OralHistoryFile(
                item_id=master_image.item.id,
                file_name=thumbnail_file_name,
                file_type=MediaFileType.objects.get(file_code="image_thumbnail"),
                file_use="thumbnail",
                request=get_mock_request(),
            )
            thumbnail_file.process_media_file(parent_id=master_id)
            logger.info(f"Thumbnail image {thumbnail_file_name} created")

    except (CommandError, ValueError) as ex:
        logger.error(ex)
        raise


def delete_existing_derivative_images(master_images: QuerySet) -> None:
    """Delete existing derivative images from masters."""
    try:
        for master_image in master_images:
            master_id = master_image.id
            MediaFile.objects.filter(
                item=master_image.item,
                parent_id=master_id,
                file_type__file_code__in=["image_submaster", "image_thumbnail"],
            ).delete()
            logger.info(
                f"Deleted existing derivative images for master {master_image.file.name}"
            )

    except (CommandError, ValueError) as ex:
        logger.error(ex)
        raise


def get_mock_request() -> HttpRequest:
    """Get mock request with generic user info for command-line processing."""
    mock_request = HttpRequest()
    mock_request.user = User.objects.get(username="oralhistory")
    return mock_request


class Command(BaseCommand):
    help = "Django management command to reprocess derivative images"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--project_item_id",
            type=int,
            help="ID of ProjectItem to reprocess derivative images for",
            required=False,
        )

    def handle(self, *args, **options) -> None:
        if options["project_item_id"]:
            master_images = MediaFile.objects.filter(
                item__id=options["project_item_id"],
                file_type__file_code="image_master",
            ).order_by("id")

        else:
            master_images = MediaFile.objects.filter(
                file_type__file_code="image_master"
            ).order_by("id")

        master_image_count = master_images.count()
        logger.info(f"Found {master_image_count} master images to reprocess")

        delete_existing_derivative_images(master_images)
        reprocess_derivative_images(master_images)
