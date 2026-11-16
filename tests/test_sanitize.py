import json
import unittest

from ccnu_reservation.transport import escape_control_chars_in_strings


def parse(raw):
    return json.loads(escape_control_chars_in_strings(raw).decode("utf-8"))


class EscapeControlCharsTest(unittest.TestCase):
    def test_escapes_newline_inside_string(self):
        self.assertEqual(parse(b'{"a":"line1\nline2"}'), {"a": "line1\nline2"})

    def test_escapes_tab_carriage_return_and_other_controls(self):
        raw = b'{"a":"x\ty\rz\x01w"}'
        self.assertEqual(parse(raw), {"a": "x\ty\rz\x01w"})

    def test_preserves_already_escaped_sequences(self):
        raw = b'{"a":"say \\"hi\\" and \\\\ bye"}'
        self.assertEqual(parse(raw), {"a": 'say "hi" and \\ bye'})

    def test_preserves_multibyte_text(self):
        raw = '{"a":"南湖分馆一楼"}'.encode("utf-8")
        self.assertEqual(parse(raw), {"a": "南湖分馆一楼"})

    def test_leaves_whitespace_outside_strings(self):
        raw = b'{\n  "a": 1\n}'
        self.assertEqual(parse(raw), {"a": 1})

    def test_handles_upstream_style_payload(self):
        raw = b'{"status":true,"code":200,"message":"ok","data":{"likeSeats":"a\nb"}}'
        self.assertEqual(parse(raw)["data"]["likeSeats"], "a\nb")


if __name__ == "__main__":
    unittest.main()
