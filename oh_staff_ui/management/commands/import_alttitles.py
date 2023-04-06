from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem, AltTitleType, AltTitle
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports AltTitle data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of AltTitles to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty AltTitle for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not AltTitleType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No AltTitleType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            item = ProjectItem.objects.get(ark=row["ARK"])
            type = AltTitleType.objects.get(type=row["TYPE"])
            # avoid duplicates - check for existing AltTitles
            if not AltTitle.objects.filter(
                value=row["VALUE"], item=item, type=type
            ).exists():
                alttitle = AltTitle(value=row["VALUE"], item=item, type=type)
                alttitle.save()

        print("Finished importing AltTitles.")
        total_alttitles = AltTitle.objects.filter().count()
        print(f"Total AltTitles in database: {total_alttitles}")
        print(f"Total rows skipped: {total_skipped}")
