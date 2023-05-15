import logging
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.http import HttpRequest
from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User
from oh_staff_ui.classes.GeneralFileHandler import GeneralFileHandler
from oh_staff_ui.classes.ImageFileHandler import ImageFileHandler
from oh_staff_ui.forms import ProjectItemForm
from oh_staff_ui.management.commands.import_file_metadata import (
    Command as FileMetadataCommand,
)
from oh_staff_ui.models import (
    Copyright,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemPublisherUsage,
    ItemResourceUsage,
    ItemSubjectUsage,
    ItemType,
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
from oh_staff_ui.classes.AudioFileHandler import AudioFileHandler
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods


logger = logging.getLogger(__name__)


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
            type=ItemType.objects.get(type="Series"),
        )
        # Get mock request with generic user info for command-line processing.
        cls.mock_request = HttpRequest()
        cls.mock_request.user = User.objects.get(username=cls.user.username)

    def get_full_path(self, relative_path: str) -> Path:
        # MediaFile.file.name contains a path relative to MEDIA_ROOT;
        # return the full absolute path.
        return Path(settings.MEDIA_ROOT, relative_path)

    def create_master_audio_file(self):
        # Utility function used in multiple tests.
        file_type = MediaFileType.objects.get(file_code="audio_master")
        master = OralHistoryFile(
            self.item.id,
            file_name="samples/sample.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        return master

    def create_bad_master_audio_file(self):
        # Purposely add a file which will fail mp3 conversion
        file_type = MediaFileType.objects.get(file_code="audio_master")
        master = OralHistoryFile(
            self.item.id,
            file_name="samples/fake_file_01.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        return master

    def create_master_image_file(self):
        # Utility function used in multiple tests.
        # Uses a tiff large enough to be resized.
        file_type = MediaFileType.objects.get(file_code="image_master")
        master = OralHistoryFile(
            self.item.id,
            file_name="samples/sample_marbles.tif",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        return master

    def create_master_general_file(self):
        # Utility function used in multiple tests.
        # Same logic applies to text/xml/pdf, no need for all to be tested.
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        master = OralHistoryFile(
            self.item.id,
            file_name="samples/sample.xml",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        return master

    def test_master_audio_file_is_added(self):
        master = self.create_master_audio_file()
        handler = AudioFileHandler(master)
        handler.process_files()
        # Confirm the new file exists.
        new_path = self.get_full_path(master.media_file.file.name)
        self.assertEqual(new_path.exists(), True)
        # For masters, new file should be same size as original.
        path = Path("samples/sample.wav")
        self.assertEqual(master.media_file.file.size, path.stat().st_size)
        # Confirm the file size was also captured, in case file is no longer accessible.
        self.assertEqual(master.media_file.file_size, path.stat().st_size)

    def test_submaster_audio_file_is_added(self):
        master = self.create_master_audio_file()
        handler = AudioFileHandler(master)
        handler.process_files()
        # master is OralHistoryFile; submaster is MediaFile
        submaster = MediaFile.objects.get(parent=master.media_file)
        self.assertEqual(
            submaster.file.name,
            "oh_wowza/audio/submasters/fake-abcdef-1-submaster.mp3",
        )
        # Confirm the new file itself exists.
        new_path = self.get_full_path(submaster.file.name)
        self.assertEqual(new_path.exists(), True)
        # Confirm we have 2 items, the master and submaster.
        self.assertEqual(MediaFile.objects.count(), 2)
        # Confirm master is parent of submaster.
        self.assertEqual(master.media_file, submaster.parent)

    def test_duplicate_files_not_allowed(self):
        file1 = self.create_master_audio_file()
        handler = AudioFileHandler(file1)
        handler.process_files()
        with self.assertRaises(FileExistsError):
            # Create a file directly, without going through normal routines
            # which would prevent duplicates anyhow...
            file2 = MediaFile(
                created_by=self.user,
                item=self.item,
                sequence=2,
                file_type=MediaFileType.objects.get(file_code="audio_master"),
            )
            # Use the filename of the first file for the second file
            path = self.get_full_path(file1.media_file.file.name)
            new_name = file1.media_file.file.name
            with path.open(mode="rb") as f:
                file2.file = File(f, name=new_name)
                file2.save()

    def test_multiple_audio_masters_not_allowed(self):
        # Different from test_duplicate_files_not_allowed();
        # specifically, multiple audio masters (from any audio files)
        # on one item are not allowed.
        file1 = self.create_master_audio_file()
        handler = AudioFileHandler(file1)
        handler.process_files()
        file2 = self.create_master_audio_file()
        with self.assertRaises(CommandError):
            handler = AudioFileHandler(file2)
            handler.process_files()

    def test_bad_audio_submaster_is_bound(self):
        file1 = self.create_bad_master_audio_file()
        handler = AudioFileHandler(file1)
        with self.assertRaises(CommandError):
            handler.process_files()

    def test_master_image_file_is_added(self):
        master = self.create_master_image_file()
        handler = ImageFileHandler(master)
        handler.process_files()
        # Confirm the new file exists.
        new_path = self.get_full_path(master.media_file.file.name)
        self.assertEqual(new_path.exists(), True)
        # For masters, new file should be same size as original.
        path = Path("samples/sample_marbles.tif")
        self.assertEqual(master.media_file.file.size, path.stat().st_size)
        # Confirm the file size was also captured, in case file is no longer accessible.
        self.assertEqual(master.media_file.file_size, path.stat().st_size)

    def test_submaster_image_file_is_added(self):
        master = self.create_master_image_file()
        handler = ImageFileHandler(master)
        handler.process_files()
        file_type = MediaFileType.objects.get(file_code="image_submaster")
        # master is OralHistoryFile; submaster is MediaFile
        submaster = MediaFile.objects.get(parent=master.media_file, file_type=file_type)
        self.assertEqual(
            submaster.file.name,
            "oh_static/submasters/fake-abcdef-1-submaster.jpg",
        )
        # Confirm the new file itself exists.
        new_path = self.get_full_path(submaster.file.name)
        self.assertEqual(new_path.exists(), True)
        # Confirm master is parent of submaster.
        self.assertEqual(master.media_file, submaster.parent)

    def test_thumbnail_image_file_is_added(self):
        master = self.create_master_image_file()
        handler = ImageFileHandler(master)
        handler.process_files()
        file_type = MediaFileType.objects.get(file_code="image_thumbnail")
        # master is OralHistoryFile; submaster is MediaFile
        submaster = MediaFile.objects.get(parent=master.media_file, file_type=file_type)
        self.assertEqual(
            submaster.file.name,
            "oh_static/nails/fake-abcdef-1-thumbnail.jpg",
        )
        # Confirm the new file itself exists.
        new_path = self.get_full_path(submaster.file.name)
        self.assertEqual(new_path.exists(), True)
        # Confirm master is parent of submaster.
        self.assertEqual(master.media_file, submaster.parent)

    def test_master_general_file_is_added(self):
        master = self.create_master_general_file()
        handler = GeneralFileHandler(master)
        handler.process_files()
        # Confirm the new file exists.
        new_path = self.get_full_path(master.media_file.file.name)
        self.assertEqual(new_path.exists(), True)
        # For masters, new file should be same size as original.
        path = Path("samples/sample.xml")
        self.assertEqual(master.media_file.file.size, path.stat().st_size)
        # Confirm the file size was also captured, in case file is no longer accessible.
        self.assertEqual(master.media_file.file_size, path.stat().st_size)

    def test_submaster_general_file_is_added(self):
        master = self.create_master_general_file()
        handler = GeneralFileHandler(master)
        handler.process_files()
        # master is OralHistoryFile; submaster is MediaFile
        submaster = MediaFile.objects.get(parent=master.media_file)
        self.assertEqual(
            submaster.file.name,
            "oh_static/text/submasters/fake-abcdef-1-submaster.xml",
        )
        # Confirm the new file itself exists.
        new_path = self.get_full_path(submaster.file.name)
        self.assertEqual(new_path.exists(), True)
        # Confirm we have 2 items, the master and submaster.
        self.assertEqual(MediaFile.objects.count(), 2)
        # Confirm master is parent of submaster.
        self.assertEqual(master.media_file, submaster.parent)

    def test_content_type_jpeg(self):
        file_type = MediaFileType.objects.get(file_code="image_submaster")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpeg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_jpg(self):
        file_type = MediaFileType.objects.get(file_code="image_submaster")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_tif(self):
        file_type = MediaFileType.objects.get(file_code="image_master")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tif",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_tiff(self):
        file_type = MediaFileType.objects.get(file_code="image_master")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tiff",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "image")

    def test_content_type_mp3(self):
        file_type = MediaFileType.objects.get(file_code="audio_submaster")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.mp3",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "audio")

    def test_content_type_pdf(self):
        file_type = MediaFileType.objects.get(file_code="pdf_master_legal_agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "pdf")

    def test_content_type_txt(self):
        file_type = MediaFileType.objects.get(file_code="text_master_introduction")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.txt",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "text")

    def test_content_type_wav(self):
        file_type = MediaFileType.objects.get(file_code="audio_master")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "audio")

    def test_content_type_xml(self):
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
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
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="FOO.XML",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.content_type, "text")

    def test_content_type_unsupported_extension(self):
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo.invalid",
                file_type=file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_no_extension(self):
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="foo",
                file_type=file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_mismatch_audio(self):
        wrong_file_type = MediaFileType.objects.get(file_code="pdf_master")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="samples/sample.wav",
                file_type=wrong_file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_mismatch_image(self):
        wrong_file_type = MediaFileType.objects.get(file_code="pdf_master")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="samples/sample.tiff",
                file_type=wrong_file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_mismatch_pdf(self):
        wrong_file_type = MediaFileType.objects.get(file_code="audio_master")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="samples/sample.pdf",
                file_type=wrong_file_type,
                file_use="master",
                request=self.mock_request,
            )

    def test_content_type_mismatch_text(self):
        wrong_file_type = MediaFileType.objects.get(file_code="pdf_master")
        with self.assertRaises(ValueError):
            OralHistoryFile(
                self.item.id,
                file_name="samples/sample.xml",
                file_type=wrong_file_type,
                file_use="master",
                request=self.mock_request,
            )

    # If the target_dir tests need to run in the test/prod environment,
    # paths will need changing or several environment variables
    # will need to be overridden.

    def test_get_target_dir_master_audio(self):
        file_type = MediaFileType.objects.get(file_code="audio_master")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.wav",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_lz/audio/masters")

    def test_get_target_dir_submaster_audio(self):
        file_type = MediaFileType.objects.get(file_code="audio_submaster")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.mp3",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_wowza/audio/submasters")

    def test_get_target_dir_master_image(self):
        file_type = MediaFileType.objects.get(file_code="image_master")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.tiff",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_lz/masters")

    def test_get_target_dir_submaster_image(self):
        file_type = MediaFileType.objects.get(file_code="image_submaster")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_static/submasters")

    def test_get_target_dir_thumbnail_image(self):
        file_type = MediaFileType.objects.get(file_code="image_thumbnail")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.jpg",
            file_type=file_type,
            file_use="thumbnail",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_static/nails")

    def test_get_target_dir_master_pdf(self):
        file_type = MediaFileType.objects.get(file_code="pdf_master_legal_agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_lz/pdf/masters")

    def test_get_target_dir_submaster_pdf(self):
        file_type = MediaFileType.objects.get(file_code="pdf_master_legal_agreement")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.pdf",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_static/pdf/submasters")

    def test_get_target_dir_master_text(self):
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.xml",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_lz/text/masters")

    def test_get_target_dir_submaster_text(self):
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        ohf = OralHistoryFile(
            self.item.id,
            file_name="foo.xml",
            file_type=file_type,
            file_use="submaster",
            request=self.mock_request,
        )
        self.assertEqual(ohf.target_dir, "oh_static/text/submasters")

    def test_get_target_dir_invalid_audio_thumbnail(self):
        # Audio doesn't have thumbnails
        file_type = MediaFileType.objects.get(file_code="audio_master")
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
        file_type = MediaFileType.objects.get(file_code="audio_master")
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
        file_type = MediaFileType.objects.get(file_code="audio_master")
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
        handler = AudioFileHandler(master)
        handler.process_files()
        self.assertEqual(
            master.media_file.file.name,
            "oh_lz/audio/masters/fake-abcdef-1-master.wav",
        )

    def test_file_url_master_is_empty(self):
        # Create minimal MediaFile object directly, with realistic file path.
        # Use valid placeholder name, then update to realistic path, to
        # work around SuspiciousFileOperation.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=self.item,
            original_file_name="FAKE",
            file="placeholder",
        )
        # Work around SuspiciousFileOperation
        mf.file.name = "/media/oh_lz/text/masters/fake-abcdef-1-master.xml"
        self.assertEqual(mf.file_url, "")

    def test_file_url_audio_submaster(self):
        # Create minimal MediaFile object directly, with realistic file path.
        # Use valid placeholder name, then update to realistic path, to
        # work around SuspiciousFileOperation.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="audio_submaster"),
            item=self.item,
            original_file_name="FAKE",
            file="placeholder",
        )
        mf.file.name = "/media/oh_wowza/audio/submasters/fake-abcdef-1-submaster.mp3"
        self.assertEqual(
            mf.file_url,
            "https://wowza.library.ucla.edu/dlp/definst/mp3:oralhistory/audio/submasters/"
            "fake-abcdef-1-submaster.mp3/playlist.m3u8",
        )

    def test_file_url_static_submaster(self):
        # Create minimal MediaFile object directly, with realistic file path.
        # Use valid placeholder name, then update to realistic path, to
        # work around SuspiciousFileOperation.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=self.item,
            original_file_name="FAKE",
            file="placeholder",
        )
        mf.file.name = "/media/oh_static/text/submasters/fake-abcdef-1-master.xml"
        self.assertEqual(
            mf.file_url,
            "https://static.library.ucla.edu/oralhistory/text/submasters/fake-abcdef-1-master.xml",
        )

    def test_file_url_static_thumbnail(self):
        # Create minimal MediaFile object directly, with realistic file path.
        # Use valid placeholder name, then update to realistic path, to
        # work around SuspiciousFileOperation.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="image_thumbnail"),
            item=self.item,
            original_file_name="FAKE",
            file="placeholder",
        )
        mf.file.name = "/media/oh_static/nails/fake-abcdef-1-thumbnail.jpg"
        self.assertEqual(
            mf.file_url,
            "https://static.library.ucla.edu/oralhistory/nails/fake-abcdef-1-thumbnail.jpg",
        )

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
            type=ItemType.objects.get(type="Series"),
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
                type=ItemType.objects.get(type="Series"),
            )

    def test_item_count(self):
        self.assertEqual(ProjectItem.objects.count(), 1)


class ProjectItemFormTestCase(TestCase):
    # ProjectItemForm has some custom code for determining item type
    # based on item position in hierarchy (series, interview, a/v file).

    # Load the lookup tables needed for these tests.
    fixtures = [
        "item-status-data.json",
        "item-type-data.json",
    ]

    @classmethod
    def setUpTestData(cls):
        # Use QAD data for fake user and fake items.
        cls.user = User.objects.create_user("tester")
        # Level 1: Series.
        cls.series_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake series",
            type=ItemType.objects.get(type="Series"),
        )
        # Level 2: Interview, child of series.
        cls.interview_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake interview",
            type=ItemType.objects.get(type="Interview"),
            parent=cls.series_item,
        )
        # Level 3: Audio, child of interview.
        cls.audio_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake audio",
            type=ItemType.objects.get(type="Audio"),
            parent=cls.interview_item,
        )

    def test_default_form_item_type_is_series(self):
        # Test that the form is correct for /add_item with no parent.
        form = ProjectItemForm()
        form_type_field = form.fields["type"]
        selected_type = ItemType.objects.get(type="Series")
        # Check the form field's initial value.
        self.assertEqual(form_type_field.initial, selected_type)
        # Check the HTML also has that value selected, just to be sure
        self.assertInHTML('<option value="2" selected>Series</option>', str(form))

    def test_series_form_item_type_is_series(self):
        # Test that the form handles display of choices for series items.
        item = self.series_item
        form = ProjectItemForm(
            data={
                "parent": item.parent,
                "title": item.title,
                "type": item.type,
                "sequence": item.sequence,
                "coverage": item.coverage,
                "relation": item.relation,
                "status": item.status,
            }
        )
        form_type_field = form.fields["type"]
        selected_type = ItemType.objects.get(type="Series")
        # Check the form field's initial value.
        self.assertEqual(form_type_field.initial, selected_type)
        # Check the HTML also has that value selected, just to be sure
        self.assertInHTML('<option value="2" selected>Series</option>', str(form))

    def test_interview_form_item_type_is_interview(self):
        # Test that the form handles display of choices for interview items.
        item = self.interview_item
        form = ProjectItemForm(
            data={
                "parent": item.parent,
                "title": item.title,
                "type": item.type,
                "sequence": item.sequence,
                "coverage": item.coverage,
                "relation": item.relation,
                "status": item.status,
            }
        )
        form_type_field = form.fields["type"]
        selected_type = ItemType.objects.get(type="Interview")
        # Check the form field's initial value.
        self.assertEqual(form_type_field.initial, selected_type)
        # Check the HTML also has that value selected, just to be sure
        self.assertInHTML('<option value="3" selected>Interview</option>', str(form))

    def test_audio_form_item_type_is_audio(self):
        # Test that the form handles display of choices for audio items.
        item = self.audio_item
        form = ProjectItemForm(
            data={
                "parent": item.parent,
                "title": item.title,
                "type": item.type,
                "sequence": item.sequence,
                "coverage": item.coverage,
                "relation": item.relation,
                "status": item.status,
            }
        )
        form_type_field = form.fields["type"]
        selected_type = ItemType.objects.get(type="Audio")
        # Check the form field's initial value.
        self.assertEqual(form_type_field.initial, selected_type)
        # Check the HTML also has that value selected, just to be sure
        self.assertInHTML('<option value="4" selected>Audio</option>', str(form))

    def test_post_to_item_form(self):
        # Test that the form handles posted data correctly.
        item = self.interview_item
        request = HttpRequest()
        # Send data unchanged, except for arbitrary title change.
        request.POST = {
            "ark": item.ark,
            "parent": item.parent,
            "sequence": item.sequence,
            "status": item.status,
            "title": "Fake new title",
            "type": item.type,
        }
        form = ProjectItemForm(request.POST, parent_item=self.series_item)
        # Check that form validation succeeded.
        self.assertEquals({}, form.errors)


class ModsTestCase(TestCase):
    # MODS related tests require an item of each type to confirm proper record creation,
    # each has a slightly different field structure in the MODS record

    # Load the lookup tables needed for these tests.
    fixtures = [
        "item-status-data.json",
        "item-type-data.json",
    ]

    @classmethod
    def setUpTestData(cls):
        # Use QAD data for fake user and fake items.
        cls.user = User.objects.create_user("tester")
        # Level 1: Series.
        cls.series_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake series",
            type=ItemType.objects.get(type="Series"),
        )
        # Level 2: Interview, child of series.
        cls.interview_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake interview",
            type=ItemType.objects.get(type="Interview"),
            parent=cls.series_item,
        )
        # Level 3: Audio, child of interview.
        cls.audio_item = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake audio",
            type=ItemType.objects.get(type="Audio"),
            parent=cls.interview_item,
        )

    def test_valid_series_item_mods(self):
        item = self.series_item
        ohmods = OralHistoryMods(item)
        ohmods.populate_fields()

        self.assertEqual(ohmods.is_valid(), True)

    def test_valid_interview_item_mods(self):
        item = self.interview_item
        ohmods = OralHistoryMods(item)
        ohmods.populate_fields()

        self.assertEqual(ohmods.is_valid(), True)

    def test_valid_audio_item_mods(self):
        item = self.audio_item
        ohmods = OralHistoryMods(item)
        ohmods.populate_fields()

        self.assertEqual(ohmods.is_valid(), True)


class FileMetadataMigrationTestCase(SimpleTestCase):
    # Test logic not already covered by OralHistoryFile tests.

    def test_get_full_file_name_audio_submaster_newer_file_in_original_name(self):
        # Newer file, subdirectory in file name, should go into audio/submasters
        full_file_name = FileMetadataCommand().get_full_file_name(
            "oh_wowza/audio/submasters",
            "audio/submasters/21198-zz002kpt8t-1-submaster.mp3",
            "https://testing/audio/submasters/21198-zz002kpt8t-1-submaster.mp3/playlist.m3u8",
        )
        self.assertEqual(
            full_file_name,
            "oh_wowza/audio/submasters/21198-zz002kpt8t-1-submaster.mp3",
        )

    def test_get_full_file_name_audio_submaster_newer_file_not_in_original_name(self):
        # Newer file, no subdirectory in file name, should also go into audio/submasters
        full_file_name = FileMetadataCommand().get_full_file_name(
            "oh_wowza/audio/submasters",
            "21198-zz002kpzdt-2-submaster.mp3",
            "https://testing/oralhistory/audio/submasters/21198-zz002kpzdt-2-submaster.mp3/"
            "playlist.m3u8",
        )
        self.assertEqual(
            full_file_name,
            "oh_wowza/audio/submasters/21198-zz002kpzdt-2-submaster.mp3",
        )

    def test_get_full_file_name_audio_submaster_older_file(self):
        # Older file, should not go into audio/submasters
        full_file_name = FileMetadataCommand().get_full_file_name(
            "oh_wowza/audio/submasters",
            "21198-zz00094qtd-3-submaster.mp3",
            "https://testing/oralhistory/21198-zz00094qtd-3-submaster.mp3/playlist.m3u8",
        )
        self.assertEqual(full_file_name, "oh_wowza/21198-zz00094qtd-3-submaster.mp3")
