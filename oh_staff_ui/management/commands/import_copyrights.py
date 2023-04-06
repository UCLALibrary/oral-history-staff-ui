from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    Copyright,
    CopyrightType,
    AuthoritySource,
    ItemCopyrightUsage,
    ProjectItem,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_copyright


class Command(BaseCommand):
    help = "Imports Copyright data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of Copyright usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Copyright for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not CopyrightType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No CopyrightType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            if not AuthoritySource.objects.filter(source=row["SOURCE"]).exists():
                print(
                    f"No AuthoritySource found matching {row['SOURCE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue
            item = ProjectItem.objects.get(ark=row["ARK"])
            type = CopyrightType.objects.get(type=row["TYPE"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            copyright = get_or_create_copyright(source, row["VALUE"])
            # avoid duplicates - only add ItemNameUsages that don't exist yet
            if not ItemCopyrightUsage.objects.filter(
                item=item, value=copyright, type=type
            ).exists():
                usage = ItemCopyrightUsage(item=item, value=copyright, type=type)
                usage.save()
        print("Finished importing Copyrights.")
        total_copyrights = Copyright.objects.filter().count()
        print(f"Total Copyrights in database: {total_copyrights}")
        total_copyright_usage = ItemCopyrightUsage.objects.filter().count()
        print(f"Total Item Copyright Usages in database: {total_copyright_usage}")
        print(f"Total rows skipped: {total_skipped}")
