import logging
from pathlib import Path
import ffmpeg  # ffmpeg-python
from django.core.management.base import CommandError
from oh_staff_ui.classes.BaseFileHandler import BaseFileHandler
from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile
from oh_staff_ui.models import MediaFile, MediaFileError, MediaFileType

logger = logging.getLogger(__name__)


class AudioFileHandler(BaseFileHandler):
    def __init__(self, master_file: OralHistoryFile) -> None:
        self._master_file = master_file

    @property
    def master_file(self) -> OralHistoryFile:
        return self._master_file

    def create_submaster(self) -> str:
        # Minimum acceptable parameters for wav conversion
        # acodec : libmp3lame - Standard mp3 encoder selection
        # audio_bitrate : 320k - High(er) constant bitrate chosen over VBR
        #  for device compatiblity reasons.
        # ar : 44.1kHz - Matches sample rate of our source file,
        # which will always be 16 bit 44.1khz wav for this project.
        # ac : 2 channels - Forces to 2 channels in the case there are more or less present.
        # OH source files will always be 2 channels.
        # overwrite_output : True - Overwrite if existing file
        # https://kkroening.github.io/ffmpeg-python/

        input_name = self._master_file.file_name
        # Replace input_name extension with .mp3 and put in /tmp
        output_name = f"/tmp/{Path(input_name).stem}.mp3"
        try:
            logger.info(f"Converting {input_name} to {output_name}...")
            stream = ffmpeg.input(input_name)
            stream = ffmpeg.output(
                stream,
                output_name,
                acodec="libmp3lame",
                audio_bitrate="320k",
                ar=44100,
                ac=2,
            )
            ffmpeg.run(
                stream, overwrite_output=True, capture_stderr=True, capture_stdout=True
            )
            # If output file was created, log basic info;
            # otherwise, an exception probably was thrown.
            if Path(output_name).exists():
                logger.info(
                    f"Created {output_name}, size {Path(output_name).stat().st_size} bytes"
                )
            return output_name
        except ffmpeg.Error as ex:
            # ffmpeg.Error(cmd, stdout, stderr)
            # Error message for easier log searching.
            logger.error(f"Failed to create {output_name}")
            # Full exception for the record.
            # stderr captured from ffmpeg.run(), includes stdout params and
            # exception info (which is minimal anyhow).
            # ex.stderr is bytes; decode it
            error_message = ex.stderr.decode()
            logger.exception(error_message)
            # Capture ffmpeg error to database for display in template as well.
            MediaFileError.objects.create(
                file_name=input_name, item=self._master_file.item, message=error_message
            )
            # Info logged; re-raise as a CommandError to pass back to caller
            raise CommandError(f"Submaster error: Failed to create {output_name}")

    def process_files(self) -> None:
        # Process master and derivatives together.
        # Master gets saved, then any derivatives.
        try:
            # Audio items can only have one master attached.
            # Before processing, check to see if item already has files,
            # and reject this new file if it does.
            if self._item_has_files():
                error_message = f"Error: Cannot add {self._master_file.file_name}; "
                "this item already has files."
                # Capture error to database for display in template as well.
                MediaFileError.objects.create(
                    file_name=self._master_file.file_name,
                    item=self._master_file.item,
                    message=error_message,
                )
                # Pass it up to the caller.
                raise CommandError(error_message)

            self.master_file.process_media_file()
            # Get id of newly created MediaFile to use as parent for derivative(s).
            master_id = self._master_file.media_file.id
            submaster_file_name = self.create_submaster()
            # Create an OHF for the newly-generated submaster, using some
            # data from master file.
            submaster_file = OralHistoryFile(
                item_id=self._master_file.item.id,
                file_name=submaster_file_name,
                file_type=MediaFileType.objects.get(file_code="audio_submaster"),
                file_use="submaster",
                request=self._master_file.request,
            )
            submaster_file.process_media_file(parent_id=master_id)
        except (ValueError, CommandError):
            # Re-raise back to caller
            raise
        finally:
            # Delete the temporary submaster file;
            # don't throw FileNotFoundError if for some reason it doesn't exist.
            try:
                Path(submaster_file_name).unlink(missing_ok=True)
            except UnboundLocalError:
                # Swallow this, which happens when create_submaster() fails
                # so submaster_file_name is not defined.
                pass

    def _item_has_files(self) -> bool:
        """See if item associated with the media_file passed to this processor
        already has other files attached to it.
        """
        files = MediaFile.objects.filter(item=self._master_file.item)
        return True if files else False
