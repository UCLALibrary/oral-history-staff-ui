from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    Subject,
    SubjectType,
    AuthoritySource,
    ItemSubjectUsage,
    ProjectItem,
)
from ._import_utils import get_dicts_from_tsv, get_or_create_subject


class Command(BaseCommand):
    help = "Imports Subject data from a TSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str)

    def handle(self, *args, **options):
        dicts_list = get_dicts_from_tsv(options["filepath"])

        print(f"Found {len(dicts_list)} rows of Subject usage to import.")

        total_skipped = 0
        for row in dicts_list:
            if not row["VALUE"]:
                print(f"Empty Subject for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not ProjectItem.objects.filter(ark=row["ARK"]).exists():
                print(f"No ProjectItem found for ARK {row['ARK']}. Row ignored.")
                total_skipped += 1
                continue
            if not SubjectType.objects.filter(type=row["TYPE"]).exists():
                print(
                    f"No SubjectType found matching {row['TYPE']} for ARK {row['ARK']}. Row ignored."
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
            type = SubjectType.objects.get(type=row["TYPE"])
            source = AuthoritySource.objects.get(source=row["SOURCE"])
            subject = get_or_create_subject(source, row["VALUE"])
            # avoid duplicates - only add ItemNameUsages that don't exist yet
            if not ItemSubjectUsage.objects.filter(
                item=item, value=subject, type=type
            ).exists():
                usage = ItemSubjectUsage(item=item, value=subject, type=type)
                usage.save()
        print("Finished importing Subjects.")
        total_subjects = Subject.objects.filter().count()
        print(f"Total Subjects in database: {total_subjects}")
        total_subject_usage = ItemSubjectUsage.objects.filter().count()
        print(f"Total Item Subject Usages in database: {total_subject_usage}")
        print(f"Total rows skipped: {total_skipped}")
