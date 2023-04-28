# Utility functions for file handling.
import logging
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.db.models import Max
from django.http import HttpRequest
from oh_staff_ui.models import MediaFile, ProjectItem

logger = logging.getLogger(__name__)


class OralHistoryFile:
    def __init__(
        self,
        item_id: int,
        file_name: str,
        file_type: str,
        file_use: str,
        request: HttpRequest,
    ):
        self.item_id = item_id
        self.file_name = file_name
        self.file_type = file_type
        self.file_use = file_use
        self.request = request
        # Expose several elements for testing and other use.
        self.item = ProjectItem.objects.get(pk=self.item_id)
        self.content_type = self.get_content_type(self.file_name)
        self.target_dir = self.get_target_dir(self.file_use, self.content_type)
        self.next_sequence = self._get_next_sequence(self.item_id)
        self.new_file_name = self.get_new_file_name(
            self.file_name, self.item, self.file_use
        )

    def process_media_file(self) -> None:
        # Combine filename with directory to get full path for MediaFile creation.
        new_name = f"{self.target_dir}/{self.new_file_name}"
        logger.info(f"{new_name = }")

        # TODO: Processing, based on file_type
        new_file = MediaFile(
            created_by=self.request.user,
            item=self.item,
            file_type=self.file_type,
            sequence=self.next_sequence,
        )
        # Read the original file, copying it to new_name and saving the MediaFile.
        with Path(self.file_name).open(mode="rb") as f:
            new_file.file = File(f, name=new_name)
            new_file.save()
            self.media_file = new_file

    def get_content_type(self, file_name: str) -> str:
        """Get broad type of content based on file extension.

        Only used for master files.
        """
        content_type = None
        file_ext = Path(file_name).suffix.lower()
        if file_ext in [".mp3", ".wav"]:
            content_type = "audio"
        elif file_ext in [".jpg", ".jpeg", ".tif", ".tiff"]:
            content_type = "image"
        elif file_ext in [".pdf"]:
            content_type = "pdf"
        elif file_ext in [".txt", ".xml"]:
            content_type = "text"

        if content_type:
            return content_type
        else:
            raise ValueError(f"Unknown content type: {file_name}")

    def get_new_file_name(
        self,
        old_name: str,
        item: ProjectItem,
        file_use: str,
        file_extension: str = None,
    ) -> str:
        """Get new item-specific file name."""
        if not file_extension:
            file_extension = Path(old_name).suffix
        item_ark = item.ark.replace("/", "-")
        next_sequence = self.next_sequence
        new_file_name = f"{item_ark}-{next_sequence}-{file_use}{file_extension}".lower()
        return new_file_name

    def get_target_dir(self, file_use: str, content_type: str) -> str:
        """Get target directory based on content type and file use (master, etc.)."""
        try:
            # Any of these can raise ValueError
            base_dir = self._get_base_dir(file_use, content_type)
            file_use_folder = self._get_file_use_folder(file_use)
            media_folder = self._get_media_folder(content_type)

            target_dir = f"{base_dir}{media_folder}{file_use_folder}"
            return target_dir
        except ValueError as ex:
            raise ValueError(
                f"Unable to determine target directory: {file_use=}, {content_type=}, {ex=}"
            )

    def _get_base_dir(self, file_use: str, content_type: str) -> str:
        if file_use == "master":
            base_dir = settings.OH_MASTERSLZ
        elif file_use == "submaster":
            if content_type == "audio":
                base_dir = settings.OH_WOWZA
            else:
                base_dir = settings.OH_STATIC
        # Thumbnails are only for images
        elif file_use == "thumbnail" and content_type == "image":
            base_dir = settings.OH_STATIC
        else:
            raise ValueError(
                f"Unable to determine base directory: {file_use=}, {content_type=}"
            )
        return base_dir

    def _get_file_use_folder(self, file_use: str) -> str:
        if file_use == "master":
            file_use_folder = "/masters"
        elif file_use == "submaster":
            file_use_folder = "/submasters"
        elif file_use == "thumbnail":
            file_use_folder = "/nails"
        else:
            raise ValueError(f"Unable to determine file use folder: {file_use=}")
        return file_use_folder

    def _get_media_folder(self, content_type: str) -> str:
        if content_type == "image":
            # Special case
            media_folder = ""
        elif content_type in ["audio", "pdf", "text"]:
            media_folder = f"/{content_type}"
        else:
            raise ValueError(f"Unable to determine media folder: {content_type=}")
        return media_folder

    def _get_next_sequence(self, item_id: int) -> int:
        """Get the next (max + 1) sequence number for use in naming files.

        If no records exist, return 1.
        """
        files = MediaFile.objects.filter(item_id=item_id)
        if files:
            next_seq = files.aggregate(Max("sequence")).get("sequence__max") + 1
        else:
            next_seq = 1
        return next_seq
