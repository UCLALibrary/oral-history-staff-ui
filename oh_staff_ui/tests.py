from pathlib import Path
from django.core.files import File
from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth.models import User
from oh_staff_ui.models import (
    Copyright,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemPublisherUsage,
    ItemResourceUsage,
    ItemSubjectUsage,
    Language,
    MediaFile,
    MediaFileType,
    Name,
    ProjectItem,
    Publisher,
    Resource,
    Subject,
)


class MediaFileTestCase(TestCase):
    # Load the lookup tables needed for these tests.
    fixtures = [
        "item-status-data.json",
        "item-type-data.json",
        "media-file-type-data.json",
    ]

    @classmethod
    def setUpTestData(cls):
        # Use QAD data for fake user and fake item.
        cls.user = User.objects.create_user("tester")
        cls.item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake title",
            type_id=1,
        )

    def create_master_audio_file(self):
        # Utility function used in multiple tests.
        master = MediaFile(
            created_by=self.user,
            item=self.item,
            sequence=1,
            file_type=MediaFileType.objects.get(file_type="MasterAudio1"),
        )
        path = Path("samples/sample.wav")
        # QAD rename for testing
        new_name = f"{self.item.ark.replace('/', '-')}_{path.name}"
        with path.open(mode="rb") as f:
            master.file = File(f, name=new_name)
            master.save()
        return master

    def test_master_audio_file_is_added(self):
        master = self.create_master_audio_file()
        path = Path("samples/sample.wav")
        self.assertEqual(master.file.name, "samples/managed/fake-abcdef_sample.wav")
        # Confirm the new file itself exists.
        self.assertEqual(Path(master.file.name).exists(), True)
        # For masters, new file should be same size as original.
        self.assertEqual(master.file.size, path.stat().st_size)

    def test_submaster_audio_file_is_added(self):
        master = self.create_master_audio_file()
        submaster = MediaFile(
            created_by=self.user,
            item=self.item,
            sequence=1,
            file_type=MediaFileType.objects.get(file_type="SubMasterAudio1"),
            # Submaster mp3 is a child of master wav file
            parent=master,
        )
        path = Path("samples/sample.wav")
        # QAD rename for testing - eventually, generate real mp3 file
        new_name = f"{self.item.ark.replace('/', '-')}_{path.name}.mp3"
        with path.open(mode="rb") as f:
            submaster.file = File(f, name=new_name)
            submaster.save()

        self.assertEqual(
            submaster.file.name, "samples/managed/fake-abcdef_sample.wav.mp3"
        )
        # Confirm the new file itself exists.
        self.assertEqual(Path(submaster.file.name).exists(), True)
        # Confirm we have 2 items, the master and submaster.
        self.assertEqual(MediaFile.objects.count(), 2)
        # Confirm master is parent of submaster.
        self.assertEqual(master, submaster.parent)

    def tearDown(self):
        # If new files aren't deleted, Django will create next file with random-ish name.
        # Deleting the MediaFile object does *not* automatically delete the file itself.
        for mf in MediaFile.objects.all():
            mf.file.delete()


class MetadataUniquenessTestCase(TestCase):
    # Load the lookup tables needed for these tests.
    fixtures = [
        "authority-source-data.json",
        "item-status-data.json",
        "item-type-data.json",
        "name-type-data.json",
    ]

    @classmethod
    def setUpTestData(cls):
        # Use QAD data for fake user and fake item.
        cls.user = User.objects.create_user("tester")
        cls.item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake title",
            type_id=1,
        )

    def test_name_usage_is_unique(self):
        # Add the same name/type combination to an item twice
        name = Name.objects.create(value="fake name", source_id=1)
        ItemNameUsage.objects.create(item=self.item, value=name, type_id=1)
        with self.assertRaises(IntegrityError):
            ItemNameUsage.objects.create(item=self.item, value=name, type_id=1)

    def test_subject_usage_is_unique(self):
        subject = Subject.objects.create(value="fake subject", source_id=1)
        ItemSubjectUsage.objects.create(item=self.item, value=subject, type_id=1)
        with self.assertRaises(IntegrityError):
            ItemSubjectUsage.objects.create(item=self.item, value=subject, type_id=1)

    def test_publisher_usage_is_unique(self):
        publisher = Publisher.objects.create(value="fake publisher", source_id=1)
        ItemPublisherUsage.objects.create(item=self.item, value=publisher, type_id=1)
        with self.assertRaises(IntegrityError):
            ItemPublisherUsage.objects.create(
                item=self.item, value=publisher, type_id=1
            )

    def test_copyright_usage_is_unique(self):
        copyright = Copyright.objects.create(value="fake copyright", source_id=1)
        ItemCopyrightUsage.objects.create(item=self.item, value=copyright, type_id=1)
        with self.assertRaises(IntegrityError):
            ItemCopyrightUsage.objects.create(
                item=self.item, value=copyright, type_id=1
            )

    def test_resource_usage_is_unique(self):
        resource = Resource.objects.create(value="fake resource", source_id=1)
        ItemResourceUsage.objects.create(item=self.item, value=resource, type_id=1)
        with self.assertRaises(IntegrityError):
            ItemResourceUsage.objects.create(item=self.item, value=resource, type_id=1)

    def test_language_usage_is_unique(self):
        language = Language.objects.create(value="fake language", source_id=1)
        ItemLanguageUsage.objects.create(item=self.item, value=language)
        with self.assertRaises(IntegrityError):
            ItemLanguageUsage.objects.create(item=self.item, value=language)
    
    def test_item_id_is_unique(self):
        with self.assertRaises(IntegrityError):
            item = ProjectItem.objects.create(
                pk=self.item.pk,
                ark=self.item.ark,
                created_by=self.user,
                last_modified_by=self.user,
                title="Fake title",
                type_id=1
            )
