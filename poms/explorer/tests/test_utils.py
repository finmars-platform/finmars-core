from poms.common.common_base_test import BaseTestCase
from poms.explorer.utils import define_content_type, join_path


class DefineContentTypeTest(BaseTestCase):
    @BaseTestCase.cases(
        ("none", "file.pdf.html.csv.txt.xxx", None),
        ("no_extension", "file.pdf.html.csv.txt.", None),
        ("html", "file.pdf.html", "text/html"),
        ("text", "file.html.txt", "plain/text"),
        ("js", "file.css.js", "text/javascript"),
        ("csv", "file.html.csv", "text/csv"),
        ("json", "file.pdf.json", "application/json"),
        ("yml", "file.pdf.yml", "application/yaml"),
        ("yaml", "file.pdf.yaml", "application/yaml"),
        ("py", "file.js.py", "text/x-python"),
        ("png", "file.pdf.png", "image/png"),
        ("jpg", "file.png.jpg", "image/jpeg"),
        ("jpeg", "file.pdf.jpeg", "image/jpeg"),
        ("pdf", "file.html.pdf", "application/pdf"),
        ("doc", "file.pdf.doc", "application/msword"),
        ("docx", "file.pdf.docx", "application/msword"),
        ("css", "file.pdf.css", "text/css"),
        ("xls", "file.txt.xls", "application/vnd.ms-excel"),
        (
            "xlsx",
            "file.csv.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
    def test__content_type(self, filename, content_type):
        self.assertEqual(define_content_type(filename), content_type)


class JoinPathTest(BaseTestCase):
    @BaseTestCase.cases(
        ("1", "realm0000.space0000", "path", "realm0000.space0000/path"),
        ("2", "realm0000.space0000", "/path", "realm0000.space0000/path"),
        ("3", "realm0000.space0000/", "/path", "realm0000.space0000/path"),
        ("4", "realm0000.space0000/", "path", "realm0000.space0000/path"),
        ("empty", "realm0000.space0000/", "", "realm0000.space0000"),
        ("null", "realm0000.space0000/", None, "realm0000.space0000"),
    )
    def test__content_type(self, space_code, path, result):
        self.assertEqual(join_path(space_code, path), result)
