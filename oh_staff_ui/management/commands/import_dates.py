from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem, DateType, Date
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports Date data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of Dates to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Date for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not DateType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No DateType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            item = ProjectItem.objects.get(ark=row["ARK"])
            type = DateType.objects.get(type=row["TYPE"])
            # avoid duplicates - check for existing Dates
            if not Date.objects.filter(
                value=row["VALUE"], item=item, type=type
            ).exists():
                date = Date(value=row["VALUE"], item=item, type=type)
                date.save()

        print("Finished importing Dates.")
        total_dates = Date.objects.filter().count()
        print(f"Total Dates in database: {total_dates}")
        print(f"Total rows skipped: {total_skipped}")
