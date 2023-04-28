from pathlib import Path
import unittest
from django.core.files import File
from django.db import IntegrityError
from django.http import HttpRequest
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

from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile


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
        # Get mock request with generic user info for command-line processing.
        cls.mock_request = HttpRequest()
        cls.mock_request.user = User.objects.get(username=cls.user.username)

    def create_master_audio_file(self):
        # Utility function used in multiple tests.
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        master = OralHistoryFile(
            self.item.id,
            file_name="samples/sample.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        master.process_media_file()
        return master

    def test_master_audio_file_is_added(self):
        master = self.create_master_audio_file()
        # Confirm the new file exists.
        self.assertEqual(Path(master.media_file.file.name).exists(), True)
        # For masters, new file should be same size as original.
        path = Path("samples/sample.wav")
        self.assertEqual(master.media_file.file.size, path.stat().st_size)

    @unittest.skip("Submaster handling WIP")
    def test_submaster_audio_file_is_added(self):
        master = self.create_master_audio_file()
        file_type = MediaFileType.objects.get(file_type="SubMasterAudio1")
        submaster = OralHistoryFile(
            self.item.id,
            file_name="samples/sample.wav",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        submaster.process_media_file()
        self.assertEqual(
            submaster.media_file.file.name,
            "media_dev/oh_wowza/audio/submasters/fake-abcdef-2-submaster.mp3",
        )
        # Confirm the new file itself exists.
        self.assertEqual(Path(submaster.media_file.file.name).exists(), True)
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
            path = Path(file1.media_file.file.name)
            new_name = file1.media_file.file.name
            with path.open(mode="rb") as f:
                file2.file = File(f, name=new_name)
                file2.save()

    def test_content_type_jpeg(self):
        file_type = MediaFileType.objects.get(file_type="SubMasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpeg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_jpg(self):
        file_type = MediaFileType.objects.get(file_type="SubMasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_tif(self):
        file_type = MediaFileType.objects.get(file_type="MasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tif",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_tiff(self):
        file_type = MediaFileType.objects.get(file_type="MasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tiff",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_mp3(self):
        file_type = MediaFileType.objects.get(file_type="SubMasterAudio1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.mp3",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "audio")

    def test_content_type_pdf(self):
        file_type = MediaFileType.objects.get(file_type="PDF Legal Agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "pdf")

    def test_content_type_txt(self):
        file_type = MediaFileType.objects.get(file_type="Text Introduction")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.txt",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "text")

    def test_content_type_wav(self):
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "audio")

    def test_content_type_xml(self):
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.xml",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "text")

    def test_content_type_extension_case(self):
        # Make sure file names are converted to lowercase.
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="FOO.XML",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "text")

    def test_content_type_unsupported_extension(self):
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo.invalid",
                file_type=file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_no_extension(self):
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo",
                file_type=file_type,
                file_use="master",
                request=self.mock_request,
            )

    # If the target_dir tests need to run in the test/prod environment,
    # paths will need changing or several environment variables
    # will need to be overridden.

    def test_get_target_dir_master_audio(self):
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_lz/audio/masters")

    def test_get_target_dir_submaster_audio(self):
        file_type = MediaFileType.objects.get(file_type="SubMasterAudio1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.mp3",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_wowza/audio/submasters")

    def test_get_target_dir_master_image(self):
        file_type = MediaFileType.objects.get(file_type="MasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tiff",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_lz/masters")

    def test_get_target_dir_submaster_image(self):
        file_type = MediaFileType.objects.get(file_type="SubMasterImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_static/submasters")

    def test_get_target_dir_thumbnail_image(self):
        file_type = MediaFileType.objects.get(file_type="ThumbnailImage1")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="thumbnail",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_static/nails")

    def test_get_target_dir_master_pdf(self):
        file_type = MediaFileType.objects.get(file_type="PDF Legal Agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_lz/pdf/masters")

    def test_get_target_dir_submaster_pdf(self):
        file_type = MediaFileType.objects.get(file_type="PDF Legal Agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_static/pdf/submasters")

    def test_get_target_dir_master_text(self):
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.xml",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_lz/text/masters")

    def test_get_target_dir_submaster_text(self):
        file_type = MediaFileType.objects.get(file_type="Text Transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.xml",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "media_dev/oh_static/text/submasters")

    def test_get_target_dir_invalid_audio_thumbnail(self):
        # Audio doesn't have thumbnails
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo.wav",
                file_type=file_type,
                file_use="thumbnail",
                request=self.mock_request,
            )

    def test_get_target_dir_invalid_audio_file_use(self):
        # Audio doesn't have thumbnails
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo.wav",
                file_type=file_type,
                file_use="INVALID",
                request=self.mock_request,
            )

    def test_get_target_dir_invalid_master_content_type(self):
        # Audio doesn't have thumbnails
        file_type = MediaFileType.objects.get(file_type="MasterAudio1")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo.INVALID",
                file_type=file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_get_new_file_name_default_extension_parameter(self):
        master = self.create_master_audio_file()
        self.assertEqual(
            master.media_file.file.name,
            "media_dev/oh_lz/audio/masters/fake-abcdef-1-master.wav",
        )

    @unittest.skip("Submaster handling WIP")
    def test_get_new_file_name_with_explicit_extension_parameter(self):
        pass
        # new_name, next_sequence = get_new_file_name(
        #     "foo.wav", self.item, "submaster", ".mp3"
        # )
        # self.assertEqual(new_name, "fake-abcdef-1-submaster.mp3")

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
