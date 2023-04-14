from pathlib import Path
from django.core.files import File
from django.test import TestCase
from django.contrib.auth.models import User
from oh_staff_ui.models import MediaFile, MediaFileType, ProjectItem


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
