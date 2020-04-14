from search.utils.string import safe_str

from unittest import TestCase


class TestSafeStr(TestCase):
    def test_safe_str(self):
        self.assertEqual(safe_str("foo"), "foo")
        self.assertEqual(safe_str(b"foo"), "foo")
        self.assertEqual(safe_str("Schröder"), "Schröder")
        self.assertEqual(safe_str("Schröder".encode("utf-8")), "Schröder")
