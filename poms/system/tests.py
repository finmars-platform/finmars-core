from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.utils import is_true_value
from poms.system.models import WhitelabelModel
from poms.system.utils import get_image_content


css_content = """
.file-upload-form {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: blue;
    padding: 20px;
    border-radius: 5px;
}
.file-upload-input {
    background-color: white;
    padding: 10px;
    border: none;
    border-radius: 5px;
}""".encode()


EXPECTED_RESPONSE = {
    "id": 1,
    "company_name": "Test Company",
    "theme_code": "com.finmars.client-a",
    "theme_css_url": "https://finmars.com/realm00000/space00000/api/storage/.system/ui/theme.css",
    "logo_dark_url": "https://finmars.com/realm00000/space00000/api/storage/.system/ui/logo_dark.png",
    "logo_light_url": "https://finmars.com/realm00000/space00000/api/storage/.system/ui/logo_light.png",
    "favicon_url": "https://finmars.com/realm00000/space00000/api/storage/.system/ui/favicon.png",
    "custom_css": "body { background-color: #fff; }",
    "meta": {
        "execution_time": 28,
        "request_id": "59db8db2-0815-4129-a14c-3d1475fc308c",
    },
}
PREFIX = "https://finmars.com/realm00000/space00000/api/storage/.system/ui/"


class WhitelabelViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/system/whitelabel/"

        self.storage_patch = mock.patch(
            "poms.system.serializers.storage",
            spec=FinmarsS3Storage,
        )
        self.storage_mock = self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)
        self.image_content = get_image_content("logo_dark.png")

    def create_whitelabel(self, is_default=False):
        return WhitelabelModel.objects.create(
            company_name=self.random_string(),
            theme_code="com.finmars.client-a",
            theme_css_url="https://example.com/theme.css",
            logo_dark_url="https://example.com/logo_dark.png",
            logo_light_url="https://example.com/logo_light.png",
            favicon_url="https://example.com/favicon.png",
            custom_css="body { background-color: #aaa; }",
            is_default=is_default,
        )

    def test__list(self):
        model = self.create_whitelabel()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[0]["id"], model.id)
        self.assertIn("company_name", response_json[0])
        self.assertEqual(response_json[0]["theme_code"], "com.finmars.client-a")
        self.assertEqual(
            response_json[0]["theme_css_url"], "https://example.com/theme.css"
        )
        self.assertEqual(
            response_json[0]["logo_dark_url"], "https://example.com/logo_dark.png"
        )
        self.assertEqual(
            response_json[0]["logo_light_url"], "https://example.com/logo_light.png"
        )
        self.assertEqual(
            response_json[0]["favicon_url"], "https://example.com/favicon.png"
        )
        self.assertEqual(
            response_json[0]["custom_css"], "body { background-color: #aaa; }"
        )

    def test__retrieve(self):
        model = self.create_whitelabel()
        response = self.client.get(f"{self.url}{model.id}/")
        self.assertEqual(response.status_code, 200)

        response_json = response.json()

        self.assertEqual(response_json["id"], model.id)
        self.assertIn("company_name", response_json)
        self.assertEqual(response_json["theme_code"], "com.finmars.client-a")
        self.assertEqual(
            response_json["theme_css_url"], "https://example.com/theme.css"
        )
        self.assertEqual(
            response_json["logo_dark_url"], "https://example.com/logo_dark.png"
        )
        self.assertEqual(
            response_json["logo_light_url"], "https://example.com/logo_light.png"
        )
        self.assertEqual(
            response_json["favicon_url"], "https://example.com/favicon.png"
        )
        self.assertEqual(
            response_json["custom_css"], "body { background-color: #aaa; }"
        )

    def create_request_data(self):
        return {
            "company_name": "Test Company",
            "theme_code": "com.finmars.client-a",
            "theme_css_file": SimpleUploadedFile(
                "theme.css", css_content, content_type="text/css"
            ),
            "logo_dark_image": SimpleUploadedFile(
                "dark.png", self.image_content, content_type="image/png"
            ),
            "logo_light_image": SimpleUploadedFile(
                "light.png", self.image_content, content_type="image/png"
            ),
            "favicon_image": SimpleUploadedFile(
                "favicon.png", self.image_content, content_type="image/png"
            ),
            "custom_css": "body { background-color: #fff; }",
        }

    def test__create(self):
        request_data = self.create_request_data()
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.json())

        response_json = response.json()

        self.assertEqual(response_json["company_name"], "Test Company")
        self.assertEqual(response_json["theme_code"], "com.finmars.client-a")
        self.assertEqual(response_json["theme_css_url"], f"{PREFIX}theme.css")
        self.assertEqual(response_json["logo_dark_url"], f"{PREFIX}logo_dark.png")
        self.assertEqual(response_json["logo_light_url"], f"{PREFIX}logo_light.png")
        self.assertEqual(response_json["favicon_url"], f"{PREFIX}favicon.png")
        self.assertEqual(
            response_json["custom_css"], "body { background-color: #fff; }"
        )

    def test__update_patch(self):
        model = self.create_whitelabel()
        request_data = self.create_request_data()
        request_data.pop("custom_css")
        response = self.client.patch(
            path=f"{self.url}{model.id}/",
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.json())

        response_json = response.json()

        self.assertEqual(response_json["company_name"], "Test Company")
        self.assertEqual(response_json["theme_code"], "com.finmars.client-a")
        self.assertEqual(response_json["theme_css_url"], f"{PREFIX}theme.css")
        self.assertEqual(response_json["logo_dark_url"], f"{PREFIX}logo_dark.png")
        self.assertEqual(response_json["logo_light_url"], f"{PREFIX}logo_light.png")
        self.assertEqual(response_json["favicon_url"], f"{PREFIX}favicon.png")

        # should be old value
        self.assertEqual(
            response_json["custom_css"], "body { background-color: #aaa; }"
        )

    def test__update_put(self):
        model = self.create_whitelabel()
        request_data = self.create_request_data()
        response = self.client.put(
            path=f"{self.url}{model.id}/",
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.json())

        response_json = response.json()

        self.assertEqual(response_json["company_name"], "Test Company")
        self.assertEqual(response_json["theme_code"], "com.finmars.client-a")
        self.assertEqual(response_json["theme_css_url"], f"{PREFIX}theme.css")
        self.assertEqual(response_json["logo_dark_url"], f"{PREFIX}logo_dark.png")
        self.assertEqual(response_json["logo_light_url"], f"{PREFIX}logo_light.png")
        self.assertEqual(response_json["favicon_url"], f"{PREFIX}favicon.png")
        self.assertEqual(
            response_json["custom_css"], "body { background-color: #fff; }"
        )

    def test__delete(self):
        model = self.create_whitelabel()
        response = self.client.delete(path=f"{self.url}{model.id}/")
        self.assertEqual(response.status_code, 204)

        none = WhitelabelModel.objects.filter(id=model.id).first()

        self.assertIsNone(none)

    @BaseTestCase.cases(
        ("true", "true"),
        ("false", "false"),
    )
    def test__is_default_filter(self, value):
        self.create_whitelabel()
        self.create_whitelabel(is_default=True)

        response = self.client.get(path=f"{self.url}?is_default={value}")
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[0]["is_default"], is_true_value(value))
