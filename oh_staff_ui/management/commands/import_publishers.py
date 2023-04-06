from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    Publisher,
    PublisherType,
    AuthoritySource,
    ItemPublisherUsage,
    ProjectItem,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_publisher


class Command(BaseCommand):
    help = "Imports Publisher data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of Publisher usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Publisher for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not PublisherType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No PublisherType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
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
            type = PublisherType.objects.get(type=row["TYPE"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            publisher = get_or_create_publisher(source, row["VALUE"])
            # avoid duplicates - only add ItemNameUsages that don't exist yet
            if not ItemPublisherUsage.objects.filter(
                item=item, value=publisher, type=type
            ).exists():
                usage = ItemPublisherUsage(item=item, value=publisher, type=type)
                usage.save()
        print("Finished importing Publishers.")
        total_publishers = Publisher.objects.filter().count()
        print(f"Total Publishers in database: {total_publishers}")
        total_publisher_usage = ItemPublisherUsage.objects.filter().count()
        print(f"Total Item Publisher Usages in database: {total_publisher_usage}")
        print(f"Total rows skipped: {total_skipped}")
