from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    ProjectItem,
    Resource,
    ItemResourceUsage,
    AuthoritySource,
    ResourceType,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_resource


class Command(BaseCommand):
    help = "Imports Resource data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of resource usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Resource value for ARK {row['ARK']}. Row ignored.")
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
            if not ResourceType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No ResourceType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
                )
                total_skipped += 1
                continue

            item = ProjectItem.objects.get(ark=row["ARK"])
            type = ResourceType.objects.get(type=row["TYPE"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            resource = get_or_create_resource(source, row["VALUE"])
            # avoid duplicates - only add ItemResourceUsages that don't exist yet
            if not ItemResourceUsage.objects.filter(
                item=item, value=resource, type=type
            ).exists():
                usage = ItemResourceUsage(item=item, value=resource, type=type)
                usage.save()
        print("Finished importing resources associated with items.")
        total_resources = Resource.objects.filter().count()
        total_resource_usage = ItemResourceUsage.objects.filter().count()
        print(f"Total Resources in database: {total_resources}")
        print(f"Total Item Resource Usages in database: {total_resource_usage}")
        print(f"Total rows skipped: {total_skipped}")
