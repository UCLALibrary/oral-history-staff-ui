import logging
from django.core.management.base import BaseCommand
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods
from oh_staff_ui.models import ProjectItem

# For handling command-line processing
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)


def export_mods_record(item_id: int) -> None:
    """Given an item_id write the related MODS record to public location"""
    logger.info(f"{item_id = }")


class Command(BaseCommand):
    help = "Django management command to process Oral History files"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--item_id",
            type=int,
            required=True,
            help="The id of the item to export mods record of",
        )
