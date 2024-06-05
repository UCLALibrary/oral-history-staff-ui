# Utility functions for file handling.
import logging
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.db.models import Max
from django.http import HttpRequest
from oh_staff_ui.models import MediaFile, MediaFileError, MediaFileType, ProjectItem

logger = logging.getLogger(__name__)


class OralHistoryFile:
    def __init__(
        self,
        item_id: int,
        file_name: str,
        file_type: MediaFileType,
        file_use: str,
        request: HttpRequest,
    ):
        # Parameters are intended as read-only by callers.
        self._item_id = item_id
        self._original_file_name = file_name
        self._file_type = file_type
        self._file_use = file_use
        self._request = request
        # Calculate several elements for later use, also read-only.
        self._file_size = self._get_file_size(self._original_file_name)
        self._item = ProjectItem.objects.get(pk=self._item_id)
        self._content_type = self.get_content_type(self._original_file_name)
        self._target_dir = self.get_target_dir(self._file_use, self._content_type)
        # Combination validation checks.
        self._validate_content_type_against_file_type()

    @property
    def content_type(self) -> str:
        return self._content_type

    @property
    def file_name(self) -> str:
        return self._original_file_name

    @property
    def file_use(self) -> str:
        return self._file_use

    @property
    def file_size(self) -> int:
        return self._file_size

    @property
    def file_type(self) -> MediaFileType:
        return self._file_type

    @property
    def item(self) -> ProjectItem:
        return self._item

    @property
    def media_file(self) -> MediaFile:
        return self._media_file

    @property
    def request(self) -> HttpRequest:
        return self._request

    @property
    def target_dir(self) -> str:
        return self._target_dir

    def process_media_file(self, parent_id: int | None = None) -> None:
        next_sequence = self._get_next_sequence(parent_id)
        new_file_name = self.get_new_file_name(next_sequence)
        # Combine filename with directory to get full path for MediaFile creation.
        new_name = f"{self._target_dir}/{new_file_name}"
        new_file = MediaFile(
            created_by=self._request.user,
            item=self._item,
            file_type=self._file_type,
            original_file_name=self._get_parent_original_name(parent_id),
            sequence=next_sequence,
            parent_id=parent_id,
        )

        # Read the original file, copying it to new_name and saving the MediaFile.
        try:
            with Path(self._original_file_name).open(mode="rb") as f:
                new_file.file = File(f, name=new_name)
                # Use original file size, since it's not available in this context.
                new_file.file_size = self._file_size
                new_file.save()
                # Also store it for read-only access by callers.
                self._media_file = new_file
        except OSError as ex:
            # Django could not copy the file from source to the relevant target directory.
            # Since we don't know exactly what went wrong, dump new_file via vars().
            error_message = (
                f"Unable to create MediaFile for an unknown reason - contact DIIT."
                f"{vars(new_file)}"
                f"Exception: {ex=}"
            )
            # Capture error to database for display in template as well.
            MediaFileError.objects.create(
                file_name=self.file_name,
                item=self.item,
                message=error_message,
            )
            # ValueError seems to fit best here for now, and is handled by callers.
            raise ValueError(error_message)

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
        elif file_ext in [".html", ".txt", ".xml"]:
            content_type = "text"

        if content_type:
            return content_type
        else:
            raise ValueError(f"Unknown content type: {file_name}")

    def get_new_file_name(
        self,
        next_sequence: int,
        file_extension: str | None = None,
    ) -> str:
        """Get new item-specific file name."""
        if not file_extension:
            file_extension = Path(self._original_file_name).suffix
        item_ark = self._item.ark.replace("/", "-")
        new_file_name = (
            f"{item_ark}-{next_sequence}-{self._file_use}{file_extension}".lower()
        )
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
            base_dir = settings.OH_MASTERS
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

    def _get_next_sequence(self, parent_id: int | None = None) -> int:
        """Get the next (max + 1) sequence number for use in naming files.

        If this is a derivative (has a parent), use the parent's sequence.
        If no records exist, return 1.
        """
        if parent_id:
            next_seq = MediaFile.objects.get(pk=parent_id).sequence
        else:
            files = MediaFile.objects.filter(item_id=self._item.id)
            if files:
                next_seq = files.aggregate(Max("sequence")).get("sequence__max") + 1
            else:
                next_seq = 1
        return next_seq

    def _get_parent_original_name(self, parent_id: int | None = None) -> str:
        """Get the original input file name of the parent file, without the full path.

        If no parent, return this object's original file name.
        """
        if parent_id:
            parent = MediaFile.objects.get(pk=parent_id)
            original_file_name = parent.original_file_name
        else:
            original_file_name = self._original_file_name
        return Path(original_file_name).name

    def _validate_content_type_against_file_type(self) -> None:
        """Validate content type against file type code.

        Raises ValueError if they do not match.
        """
        file_type_code = self._file_type.file_code
        # File type code should always start with the content type:
        # audio_master, pdf_legal_agreement, image_thumbnail, etc.
        if not file_type_code.startswith(self._content_type):
            raise ValueError(
                f"File/content type mismatch: {file_type_code=}, {self._content_type=}"
            )

    def _get_file_size(self, file_name: str) -> int:
        """Get the size of the file, in bytes.

        Returns 0 if the file doesn't exist, to avoid complicating
        migration of legacy data.
        """
        file = Path(file_name)
        if file.exists():
            return file.stat().st_size
        else:
            return 0
