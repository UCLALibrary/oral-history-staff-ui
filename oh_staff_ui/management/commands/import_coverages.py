from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports ProjectItem coverage data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of coverages to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Coverage for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            item = ProjectItem.objects.get(ark=row["ARK"])
            item.coverage = row["VALUE"]
            item.save()

        print("Finished importing coverages.")
        print(f"Total rows skipped: {total_skipped}")
