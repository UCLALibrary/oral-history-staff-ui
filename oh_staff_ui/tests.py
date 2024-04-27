from copy import deepcopy
from lxml import etree
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.http import HttpRequest
from django.test import SimpleTestCase, TestCase
from django.contrib.auth.models import User
from eulxml.xmlmap import load_xmlobject_from_string, mods
from oh_staff_ui.classes.GeneralFileHandler import GeneralFileHandler
from oh_staff_ui.classes.ImageFileHandler import ImageFileHandler
from oh_staff_ui.forms import ProjectItemForm
from oh_staff_ui.management.commands.import_file_metadata import (
    Command as FileMetadataCommand,
)
from oh_staff_ui.models import (
    AltId,
    AltIdType,
    AltTitle,
    AltTitleType,
    AuthoritySource,
    Copyright,
    CopyrightType,
    Date,
    DateType,
    Description,
    DescriptionType,
    ItemCopyrightUsage,
    ItemLanguageUsage,
    ItemNameUsage,
    ItemPublisherUsage,
    ItemResourceUsage,
    ItemStatus,
    ItemSubjectUsage,
    ItemType,
    Format,
    Language,
    MediaFile,
    MediaFileError,
    MediaFileType,
    Name,
    NameType,
    ProjectItem,
    Publisher,
    Resource,
    Subject,
    SubjectType,
)

from oh_staff_ui.classes.OralHistoryFile import OralHistoryFile
from oh_staff_ui.classes.AudioFileHandler import AudioFileHandler
from oh_staff_ui.classes.OralHistoryMods import OralHistoryMods
from oh_staff_ui.views_utils import (
    get_records_oai,
    get_bad_arg_error_xml,
    get_bad_verb_error_xml,
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
        # Confirm submaster has correct file type.
        self.assertEqual(
            submaster.file_type, MediaFileType.objects.get(file_code="audio_submaster")
        )

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

    def test_bad_audio_submaster_raises_error(self):
        # Confirm processing a bad master audio file raises an error.
        master = self.create_bad_master_audio_file()
        handler = AudioFileHandler(master)
        with self.assertRaises(CommandError):
            handler.process_files()

    def test_bad_audio_submaster_is_logged_to_db(self):
        # Confirm processing a bad master audio file adds a MediaFileError to db.
        master = self.create_bad_master_audio_file()
        handler = AudioFileHandler(master)
        try:
            handler.process_files()
        except CommandError:
            self.assertEquals(MediaFileError.objects.count(), 1)

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
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=self.item,
            original_file_name="FAKE",
            file="oh_lz/text/masters/fake-abcdef-1-master.xml",
        )
        self.assertEqual(mf.file_url, "")

    def test_file_url_audio_submaster(self):
        # Create minimal MediaFile object directly, with realistic file path.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="audio_submaster"),
            item=self.item,
            original_file_name="FAKE",
            file="oh_wowza/audio/submasters/fake-abcdef-1-submaster.mp3",
        )
        self.assertEqual(
            mf.file_url,
            "https://wowza.library.ucla.edu/dlp/definst/mp3:oralhistory/audio/submasters/"
            "fake-abcdef-1-submaster.mp3/playlist.m3u8",
        )

    def test_file_url_static_submaster(self):
        # Create minimal MediaFile object directly, with realistic file path.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=self.item,
            original_file_name="FAKE",
            file="oh_static/text/submasters/fake-abcdef-1-master.xml",
        )
        self.assertEqual(
            mf.file_url,
            "https://static.library.ucla.edu/oralhistory/text/submasters/fake-abcdef-1-master.xml",
        )

    def test_file_url_static_thumbnail(self):
        # Create minimal MediaFile object directly, with realistic file path.
        mf = MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="image_thumbnail"),
            item=self.item,
            original_file_name="FAKE",
            file="oh_static/nails/fake-abcdef-1-thumbnail.jpg",
        )
        self.assertEqual(
            mf.file_url,
            "https://static.library.ucla.edu/oralhistory/nails/fake-abcdef-1-thumbnail.jpg",
        )

    def test_file_size_file_exists(self):
        # Uses real file samples/sample.xml
        file = self.create_master_general_file()
        self.assertEquals(file.file_size, 902)

    def test_file_size_file_does_not_exist(self):
        # Uses non-existent file
        file_type = MediaFileType.objects.get(file_code="text_master_transcript")
        file = OralHistoryFile(
            self.item.id,
            file_name="/some/fake/file.xml",
            file_type=file_type,
            file_use="master",
            request=self.mock_request,
        )
        self.assertEquals(file.file_size, 0)

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
        "authority-source-data.json",
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
        # Level 3: Audio, child #1 of interview.
        cls.audio_item1 = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            sequence=1,
            title="Fake audio",
            type=ItemType.objects.get(type="Audio"),
            parent=cls.interview_item,
        )
        # Level 3: Audio, child #2 of interview.
        cls.audio_item2 = ProjectItem.objects.create(
            ark="fake/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            sequence=2,
            title="Fake audio",
            type=ItemType.objects.get(type="Audio"),
            parent=cls.interview_item,
        )

    def test_all_setup_items_are_created(self):
        # Series, interview, and 2 audio items created in setUpTestData().
        self.assertEqual(ProjectItem.objects.count(), 4)

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
        item = self.audio_item1
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

    def test_next_sequence_non_file_item(self):
        # Test that the form displays 1 for sequence for non-file
        # (series and interview) items.
        for item in [self.series_item, self.interview_item]:
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
            form_type_field = form.fields["sequence"]
            self.assertEquals(form_type_field.initial, 1)

    def test_next_sequence_file_item(self):
        # Test that the form displays 3 for sequence for the next
        # file-level items, given audio items 1 & 2 already exist.
        # Simulate call to /add_item/<parent_item_id>
        form = ProjectItemForm(
            data={
                "parent": self.interview_item,
            }
        )
        form_type_field = form.fields["sequence"]
        self.assertEquals(form_type_field.initial, 3)


class ModsTestCase(TestCase):
    # MODS related tests require an item of each type to confirm proper record creation,
    # each has a slightly different field structure in the MODS record

    # Load the lookup tables needed for these tests.
    fixtures = [
        "item-status-data.json",
        "item-type-data.json",
        "authority-source-data.json",
        "description-type-data.json",
        "date-type-data.json",
        "alttitle-type-data.json",
        "altid-type-data.json",
        "copyright-type-data.json",
        "name-type-data.json",
        "subject-type-data.json",
        "media-file-type-data.json",
    ]

    @classmethod
    def setUpTestData(cls):
        # Use QAD data for fake user and fake items.
        cls.user = User.objects.create_user("tester")
        language = Language.objects.create(
            value="language placeholder value", source_id=1
        )

        # Level 1: Series.
        cls.series_item = ProjectItem.objects.create(
            ark="fakeseries/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake series",
            type=ItemType.objects.get(type="Series"),
        )
        ItemLanguageUsage.objects.create(item=cls.series_item, value=language)

        # Level 2: Interview, child of series.
        cls.interview_item = ProjectItem.objects.create(
            ark="fakeinterview/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake interview",
            type=ItemType.objects.get(type="Interview"),
            parent=cls.series_item,
        )
        ItemLanguageUsage.objects.create(item=cls.interview_item, value=language)

        Description.objects.create(
            item=cls.interview_item,
            value="Abstract element",
            type=DescriptionType.objects.get(type="abstract"),
        )

        Description.objects.create(
            item=cls.interview_item,
            value="Admin note should not display",
            type=DescriptionType.objects.get(type="adminnote"),
        )

        Description.objects.create(
            item=cls.interview_item,
            value="Process interview description as qualifier",
            type=DescriptionType.objects.get(type="processinterview"),
        )

        Description.objects.create(
            item=cls.interview_item,
            value="Biographical note with invalid XML characters & \" ' ` < >",
            type=DescriptionType.objects.get(type="biographicalNote"),
        )

        Description.objects.create(
            item=cls.interview_item,
            value="Generic note should display",
            type=DescriptionType.objects.get(type="note"),
        )

        Date.objects.create(
            item=cls.interview_item,
            value="2000",
            type=DateType.objects.get(type="creation"),
        )

        AltTitle.objects.create(
            item=cls.interview_item,
            value="Alternate Title",
            type=AltTitleType.objects.get(type="descriptive"),
        )

        AltId.objects.create(
            item=cls.interview_item,
            value="Alt Id",
            type=AltIdType.objects.get(type="OPAC"),
        )

        cr = Copyright.objects.create(value="Rights statement", source_id=1)

        ItemCopyrightUsage.objects.create(
            item=cls.interview_item,
            value=cr,
            type=CopyrightType.objects.get(type="copyrightStatus"),
        )

        name = Name.objects.create(
            value="Joe Bruin", source=AuthoritySource.objects.get(source="local")
        )
        ItemNameUsage.objects.create(
            item=cls.interview_item,
            value=name,
            type=NameType.objects.get(type="interviewer"),
        )

        subject = Subject.objects.create(
            value="Sample Subject", source=AuthoritySource.objects.get(source="local")
        )
        ItemSubjectUsage.objects.create(
            item=cls.interview_item,
            value=subject,
            type=SubjectType.objects.get(type="level1"),
        )

        subject = Subject.objects.create(
            value="Arts, Literature, Music, and Film",
            source=AuthoritySource.objects.get(source="local"),
        )
        ItemSubjectUsage.objects.create(
            item=cls.interview_item,
            value=subject,
            type=SubjectType.objects.get(type="level1"),
        )
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(file_code="image_submaster"),
            item=cls.interview_item,
            original_file_name="FAKE_IMAGE",
            file="oh_static/submasters/fake-abcdef-1-master.jpg",
        )
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(file_code="pdf_master"),
            item=cls.interview_item,
            original_file_name="FAKE_PDF",
            file="oh_static/pdf/submasters/fake-abcdef-1-master.pdf",
        )
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(
                file_code="text_master_interview_history"
            ),
            item=cls.interview_item,
            original_file_name="FAKE_XML",
            file="oh_static/text/submasters/fake-abcdef-1-master.xml",
        )

        # Level 3: Audio, child of interview.
        cls.audio_item = ProjectItem.objects.create(
            ark="fakeaudio/abcdef",
            created_by=cls.user,
            last_modified_by=cls.user,
            title="Fake audio",
            type=ItemType.objects.get(type="Audio"),
            parent=cls.interview_item,
        )
        Format.objects.create(
            item=cls.audio_item, value="format placeholder value, 1 hour"
        )
        ItemLanguageUsage.objects.create(item=cls.audio_item, value=language)
        Description.objects.create(
            item=cls.audio_item,
            value="Table of Contents",
            type=DescriptionType.objects.get(type="tableOfContents"),
        )

        # The order these files are created seem to matter
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(file_code="audio_submaster"),
            item=cls.audio_item,
            original_file_name="FAKE",
            file="oh_wowza/audio/submasters/fake-abcdef-1-submaster.mp3",
        )
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(file_code="text_master_index"),
            item=cls.audio_item,
            original_file_name="FAKE_TIMED_LOG",
            file="oh_static/text/submasters/fake-abcdef-2-master.xml",
        )
        MediaFile.objects.create(
            created_by=cls.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=cls.audio_item,
            original_file_name="FAKE_TEI_TIMED_LOG",
            file="oh_static/text/submasters/fake-abcdef-2-master-tei.xml",
        )

    # Utility methods to pretty print xml
    def prettify_xml(self, xml: str) -> str:
        root = etree.fromstring(xml.serializeDocument())
        pretty_xml = etree.tostring(root, pretty_print=True, encoding="unicode")
        return pretty_xml

    # Utility methods to return MODS specific to item type
    def get_mods_from_audio_item(self):
        return self.get_mods_from_item_type(type="audio")

    def get_mods_from_interview_item(self):
        return self.get_mods_from_item_type(type="interview")

    def get_mods_from_series_item(self):
        return self.get_mods_from_item_type(type="series")

    def get_mods_from_item_type(self, type: str = "interview") -> OralHistoryMods:
        # For MODS tests, ensure test items have a status which allows
        # full MODS generation.  Other tests may have changed item status, which
        # can break other tests due to use of persistent class items.
        self.save_interview_item_with_status("Completed")
        self.save_audio_item_with_status("Completed")

        item = self.interview_item
        if type == "series":
            item = self.series_item
        if type == "audio":
            item = self.audio_item
        ohmods = OralHistoryMods(item)
        ohmods.populate_fields()
        return ohmods

    # Utility methods to save items with specifc status, for OAI feed testing
    def save_series_item_with_status(self, status: str):
        series = self.series_item
        series.status = ItemStatus.objects.get(status=status)
        series.save()

    def save_interview_item_with_status(self, status: str):
        interview = self.interview_item
        interview.status = ItemStatus.objects.get(status=status)
        interview.save()

    def save_audio_item_with_status(self, status: str):
        audio = self.audio_item
        audio.status = ItemStatus.objects.get(status=status)
        audio.save()

    # Utility methods to get specific data from OAI feed
    def get_oai_record_count(self) -> int:
        response = get_records_oai("ListRecords")
        root = etree.fromstring(response)
        # Default namespace is "http://www.openarchives.org/OAI/2.0/";
        # record elements are in that default namespace, 2 levels down.
        records = root.findall(".//record", namespaces=root.nsmap)
        return len(records)

    def get_oai_interview_related_titles(self) -> list:
        # This is buried waaaaaay down there....
        response = get_records_oai("ListRecords")
        root = etree.fromstring(response)
        nsmap = root.nsmap
        # Add mods to namespace dictionary, since it gets used later but is not
        # defined at the root level...
        nsmap["mods"] = "http://www.loc.gov/mods/v3"
        # Default namespace is "http://www.openarchives.org/OAI/2.0/";
        # record elements are in that default namespace, 2 levels down.
        # This test feed has interview as first record; get metadata element
        # from that first record.
        metadata = root.find(".//record/metadata", namespaces=nsmap)
        # Get mods container, one level inside metadata; it uses the mods namespace.
        mods = metadata.find("./mods:mods", namespaces=nsmap)
        # Get related item(s), one level inside mods
        related_items = mods.findall("./mods:relatedItem", namespaces=nsmap)
        # Finally, get the titleInfo/title text from each related item for this interview
        titles = [
            item.find("./mods:titleInfo/mods:title", namespaces=nsmap).text
            for item in related_items
        ]
        return titles

    def test_valid_abstract_parse(self):
        ohmods = self.get_mods_from_interview_item()

        ohmods_from_string = load_xmlobject_from_string(
            ohmods.serializeDocument(), mods.MODSv34
        )

        # Assert abstract generated properly
        mods_xml = ohmods_from_string.serialize(pretty=True)
        self.assertTrue(b"<mods:abstract>Abstract element</mods:abstract>" in mods_xml)

    def test_valid_description_parse(self):
        ohmods = self.get_mods_from_interview_item()

        ohmods_from_string = load_xmlobject_from_string(
            ohmods.serializeDocument(), mods.MODSv34
        )

        # Assert specific description type properly exists
        mods_xml = ohmods_from_string.serialize(pretty=True)
        self.assertTrue(
            b'<mods:note type="processinterview" displayLabel="Processing of Interview">'
            in mods_xml
        )
        self.assertTrue(
            b"<mods:note>Generic note should display</mods:note>" in mods_xml
        )

        self.assertFalse(
            b"<mods:note>Admin note should not display</mods:note>" in mods_xml
        )

    def test_valid_mods_created_date(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b"<mods:dateCreated>2000</mods:dateCreated>" in ohmods.serializeDocument()
        )

    def test_valid_mods_alttitle(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:titleInfo type="alternative">' in ohmods.serializeDocument()
        )

    def test_valid_mods_altid(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:identifier type="OPAC">Alt Id</mods:identifier>'
            in ohmods.serializeDocument()
        )

    def test_valid_mods_copyright(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b"<mods:accessCondition>Rights statement</mods:accessCondition>"
            in ohmods.serializeDocument()
        )

    def test_valid_mods_name(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:roleTerm type="text">interviewer</mods:roleTerm>'
            in ohmods.serializeDocument()
        )
        self.assertTrue(
            b"<mods:namePart>Joe Bruin</mods:namePart>" in ohmods.serializeDocument()
        )

    def test_valid_mods_subject(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:subject authority="local">' in ohmods.serializeDocument()
        )
        self.assertTrue(
            b"<mods:topic>Sample Subject</mods:topic>" in ohmods.serializeDocument()
        )
        # Confirm one of the excluded subjects is not in the record
        self.assertTrue(
            b"<mods:topic>Arts, Literature, Music, and Film</mods:topic>"
            not in ohmods.serializeDocument()
        )

    def test_valid_related_audio_item(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:relatedItem xlink:href="https://wowza.library.ucla.edu/'
            b"dlp/definst/mp3:oralhistory/audio/submasters/fake-abcdef-1-submaster.mp3/"
            b'playlist.m3u8" type="constituent">' in ohmods.serializeDocument()
        )

    def test_valid_timing_log(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(b"<mods:tableOfContents>" in ohmods.serializeDocument())

    def test_valid_mods_image(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:location displayLabel="Image of Interviewee">'
            in ohmods.serializeDocument()
        )

    def test_valid_mods_ihist_on_interview_item(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:location displayLabel="Interview History">'
            in ohmods.serializeDocument()
        )

    def test_valid_mods_pdf_on_interview_item(self):
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:location displayLabel="Interview Full Transcript (PDF)">'
            in ohmods.serializeDocument()
        )

    def test_series_relateditem_on_items(self):
        # A relatedItem of type series should only be present in items of interview type
        ohmods = self.get_mods_from_interview_item()
        self.assertTrue(
            b'<mods:relatedItem type="series">' in ohmods.serializeDocument()
        )
        ohmods = self.get_mods_from_series_item()
        self.assertTrue(
            b'<mods:relatedItem type="series">' not in ohmods.serializeDocument()
        )
        ohmods = self.get_mods_from_audio_item()
        self.assertTrue(
            b'<mods:relatedItem type="series">' not in ohmods.serializeDocument()
        )

    def test_timed_log_attribute_is_added(self):
        # If an item contains a TEI/XML transcript, it should have a usage attribute with value "timed_log"
        if MediaFile(
            item=self.audio_item,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
        ):
            ohmods = self.get_mods_from_audio_item()
            self.assertTrue(
                b'<mods:url usage="timed log">' in ohmods.serializeDocument()
            )

    def test_absence_of_timed_log_with_text_master_index(self):
        # If an item does not contain a file_code of text_master_transcript, mods:url[@usage="timed log"] should not be present

        # Delete MediaFile associated with "text_master_transcript" file_code
        media_file = MediaFile.objects.get(
            item__id=self.audio_item.id, file_type__file_code="text_master_transcript"
        )
        media_file.delete()

        ohmods = self.get_mods_from_audio_item()

        # At this point we should only have "text_master_index" file_code MediaFile
        if MediaFile.objects.get(
            item__id=self.audio_item.id, file_type__file_code="text_master_index"
        ):
            self.assertFalse(
                b'<mods:url usage="timed log">' in ohmods.serializeDocument()
            )

        # Add "text_master_transcript" back in case future tests rely on it
        MediaFile.objects.create(
            created_by=self.user,
            file_type=MediaFileType.objects.get(file_code="text_master_transcript"),
            item=self.audio_item,
            original_file_name="FAKE_TEI_TIMED_LOG",
            file="oh_static/text/submasters/fake-abcdef-2-master-tei.xml",
        )

    def test_writing_single_mods(self):
        ohmods = self.get_mods_from_interview_item()
        ohmods.write_mods_record()

        ark_ns = self.interview_item.ark.replace("/", "-")
        # Verify file exists
        p = Path(f"{settings.MEDIA_ROOT}/{settings.OH_STATIC}/mods/{ark_ns}-mods.xml")
        self.assertTrue(p.is_file())

    def test_bad_getrecord_request(self):
        bad_response = get_bad_arg_error_xml("GetRecordWithoutIdentifier")
        self.assertTrue(b'<error code="badArgument"/>' in bad_response)

    def test_bad_verb_request(self):
        bad_response = get_bad_verb_error_xml("BadVerb")
        self.assertTrue(b'<error code="badVerb"/>' in bad_response)

    def test_getrecord_request(self):
        id_to_check = self.series_item.ark
        response = get_records_oai(verb="GetRecord", ark=id_to_check)
        id_tag = f'identifier="{id_to_check}"'

        self.assertTrue(bytes(id_tag, "utf-8") in response)

    def test_listrecords_request(self):
        response = get_records_oai("ListRecords")
        self.assertTrue(
            b'<request metadataPrefix="mods" verb="ListRecords">' in response
        )

    def test_completed_interviews_are_included(self):
        # Confirm the OAI feed includes Completed interview item.
        # This is the only item, so feed contains 1 record.
        self.save_interview_item_with_status("Completed")
        record_count = self.get_oai_record_count()
        self.assertEqual(record_count, 1)

    def test_sealed_interviews_are_excluded(self):
        # Confirm the OAI feed does not include Sealed interview item.
        self.save_interview_item_with_status("Sealed")
        record_count = self.get_oai_record_count()
        self.assertEqual(record_count, 0)

    def test_series_records_are_excluded(self):
        # Confirm the OAI feed does not include series as primary records.
        self.save_series_item_with_status("Completed")
        self.save_interview_item_with_status("Completed")
        record_count = self.get_oai_record_count()
        self.assertEqual(record_count, 1)

    def test_series_as_related_title(self):
        # Confirm the OAI feed includes series as related titles to interviews.
        self.save_series_item_with_status("Completed")
        self.save_interview_item_with_status("Completed")

        related_titles = self.get_oai_interview_related_titles()
        self.assertIn("Fake series", related_titles)

    def test_completed_audio_items_are_included(self):
        # Confirm the OAI feed includes both interview and audio item
        # (by design, feed includes records for both, though they are parent/child).
        self.save_interview_item_with_status("Completed")
        self.save_audio_item_with_status("Completed")
        record_count = self.get_oai_record_count()
        self.assertEqual(record_count, 2)

    def test_sealed_audio_items_are_excluded(self):
        # Confirm the OAI feed has only 1 item, the Completed interview.
        self.save_interview_item_with_status("Completed")
        self.save_audio_item_with_status("Sealed")
        record_count = self.get_oai_record_count()
        self.assertEqual(record_count, 1)

    def test_sealed_audio_metadata_is_excluded(self):
        # Confirm that Completed interview items in the OAI feed
        # do not include metadata for Sealed audio items related to them.
        self.save_interview_item_with_status("Completed")
        self.save_audio_item_with_status("Sealed")
        related_titles = self.get_oai_interview_related_titles()
        # Interview items can have any number of related items (audio and series);
        # in our test data, the Sealed audio item has title "Fake audio".
        # That title should not be present, since that item has been Sealed.
        self.assertNotIn("Fake audio", related_titles)


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
