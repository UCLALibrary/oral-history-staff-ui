import logging
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods
from oh_staff_ui.models import ProjectItem

logger = logging.getLogger(__name__)


def create_mods_records(item_id: int) -> None:
    """Given an item_id write the related MODS record to public location"""
    try:
        pi = ProjectItem.objects.get(id=item_id)
        OralHistoryMods(pi).write_mods_record()
    except (ProjectItem.DoesNotExist) as e:
        logger.error(e)
        raise CommandError(f"ProjectItem with id {item_id} does not exist")


class Command(BaseCommand):
    help = "Django management command to generate Oral History MODS records"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--item_id",
            type=int,
            required=True,
            help="The id of the item to export mods record of",
        )

    def handle(self, *args, **options):

        item_id = options["item_id"]
        create_mods_records(item_id)
