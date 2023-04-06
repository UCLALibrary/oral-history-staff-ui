from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    ProjectItem,
    Language,
    ItemLanguageUsage,
    AuthoritySource,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_language


class Command(BaseCommand):
    help = "Imports Language data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of language usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Language for ARK {row['ARK']}. Row ignored.")
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

            item = ProjectItem.objects.get(ark=row["ARK"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            language = get_or_create_language(source, row["VALUE"])
            # avoid duplicates - only add ItemLanguageUsages that don't exist yet
            if not ItemLanguageUsage.objects.filter(item=item, value=language).exists():
                usage = ItemLanguageUsage(item=item, value=language)
                usage.save()
        print("Finished importing languages associated with items.")
        total_languages = Language.objects.filter().count()
        total_language_usage = ItemLanguageUsage.objects.filter().count()
        print(f"Total Languages in database: {total_languages}")
        print(f"Total Item Language Usages in database: {total_language_usage}")
        print(f"Total rows skipped: {total_skipped}")
