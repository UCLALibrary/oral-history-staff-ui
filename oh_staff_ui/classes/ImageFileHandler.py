import logging
from PIL import ExifTags, Image, UnidentifiedImageError
from pathlib import Path
from django.conf import settings
from django.core.management.base import CommandError
from oh_staff_ui.classes.BaseFileHandler import BaseFileHandler
from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile
from oh_staff_ui.models import MediaFileType

logger = logging.getLogger(__name__)


class ImageFileHandler(BaseFileHandler):
    def __init__(self, master_file: OralHistoryFile) -> None:
        self._master_file = master_file

    @property
    def master_file(self) -> OralHistoryFile:
        return self._master_file

    def create_submaster(self) -> str:
        return self._create_derivative_image("submaster")

    def create_thumbnail(self) -> str:
        return self._create_derivative_image("thumbnail")

    def process_files(self) -> None:
        # Process master and derivatives together.
        # Master gets saved, then any derivatives.
        try:
            self.master_file.process_media_file()
            # Get id of newly created MediaFile to use as parent for derivative(s).
            master_id = self._master_file.media_file.id

            # Submaster
            submaster_file_name = self.create_submaster()
            # Create an OHF for the newly-generated submaster, using some
            # data from master file.
            submaster_file = OralHistoryFile(
                item_id=self._master_file.item.id,
                file_name=submaster_file_name,
                file_type=MediaFileType.objects.get(file_code="image_submaster"),
                file_use="submaster",
                request=self._master_file.request,
            )
            submaster_file.process_media_file(parent_id=master_id)

            # Thumbnail
            thumbnail_file_name = self.create_thumbnail()
            # Create an OHF for the newly-generated thumbnail, using some
            # data from master file.
            thumbnail_file = OralHistoryFile(
                item_id=self._master_file.item.id,
                file_name=thumbnail_file_name,
                file_type=MediaFileType.objects.get(file_code="image_thumbnail"),
                file_use="thumbnail",
                request=self._master_file.request,
            )
            thumbnail_file.process_media_file(parent_id=master_id)

        except (ValueError, CommandError):
            # Re-raise back to caller
            raise
        finally:
            # Delete the temporary files;
            # don't throw FileNotFoundError if for some reason it doesn't exist.
            try:
                Path(submaster_file_name).unlink(missing_ok=True)
                Path(thumbnail_file_name).unlink(missing_ok=True)
            except UnboundLocalError:
                # Swallow this, which happens when derivative creation fails
                # so file_name variable is not defined.
                pass

    def _create_derivative_image(self, derivative_type: str) -> str:
        """Creates a new derivative image from the master image.
        The same logic is used for both submaster and thumbnail;
        just file names and sizes differ.

        Arguments:
        derivative_type: submaster or thumbnail.
        Returns: file name of new derivative image.
        """

        if derivative_type == "submaster":
            max_size = settings.IMAGE_SETTINGS["submaster_long_dimension"]
        elif derivative_type == "thumbnail":
            max_size = settings.IMAGE_SETTINGS["thumbnail_long_dimension"]
        else:
            raise ValueError(f"Unsupported derivative type: {derivative_type}")

        input_name = self._master_file.file_name
        output_name = f"/tmp/{Path(input_name).stem}_{derivative_type}.jpg"
        try:
            with Image.open(input_name) as master_image:
                new_sizes = self._get_new_image_dimensions(master_image.size, max_size)
                orientation = self._get_orientation(master_image)
                # PIL.ImageOps.exif_transpose() should work with TIFFs... but does not seem to.
                # For now, using Image.rotate instead, handling only specific orientations which
                # can be fixed just by simple rotation. All other cases are ignored.
                # https://reference.aspose.com/imaging/net/aspose.imaging.exif.enums/exiforientation/
                # Rotation is counter-clockwise by number of degrees given;
                # must expand, at least for 90/270 degree rotation, to avoid cropping.
                # Master image is NOT changed.
                if orientation == 3:
                    # Bottom right. Rotated by 180 degrees.
                    derivative_image = master_image.rotate(180, expand=True)
                elif orientation == 6:
                    # Right top. Rotated by 90 degrees clockwise.
                    derivative_image = master_image.rotate(90, expand=True)
                elif orientation == 8:
                    # Left bottom. Rotated by 90 degrees counterclockwise.
                    derivative_image = master_image.rotate(270, expand=True)
                else:
                    # No rotation, just initialize derivative_image from the master.
                    derivative_image = master_image.copy()

                # Resizing and other changes.
                derivative_image = derivative_image.resize(new_sizes)
                if derivative_type == "thumbnail":
                    derivative_image = self._make_square_thumbnail(derivative_image)
                # Ordinary jpg does not support transparency, so convert if needed.
                if derivative_image.mode in ("RGBA", "P"):
                    derivative_image = derivative_image.convert("RGB")
                derivative_image.save(output_name)
            # If output file was created, log basic info;
            # otherwise, an exception probably was thrown.
            if Path(output_name).exists():
                logger.info(
                    f"Created {output_name}, size {Path(output_name).stat().st_size} bytes"
                )
            return output_name
        except (FileNotFoundError, OSError) as ex:
            # Error message for easier log searching.
            logger.error(f"Failed to create {output_name}")
            # Full exception for the record.
            logger.exception(ex)
            # Info logged; re-raise as a CommandError to pass back to caller
            raise CommandError(f"Submaster error: Failed to create {output_name}")

    def _get_new_image_dimensions(
        self, current_sizes: tuple[int, int], max_size: int
    ) -> tuple[int, int]:
        """Calculate new dimensions for an image.

        Arguments:
        current_sizes - tuple(width, height) of the original image.
        max_size - the longest any side should be in the new image.
        Returns: tuple(width, height)
        """
        scale_factor = max(current_sizes) / max_size
        new_sizes = tuple(int(dimension / scale_factor) for dimension in current_sizes)
        return new_sizes

    def _make_square_thumbnail(self, thumbnail_image: Image.Image) -> Image.Image:
        """Create a square thumbnail from a rectangular image, with black padding.
        To be used after image is resized to thumbnail size.

        Arguments:
        thumbnail_image: image resized such that the longest side is the thumbnail size.
        Returns: the square thumbnail.
        """
        width, height = thumbnail_image.size
        size = max(width, height)
        square_thumbnail = Image.new("RGB", (size, size), color="black")
        square_thumbnail.paste(
            thumbnail_image, (int((size - width) / 2), int((size - height) / 2))
        )
        return square_thumbnail

    def _get_orientation(self, image: Image.Image) -> int | None:
        """Obtain the image orientation from its EXIF data.

        Arguments:
        image: the image to check.
        Returns: the integer value from EXIF data, or None.
        """
        try:
            exif = image.getexif()
            return exif.get(ExifTags.Base.Orientation)
        except UnidentifiedImageError:
            logger.error(
                f"Unable to get orientation: Unidentified image {image.filename}"
            )
