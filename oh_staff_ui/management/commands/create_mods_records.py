import logging
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods
from oh_staff_ui.models import ProjectItem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django management command to generate Oral History MODS records"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--item_id",
            nargs="+",
            type=int,
            required=False,
            help="The id(s) of the item to export mods record of",
        )
        parser.add_argument(
            "-b",
            "--bulk",
            type=str,
            required=False,
            choices=["series", "interview", "audio", "all"],
            help="The type of items to bulk export, choices are: series, interview, assets and all",
        )

    def handle(self, *args, **options):

        if options["item_id"]:
            for item_id in options["item_id"]:
                self._create_mods_record(item_id)

        if options["bulk"]:
            self._create_bulk_mods_records(options["bulk"])

    def _create_mods_record(self, item_id: int) -> None:
        """Given an item_id write the related MODS record to public location"""
        try:
            pi = ProjectItem.objects.get(id=item_id)
            OralHistoryMods(pi).write_mods_record()
            logger.info(f"Item: {pi.id} with ark {pi.ark} MODS record written")

        except (ProjectItem.DoesNotExist) as e:
            logger.error(e)
            raise CommandError(f"ProjectItem with id {item_id} does not exist")

    def _create_bulk_mods_records(self, category: str) -> None:
        """Only items of status 'Completed' are allowed for bulk operations"""
        err_items = ()
        pi_set = ProjectItem.objects.filter(status__status__iexact="completed")
        if category != "all":
            pi_set = pi_set.filter(type__type__iexact=category)

        for pi in pi_set:
            try:
                self._create_mods_record(pi.id)
            except (CommandError) as e:
                logger.error(e)
                err_items.append(pi)

        self.stdout.write(
            self.style.SUCCESS(
                f"{pi_set.count() - len(err_items)} of {pi_set.count()} MODS records written"
            )
        )
