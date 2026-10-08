import unittest

from http_content_range_parser import ContentRange, ContentRangeParseError


class TestParseSatisfied(unittest.TestCase):
    def test_basic_satisfied_range(self):
        cr = ContentRange.parse("bytes 0-1023/2048")
        self.assertEqual(cr.unit, "bytes")
        self.assertEqual(cr.start, 0)
        self.assertEqual(cr.end, 1023)
        self.assertEqual(cr.total, 2048)

    def test_satisfied_range_unknown_total(self):
        cr = ContentRange.parse("bytes 0-1023/*")
        self.assertEqual(cr.start, 0)
        self.assertEqual(cr.end, 1023)
        self.assertIsNone(cr.total)

    def test_start_zero_end_zero(self):
        cr = ContentRange.parse("bytes 0-0/1")
        self.assertEqual(cr.start, 0)
        self.assertEqual(cr.end, 0)
        self.assertEqual(cr.total, 1)

    def test_whitespace_around_header(self):
        cr = ContentRange.parse("  bytes 0-1023/2048  ")
        self.assertEqual(cr.start, 0)
        self.assertEqual(cr.end, 1023)
        self.assertEqual(cr.total, 2048)


class TestParseUnsatisfied(unittest.TestCase):
    def test_unsatisfied_range(self):
        cr = ContentRange.parse("bytes */2048")
        self.assertEqual(cr.unit, "bytes")
        self.assertIsNone(cr.start)
        self.assertIsNone(cr.end)
        self.assertEqual(cr.total, 2048)


class TestRejection(unittest.TestCase):
    def test_empty_header(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("")

    def test_whitespace_only(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("   ")

    def test_non_bytes_unit(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("items 0-1/10")

    def test_missing_space(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes0-1023/2048")

    def test_missing_slash(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes 0-1023")

    def test_missing_dash_in_satisfied_form(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes 01023/2048")

    def test_end_less_than_start(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes 5-2/10")

    def test_unsatisfied_with_unknown_total(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes */*")

    def test_leading_zero_in_field(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes 00-1023/2048")

    def test_non_digit_in_field(self):
        with self.assertRaises(ContentRangeParseError):
            ContentRange.parse("bytes abc-1023/2048")


class TestTypes(unittest.TestCase):
    def test_fields_are_int_or_none(self):
        cr = ContentRange.parse("bytes 0-1023/*")
        self.assertIsInstance(cr.start, int)
        self.assertIsInstance(cr.end, int)
        self.assertIsNone(cr.total)

    def test_unsatisfied_fields_are_none(self):
        cr = ContentRange.parse("bytes */2048")
        self.assertIsNone(cr.start)
        self.assertIsNone(cr.end)
        self.assertIsInstance(cr.total, int)


class TestFrozen(unittest.TestCase):
    def test_dataclass_is_frozen(self):
        cr = ContentRange.parse("bytes 0-1023/2048")
        with self.assertRaises(Exception):
            cr.start = 10  # type: ignore[misc]


class TestErrorSubclassing(unittest.TestCase):
    def test_parse_error_is_value_error(self):
        self.assertTrue(issubclass(ContentRangeParseError, ValueError))


if __name__ == "__main__":
    unittest.main()
