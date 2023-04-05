from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem, AltIdType, AltId
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports AltId data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of AltIds to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty AltID for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not AltIdType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No AltIdType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue

            item = ProjectItem.objects.get(ark=row["ARK"])
            type = AltIdType.objects.get(type=row["TYPE"])
            # avoid duplicates - check for existing AltIds
            if not AltId.objects.filter(
                value=row["VALUE"], item=item, type=type
            ).exists():
                altID = AltId(value=row["VALUE"], item=item, type=type)
                altID.save()

        print("Finished importing AltIds.")
        total_altIDs = AltId.objects.filter().count()
        print(f"Total AltIds in database: {total_altIDs}")
        print(f"Total rows skipped: {total_skipped}")
