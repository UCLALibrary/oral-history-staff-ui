from django.test import override_settings, SimpleTestCase

from .models import ProjectItem, ItemStatus, ItemType
from .views_utils import get_public_site_url


@override_settings(OH_PUBLIC_SITE="https://oralhistory.library.ucla.edu")
class TestGetPublicSiteUrl(SimpleTestCase):
    def test_series_link(self):
        """For series, link should be to a faceted search for the series title."""

        for status in ("Completed", "Completed with minimal metadata"):
            with self.subTest(status=status):
                item = ProjectItem(
                    title="Test Series",
                    type=ItemType(type="Series"),
                    status=ItemStatus(status=status),
                    ark="123/1",
                )
                self.assertEqual(
                    get_public_site_url(item),
                    "https://oralhistory.library.ucla.edu/?f[series_facet][]=Test Series",
                )

    def test_interview_link(self):
        """For interviews, link should be to the item's catalog page."""

        for status in ("Completed", "Completed with minimal metadata"):
            with self.subTest(status=status):
                item = ProjectItem(
                    title="Test Item",
                    type=ItemType(type="Interview"),
                    status=ItemStatus(status=status),
                    ark="123/2",
                )
                self.assertEqual(
                    get_public_site_url(item),
                    "https://oralhistory.library.ucla.edu/catalog/123-2",
                )

    def test_other_types(self):
        """For other item types, no link should be generated."""

        for type in ("Audio", "Video"):
            for status in ("Completed", "Completed with minimal metadata"):
                with self.subTest(type=type, status=status):
                    item = ProjectItem(
                        title="Test Item",
                        type=ItemType(type=type),
                        status=ItemStatus(status=status),
                        ark="123/4",
                    )
                    self.assertIsNone(get_public_site_url(item))
                    self.assertEqual(get_public_site_url(item), None)

    def test_other_statuses(self):
        """For other statuses, no link should be generated regardless of type."""

        for status in (
            "In progress",
            "Pending",
            "Derived",
            "Imported",
            "Needs QA",
            "Needs Review",
            "Sealed",
            "Migrated",
            "Record proofed; needs metadata review",
            "Needs expert metadata review",
        ):
            for type in ("Series", "Interview", "Audio", "Video"):
                with self.subTest(type=type, status=status):
                    item = ProjectItem(
                        title="Test Item",
                        type=ItemType(type=type),
                        status=ItemStatus(status=status),
                        ark="123/5",
                    )
                    self.assertIsNone(get_public_site_url(item))

    @override_settings(OH_PUBLIC_SITE=None)
    def test_no_host_setting(self):
        """If the OH_PUBLIC_SITE setting is not set, return None."""

        item = ProjectItem(
            title="Test Item",
            type=ItemType(type="Interview"),
            status=ItemStatus(status="Completed"),
            ark="123/6",
        )
        self.assertIsNone(get_public_site_url(item))
