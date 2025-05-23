import logging
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.http import HttpRequest
from oh_staff_ui.classes.AudioFileHandler import AudioFileHandler
from oh_staff_ui.classes.GeneralFileHandler import GeneralFileHandler
from oh_staff_ui.classes.ImageFileHandler import ImageFileHandler
from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile
from oh_staff_ui.models import MediaFileType

# For handling command-line processing
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


def process_file(
    item_id: int, file_name: str, file_type: MediaFileType, request: HttpRequest
) -> None:
    """Do the actual work.

    This script only processes user-uploaded files, which are always masters.
    Create initial file object, determine content type, then pass it to
    an appropriate handler to generate derivatives and save all to database
    and file system.
    """
    file_use = "master"
    try:
        master_file = OralHistoryFile(item_id, file_name, file_type, file_use, request)
        content_type = master_file.content_type
        if content_type == "audio":
            handler = AudioFileHandler(master_file)
        elif content_type == "image":
            handler = ImageFileHandler(master_file)
        elif content_type in ["pdf", "text"]:
            handler = GeneralFileHandler(master_file)
        else:
            # No code here; OralHistoryFile (above) raises ValueError on unsupported content_type.
            pass

        # Do whatever needs to be done
        handler.process_files()
    except (CommandError, ValueError) as ex:
        # AudioFileHandler raises CommandError if ffmpeg fails.
        # OralHistoryFile raises ValueError if validation fails.
        logger.error(ex)
        # Pass the exception up to the caller.
        raise


def get_mock_request() -> HttpRequest:
    """Get mock request with generic user info for command-line processing."""
    mock_request = HttpRequest()
    mock_request.user = User.objects.get(username="oralhistory data entry")
    return mock_request


class Command(BaseCommand):
    help = "Django management command to process Oral History files"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--item_id",
            type=int,
            required=True,
            help="The id of the item to attach file to",
        )
        parser.add_argument(
            "-f",
            "--file_name",
            type=str,
            required=True,
            help="The full path of the file to process",
        )
        master_types = self._get_master_file_type_codes()
        parser.add_argument(
            "-t",
            "--file_type",
            type=str,
            required=True,
            help=f"The file type code of the file to process; must be one of {master_types}",
        )
        parser.add_argument(
            "-r",
            "--request",
            required=False,
            help="The request from the view - do not use via command line",
        )

    def handle(self, *args, **options):
        item_id = options["item_id"]
        file_name = options["file_name"]
        file_type = options["file_type"]
        request = options["request"]
        # For command-line processing
        if not isinstance(file_type, MediaFileType):
            file_type = MediaFileType.objects.get(file_code=options["file_type"])
        if request is None:
            request = get_mock_request()

        process_file(item_id, file_name, file_type, request)

    def _get_master_file_type_codes(self) -> list[str]:
        """Get the codes for master file types."""
        return [
            mf.file_code
            for mf in MediaFileType.objects.filter(
                file_code__contains="_master"
            ).order_by("file_code")
        ]
