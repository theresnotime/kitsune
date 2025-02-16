import re
from unittest.mock import Mock

from django.conf import settings
from pyquery import PyQuery as pq

from kitsune.groups.models import GroupProfile
from kitsune.groups.templatetags.jinja_helpers import group_avatar, group_link
from kitsune.groups.tests import GroupProfileFactory
from kitsune.sumo.tests import TestCase
from kitsune.sumo.urlresolvers import reverse
from kitsune.users.tests import GroupFactory


class GroupHelperTests(TestCase):
    def test_group_link_no_profile(self):
        g = GroupFactory()
        text = group_link(g)
        self.assertEqual(g.name, text)

    def test_group_link_with_profile(self):
        g = GroupFactory()
        g.save()
        p = GroupProfile.objects.create(group=g, slug="foo")
        text = group_link(g)
        doc = pq(text)
        self.assertEqual(reverse("groups.profile", args=[p.slug]), doc("a")[0].attrib["href"])
        self.assertEqual(g.name, doc("a")[0].text)

    def test_right_group_profile(self):
        """Make sure we get the right group profile."""
        g1 = GroupFactory(pk=100)
        g1.save()
        self.assertEqual(100, g1.pk)
        g2 = GroupFactory(pk=101)
        g2.save()
        self.assertEqual(101, g2.pk)
        p = GroupProfileFactory(pk=100, group=g2, slug="foo")
        self.assertEqual(100, p.pk)

        self.assertEqual(group_link(g1), g1.name)

    def test_group_avatar(self):
        g = GroupFactory()
        g.save()
        p = GroupProfile.objects.create(group=g, slug="foo")
        url = group_avatar(p)
        self.assertRegex(url, fr"{re.escape(settings.STATIC_URL)}avatar\.[0-9a-f]+\.png")
        p.avatar = Mock()
        p.avatar.url = "/foo/bar"
        url = group_avatar(p)
        self.assertEqual("/foo/bar", url)
