import logging
from pathlib import Path
import shutil
from django.core.management.base import CommandError
from oh_staff_ui.classes.BaseFileHandler import BaseFileHandler
from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile


logger = logging.getLogger(__name__)


class GeneralFileHandler(BaseFileHandler):
    def __init__(self, master_file: OralHistoryFile) -> None:
        self._master_file = master_file

    @property
    def master_file(self) -> OralHistoryFile:
        return self._master_file

    def create_submaster(self) -> str:
        input_name = self._master_file.file_name
        # Use same filename and put in /tmp
        output_name = f"/tmp/{Path(input_name).name}"
        # Copy the file.  Not really necessary... but consistent
        # with Audio/Image handlers which generate actual derivatives.
        try:
            shutil.copyfile(input_name, output_name)
        except OSError as ex:
            # Error message for easier log searching.
            logger.error(f"Failed to create {output_name}")
            # Full exception for the record.
            logger.exception(ex)
            # Info logged; re-raise as a CommandError to pass back to caller
            raise CommandError(f"Submaster error: Failed to create {output_name}")
        return output_name

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
                # General submasters have same file type as masters.
                file_type=self._master_file.file_type,
                file_use="submaster",
                request=self._master_file.request,
            )
            submaster_file.process_media_file(parent_id=master_id)

        except (ValueError, CommandError):
            # Re-raise back to caller
            raise
        finally:
            # Delete the temporary files;
            # don't throw FileNotFoundError if for some reason it doesn't exist.
            try:
                Path(submaster_file_name).unlink(missing_ok=True)
            except UnboundLocalError:
                # Swallow this, which happens when derivative creation fails
                # so file_name variable is not defined.
                pass
