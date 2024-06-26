from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    ProjectItem,
    Name,
    ItemNameUsage,
    AuthoritySource,
    NameType,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_name


class Command(BaseCommand):
    help = "Imports Name data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of name usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Name for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not AuthoritySource.objects.filter(source=row["SOURCE"]).exists():
                print(
                    f"No AuthoritySource found matching {row['SOURCE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            if not NameType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No NameType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue

            item = ProjectItem.objects.get(ark=row["ARK"])
            type = NameType.objects.get(type=row["TYPE"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            name = get_or_create_name(source, row["VALUE"])
            # avoid duplicates - only add ItemNameUsages that don't exist yet
            if not ItemNameUsage.objects.filter(
                item=item, value=name, type=type
            ).exists():
                usage = ItemNameUsage(item=item, value=name, type=type)
                usage.save()
        print("Finished importing names associated with items.")
        total_names = Name.objects.filter().count()
        total_name_usage = ItemNameUsage.objects.filter().count()
        print(f"Total Names in database: {total_names}")
        print(f"Total Item Name Usages in database: {total_name_usage}")
        print(f"Total rows skipped: {total_skipped}")
