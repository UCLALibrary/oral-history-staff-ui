from django.core.management.base import BaseCommand
from oh_staff_ui.models import (
    ProjectItem,
    Name,
    ItemNameUsage,
    AuthoritySource,
    NameType,
)
from csv import DictReader
import os


class Command(BaseCommand):
    help = "Imports Name data from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        # open and read input CSV - assuming it's in the fixtures folder
        filepath = os.path.join("oh_staff_ui/fixtures", options["filename"])
        print(os.listdir("oh_staff_ui/fixtures"))
        with open(filepath, mode="r") as f:
            dict_reader = DictReader(f)
            name_dicts = list(dict_reader)

        print(f"Found {len(name_dicts)} rows to import.")
        for row in name_dicts:
            item = ProjectItem.objects.get(ark=row["ARK"])
            source = self.get_or_create_source(row["SOURCE"])
            name = self.get_or_create_name(source, row["VALUE"])
            type = self.get_or_create_nametype(row["TYPE"])
            usage = ItemNameUsage(item=item, name=name, type=type)
            usage.save()

    def get_or_create_source(self, source=str) -> AuthoritySource:
        if AuthoritySource.objects.filter(source=source).exists():
            return AuthoritySource.objects.get(source=source)
        else:
            auth_source = AuthoritySource(source=source)
            auth_source.save()
            return auth_source

    def get_or_create_name(self, source=AuthoritySource, value=str) -> Name:
        if Name.objects.filter(source=source, value=value).exists():
            return Name.objects.get(source=source, value=value)
        else:
            name = Name(source=source, value=value)
            name.save()
            return name

    def get_or_create_nametype(self, type=str) -> NameType:
        if NameType.objects.filter(type=type).exists():
            return NameType.objects.get(type=type)
        else:
            nametype = NameType(type=type)
            nametype.save()
            return nametype
