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
from oh_staff_ui.file_utils import get_content_type, get_new_file_name, get_target_dir


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
        file_use = "master"
        content_type = "audio"
        target_dir = get_target_dir(file_use, content_type)
        path = Path("samples/sample.wav")
        new_file_name, next_sequence = get_new_file_name(path.name, self.item, file_use)
        # Combine filename with directory to get full path for MediaFile creation.
        new_name = f"{target_dir}/{new_file_name}"
        master = MediaFile(
            created_by=self.user,
            item=self.item,
            sequence=next_sequence,
            file_type=MediaFileType.objects.get(file_type="MasterAudio1"),
        )
        with path.open(mode="rb") as f:
            master.file = File(f, name=new_name)
            master.save()
        return master

    def test_master_audio_file_is_added(self):
        master = self.create_master_audio_file()
        path = Path("samples/sample.wav")
        self.assertEqual(
            master.file.name, "media_dev/oh_lz/audio/masters/fake-abcdef-1-master.wav"
        )
        # Confirm the new file itself exists.
        self.assertEqual(Path(master.file.name).exists(), True)
        # For masters, new file should be same size as original.
        self.assertEqual(master.file.size, path.stat().st_size)

    def test_submaster_audio_file_is_added(self):
        master = self.create_master_audio_file()
        file_use = "submaster"
        content_type = "audio"
        target_dir = get_target_dir(file_use, content_type)
        path = Path("samples/sample.wav")
        # QAD rename for testing - eventually, generate real mp3 file
        new_file_name, next_sequence = get_new_file_name(
            path.name, self.item, file_use, ".mp3"
        )
        # Combine filename with directory to get full path for MediaFile creation.
        new_name = f"{target_dir}/{new_file_name}"
        submaster = MediaFile(
            created_by=self.user,
            item=self.item,
            sequence=next_sequence,
            file_type=MediaFileType.objects.get(file_type="SubMasterAudio1"),
            # Submaster mp3 is a child of master wav file
            parent=master,
        )
        with path.open(mode="rb") as f:
            submaster.file = File(f, name=new_name)
            submaster.save()

        self.assertEqual(
            submaster.file.name,
            "media_dev/oh_wowza/audio/submasters/fake-abcdef-2-submaster.mp3",
        )
        # Confirm the new file itself exists.
        self.assertEqual(Path(submaster.file.name).exists(), True)
        # Confirm we have 2 items, the master and submaster.
        self.assertEqual(MediaFile.objects.count(), 2)
        # Confirm master is parent of submaster.
        self.assertEqual(master, submaster.parent)

    def test_duplicate_files_not_allowed(self):
        file1 = self.create_master_audio_file()
        with self.assertRaises(FileExistsError):
            # Create a file directly, without going through normal routines
            # which would prevent duplicates anyhow...
            file2 = MediaFile(
                created_by=self.user,
                item=self.item,
                sequence=2,
                file_type=MediaFileType.objects.get(file_type="MasterAudio1"),
            )
            # Use the filename of the first file for the second file
            path = Path(file1.file.name)
            new_name = file1.file.name
            with path.open(mode="rb") as f:
                file2.file = File(f, name=new_name)
                file2.save()

    def test_get_content_type(self):
        # Confirm supported file extensions are handled correctly.
        self.assertEqual(get_content_type("foo.jpg"), "image")
        self.assertEqual(get_content_type("foo.jpeg"), "image")
        self.assertEqual(get_content_type("foo.mp3"), "audio")
        self.assertEqual(get_content_type("foo.wav"), "audio")
        self.assertEqual(get_content_type("foo.pdf"), "pdf")
        self.assertEqual(get_content_type("foo.txt"), "text")
        self.assertEqual(get_content_type("foo.xml"), "text")
        # Make sure file names are converted to lowercase.
        self.assertEqual(get_content_type("FOO.XML"), "text")
        # Unsupported file extension
        with self.assertRaises(ValueError):
            get_content_type("foo.bad")
        # No file extension
        with self.assertRaises(ValueError):
            get_content_type("foo.")
        with self.assertRaises(ValueError):
            get_content_type("foo")

    def test_get_target_dir_audio(self):
        # If this test needs to run in test/prod environment,
        # paths will need changing or several environment variables
        # will need to be overridden.
        self.assertEqual(
            get_target_dir("master", "audio"), "media_dev/oh_lz/audio/masters"
        )
        self.assertEqual(
            get_target_dir("submaster", "audio"), "media_dev/oh_wowza/audio/submasters"
        )

    def test_get_target_dir_image(self):
        # If this test needs to run in test/prod environment,
        # paths will need changing or several environment variables
        # will need to be overridden.
        self.assertEqual(get_target_dir("master", "image"), "media_dev/oh_lz/masters")
        self.assertEqual(
            get_target_dir("submaster", "image"), "media_dev/oh_static/submasters"
        )
        self.assertEqual(
            get_target_dir("thumbnail", "image"), "media_dev/oh_static/nails"
        )

    def test_get_target_dir_pdf(self):
        # If this test needs to run in test/prod environment,
        # paths will need changing or several environment variables
        # will need to be overridden.
        self.assertEqual(get_target_dir("master", "pdf"), "media_dev/oh_lz/pdf/masters")
        self.assertEqual(
            get_target_dir("submaster", "pdf"), "media_dev/oh_static/pdf/submasters"
        )

    def test_get_target_dir_text(self):
        # If this test needs to run in test/prod environment,
        # paths will need changing or several environment variables
        # will need to be overridden.
        self.assertEqual(
            get_target_dir("master", "text"), "media_dev/oh_lz/text/masters"
        )
        self.assertEqual(
            get_target_dir("submaster", "text"), "media_dev/oh_static/text/submasters"
        )

    def test_get_target_dir_invalid(self):
        # Thumbnails are only for images
        with self.assertRaises(ValueError):
            get_target_dir("thumbnail", "audio")
        # Other combinations with bad parameters
        with self.assertRaises(ValueError):
            get_target_dir("master", "INVALID")
        with self.assertRaises(ValueError):
            get_target_dir("INVALID", "audio")
        with self.assertRaises(ValueError):
            get_target_dir("INVALID", "INVALID")

    def test_get_new_file_name_no_extension_parameter(self):
        new_name, next_sequence = get_new_file_name("foo.wav", self.item, "master")
        self.assertEqual(new_name, "fake-abcdef-1-master.wav")

    def test_get_new_file_name_with_extension_parameter(self):
        new_name, next_sequence = get_new_file_name(
            "foo.wav", self.item, "submaster", ".mp3"
        )
        self.assertEqual(new_name, "fake-abcdef-1-submaster.mp3")

    def tearDown(self):
        # If new files aren't deleted, Django will create next file with random-ish name.
        # Deleting the MediaFile object does *not* automatically delete the file itself.
        for mf in MediaFile.objects.all():
            mf.file.delete()


class MetadataUniquenessTestCase(TestCase):
    # Load the lookup tables needed for these tests.
    fixtures = [
        "item-status-data.json",
        "item-type-data.json",
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
            ProjectItem.objects.create(
                pk=self.item.pk,
                ark=self.item.ark,
                created_by=self.user,
                last_modified_by=self.user,
                title="Fake title",
                type_id=1,
            )

    def test_item_count(self):
        self.assertEqual(ProjectItem.objects.count(), 1)
