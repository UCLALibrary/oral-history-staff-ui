from django.core.management.base import BaseCommand
from oh_staff_ui.models import ProjectItem, ItemStatus, ItemType
from django.contrib.auth.models import User
from csv import DictReader
import os
import datetime


class Command(BaseCommand):
    help = "Deletes all existing ProjectItem data, then imports from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        # to avoid duplication, start by deleting all existing ProjectItems
        print("Deleting all existing ProjectItems.")
        ProjectItem.objects.all().delete()

        # open and read input CSV - assuming it's in the fixtures folder
        filepath = os.path.join("oh_staff_ui/fixtures", options["filename"])
        with open(filepath, mode="r") as f:
            dict_reader = DictReader(f)
            projectitem_dicts = list(dict_reader)
        total_rows = len(projectitem_dicts)
        print(f"Found {total_rows} ProjectItems to import.")

        # start with known top-level ProjectItem
        # handled outside of main loop due to lack of parent
        added_items = []
        root_item = next(
            item for item in projectitem_dicts if item["ARK"] == "21198/zz0008zh0f"
        )
        # create and save ProjectItem for root object
        p = ProjectItem(
            ark=root_item["ARK"],
            create_date=self.format_date(root_item["CREATE_DATE"]),
            created_by=self.get_or_create_user(root_item["CREATED_BY"]),
            last_modified_date=self.format_date(root_item["LAST_MODIFIED_DATE"]),
            last_modified_by=self.get_or_create_user(root_item["LAST_MODIFIED_BY"]),
            sequence=self.format_sequence(root_item["SEQUENCE"]),
            status=ItemStatus.objects.get(status=root_item["STATUS"]),
            title=root_item["TITLE"],
            type=ItemType.objects.get(type=root_item["TYPE"]),
        )
        p.save()
        added_items.append(root_item)

        # main logical loop
        # until we've added all items, look in imported data for children of added items
        # for each child we haven't seen already,
        # save a PI object and add to list of completed items
        while len(added_items) < len(projectitem_dicts):
            for parent in added_items:
                child_items = self.find_child_items(projectitem_dicts, parent["ARK"])
                for child in child_items:
                    if child not in added_items:
                        self.add_projectitem(child)
                        added_items.append(child)
        total_added = len(added_items)
        print(f"Finished adding {total_added} ProjectItems.")
        total_projectitems = ProjectItem.objects.filter().count()
        print(f"Number of ProjectItems in database: {total_projectitems}.")

    def find_child_items(self, projectitem_dicts: list, parent_ark: str) -> list:
        output_items = []
        for line in projectitem_dicts:
            if line["PARENT_ARK"] == parent_ark:
                output_items.append(line)
        return output_items

    def add_projectitem(self, pi_dict: dict) -> list:
        p = ProjectItem(
            ark=pi_dict["ARK"],
            create_date=self.format_date(pi_dict["CREATE_DATE"]),
            created_by=self.get_or_create_user(pi_dict["CREATED_BY"]),
            last_modified_date=self.format_date(pi_dict["LAST_MODIFIED_DATE"]),
            last_modified_by=self.get_or_create_user(pi_dict["LAST_MODIFIED_BY"]),
            parent=ProjectItem.objects.get(ark=pi_dict["PARENT_ARK"]),
            sequence=self.format_sequence(pi_dict["SEQUENCE"]),
            status=ItemStatus.objects.get(status=pi_dict["STATUS"]),
            title=pi_dict["TITLE"],
            type=ItemType.objects.get(type=pi_dict["TYPE"]),
        )
        p.save()

    def format_date(self, date: str) -> str:
        return datetime.datetime.strptime(date, "%d-%b-%y").strftime("%Y-%m-%d")

    def format_sequence(self, seq) -> int:
        if seq == "":
            seq = 0
        return seq

    def get_or_create_user(self, email: str) -> User:
        username = email.split("@")[0]
        if User.objects.filter(username=username).exists():
            return User.objects.get(username=username)
        else:
            print(f"Created new user for email {email}")
            return User.objects.create_user(username, email=email)
