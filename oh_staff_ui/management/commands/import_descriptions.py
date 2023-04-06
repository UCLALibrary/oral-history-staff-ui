from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem, DescriptionType, Description
from ._import_utils import get_dicts_from_tsv


class Command(BaseCommand):
    help = "Imports Description data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of Descriptions to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Description for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not DescriptionType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No DescriptionType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            item = ProjectItem.objects.get(ark=row["ARK"])
            type = DescriptionType.objects.get(type=row["TYPE"])
            # avoid duplicates - check for existing Descriptions
            if not Description.objects.filter(
                value=row["VALUE"], item=item, type=type
            ).exists():
                description = Description(value=row["VALUE"], item=item, type=type)
                description.save()

        print("Finished importing Descriptions.")
        total_descriptions = Description.objects.filter().count()
        print(f"Total Descriptions in database: {total_descriptions}")
        print(f"Total rows skipped: {total_skipped}")
