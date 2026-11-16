import unittest

from ccnu_reservation.auth import (
    find_seat_project_id,
    parse_cas_form,
    token_from_location,
)
from ccnu_reservation.errors import LoginFailed


class CasFormTest(unittest.TestCase):
    HTML = """
    <html><body>
      <form id="fm1" action="/cas/login?service=https%3A%2F%2Fkjyy.ccnu.edu.cn%2Frem&amp;locale=zh">
        <input type="hidden" name="lt" value="LT-123-abc" />
        <input type="hidden" name="execution" value="e1s1" />
        <input type="text" name="username" />
      </form>
    </body></html>
    """

    def test_extracts_lt_execution_and_action(self):
        lt, execution, action = parse_cas_form(self.HTML)
        self.assertEqual(lt, "LT-123-abc")
        self.assertEqual(execution, "e1s1")
        self.assertEqual(
            action,
            "/cas/login?service=https%3A%2F%2Fkjyy.ccnu.edu.cn%2Frem&locale=zh",
        )

    def test_raises_when_form_missing(self):
        with self.assertRaises(LoginFailed):
            parse_cas_form("<html></html>")


class ProjectIdTest(unittest.TestCase):
    def test_finds_id_from_onclick_element(self):
        html = """<div class="app" onclick="gotoProject('/rem/static/gotoProject/1981289670190006272')">
                    座位预约
                  </div>"""
        self.assertEqual(find_seat_project_id(html), "1981289670190006272")

    def test_finds_id_from_anchor(self):
        html = '<a href="/rem/static/gotoProject/123456">座位预约</a>'
        self.assertEqual(find_seat_project_id(html), "123456")

    def test_ignores_other_projects(self):
        html = '<a href="/rem/static/gotoProject/999">研讨间预约</a>'
        self.assertEqual(find_seat_project_id(html), "")


class HandoffTokenTest(unittest.TestCase):
    def test_reads_token_from_query(self):
        self.assertEqual(
            token_from_location("https://kjyy.ccnu.edu.cn/jsq-v/#/home?token=abc.def"),
            "abc.def",
        )

    def test_reads_token_from_fragment_query(self):
        self.assertEqual(
            token_from_location("https://kjyy.ccnu.edu.cn/jsq-v/#/?token=ghi.jkl"),
            "ghi.jkl",
        )

    def test_raises_without_token(self):
        with self.assertRaises(LoginFailed):
            token_from_location("https://kjyy.ccnu.edu.cn/jsq-v/#/home")


if __name__ == "__main__":
    unittest.main()
