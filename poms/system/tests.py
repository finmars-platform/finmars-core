from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile

from poms.common.common_base_test import BaseTestCase
from poms.common.storage import FinmarsS3Storage
from poms.explorer.utils import is_true_value
from poms.system.models import WhitelabelModel
from poms.system.utils import get_image_content

CSS_CONTENT = """
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


UI_ROOT = ".system/ui"
API_PREFIX = f"api/storage/{UI_ROOT}"
STORAGE_PREFIX = f"space00000/{UI_ROOT}/"


class WhitelabelViewSetTest(BaseTestCase):
    def setUp(self):
        self.maxDiff = None
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

    def _create_name_and_configuration_code(self):
        name = f"{self.random_string()}-white-lable"
        configuration_code = f"com.finmars.{name}"
        return name, configuration_code

    def create_whitelabel(self, is_default=False):
        name, configuration_code = self._create_name_and_configuration_code()

        return WhitelabelModel.objects.create(
            configuration_code=configuration_code,
            name=name,
            owner=self.member,
            theme_css_url="https://example.com/theme.css",
            logo_dark_url="https://example.com/logo_dark.png",
            logo_light_url="https://example.com/logo_light.png",
            favicon_url="https://example.com/favicon.png",
            custom_css="body { background-color: #aaa; }",
            is_default=is_default,
            notes="some notes"
        )

    def test__list(self):
        model = self.create_whitelabel()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[0]["id"], model.id)
        self.assertIn("company_name", response_json[0])
        self.assertIn("theme_code", response_json[0])
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
        self.assertIn("theme_code", response_json)
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
        name, configuration_code = self._create_name_and_configuration_code()

        return {
            "configuration_code": configuration_code,
            "name": name,
            "theme_css_file": SimpleUploadedFile(
                "theme.css", CSS_CONTENT, content_type="text/css"
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
            "notes": "some notes"
        }

    def validate_response(self, response_json, name: str, configuration_code: str):
        self.assertEqual(response_json["configuration_code"], configuration_code)
        self.assertEqual(response_json["name"], name)
        self.assertEqual(response_json["theme_css_url"], f"{API_PREFIX}/theme.css")
        self.assertEqual(response_json["logo_dark_url"], f"{API_PREFIX}/dark.png")
        self.assertEqual(response_json["logo_light_url"], f"{API_PREFIX}/light.png")
        self.assertEqual(response_json["favicon_url"], f"{API_PREFIX}/favicon.png")
        self.assertEqual(response_json["notes"], "some notes")

        inst_db = WhitelabelModel.objects.get(id=response_json["id"])
        self.assertEqual(inst_db.is_enabled, True)

    def test__create(self):
        request_data = self.create_request_data()
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(self.storage_mock.save.call_count, 4)
        storage_call_args = self.storage_mock.save.call_args_list[0]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}theme.css")
        storage_call_args = self.storage_mock.save.call_args_list[1]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}dark.png")
        storage_call_args = self.storage_mock.save.call_args_list[2]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}light.png")
        storage_call_args = self.storage_mock.save.call_args_list[3]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}favicon.png")

        response_json = response.json()
        self.validate_response(response_json, request_data["name"], request_data["configuration_code"])
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

        self.validate_response(response_json, request_data["name"], request_data["configuration_code"])
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
        self.validate_response(response_json, request_data["name"], request_data["configuration_code"])
        self.assertEqual(
            response_json["custom_css"], "body { background-color: #fff; }"
        )

    def test__delete(self):
        model = self.create_whitelabel()
        response = self.client.delete(path=f"{self.url}{model.id}/")
        self.assertEqual(response.status_code, 204)

        none = WhitelabelModel.objects.filter(id=model.id).first()

        self.assertIsNone(none)

    def test__try_delete_default(self):
        model = self.create_whitelabel(is_default=True)
        response = self.client.delete(path=f"{self.url}{model.id}/")
        self.assertEqual(response.status_code, 400)

        obj = WhitelabelModel.objects.filter(id=model.id).first()

        self.assertIsNotNone(obj)

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

    def test__update_is_default_field(self):
        model = self.create_whitelabel()
        request_data = {"is_default": True}
        response = self.client.patch(
            path=f"{self.url}{model.id}/",
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.json())

        response_json = response.json()
        self.assertTrue(response_json["is_default"])

        model.refresh_from_db()
        self.assertTrue(model.is_default)

    def test__is_default_can_be_only_one(self):
        model_1 = self.create_whitelabel()
        request_data = {"is_default": True}
        response = self.client.patch(
            path=f"{self.url}{model_1.id}/",
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.json())
        model_1.refresh_from_db()
        self.assertTrue(model_1.is_default)

        model_2 = self.create_whitelabel()
        response = self.client.patch(
            path=f"{self.url}{model_2.id}/",
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.json())
        model_2.refresh_from_db()
        self.assertTrue(model_2.is_default)

        model_1.refresh_from_db()
        self.assertFalse(model_1.is_default)

    def create_request_with_utf8_names(self):
        name, configuration_code = self._create_name_and_configuration_code()

        return {
            "user_code": configuration_code,
            "configuration_code": configuration_code,
            "name": name,
            "theme_css_file": SimpleUploadedFile(
                "theme 1.css", CSS_CONTENT, content_type="text/css"
            ),
            "logo_dark_image": SimpleUploadedFile(
                "dark 2.png", self.image_content, content_type="image/png"
            ),
            "logo_light_image": SimpleUploadedFile(
                "пыжый 3.png", self.image_content, content_type="image/png"
            ),
            "favicon_image": SimpleUploadedFile(
                "зюфьянка 4.png", self.image_content, content_type="image/png"
            ),
        }

    def test__utf8_names(self):
        request_data = self.create_request_with_utf8_names()
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.json())

        self.assertEqual(self.storage_mock.save.call_count, 4)
        storage_call_args = self.storage_mock.save.call_args_list[0]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}theme 1.css")
        storage_call_args = self.storage_mock.save.call_args_list[1]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}dark 2.png")
        storage_call_args = self.storage_mock.save.call_args_list[2]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}пыжый 3.png")
        storage_call_args = self.storage_mock.save.call_args_list[3]
        self.assertEqual(storage_call_args[0][0], f"{STORAGE_PREFIX}зюфьянка 4.png")

        response_json = response.json()
        self.assertEqual(
            response_json["theme_css_url"], f"{API_PREFIX}/theme%201.css"
        )
        self.assertEqual(
            response_json["logo_dark_url"], f"{API_PREFIX}/dark%202.png"
        )
        self.assertEqual(
            response_json["logo_light_url"], f"{API_PREFIX}/%D0%BF%D1%8B%D0%B6%D1%8B%D0%B9%203.png"
        )
        self.assertEqual(
            response_json["favicon_url"], f"{API_PREFIX}/%D0%B7%D1%8E%D1%84%D1%8C%D1%8F%D0%BD%D0%BA%D0%B0%204.png"
        )

    @BaseTestCase.cases(
        ("0", "&"),
        ("1", "$"),
        ("2", "@"),
        ("3", "="),
        ("4", ";"),
        ("5", "/"),
        ("6", ":"),
        ("7", ","),
        ("8", "?"),
        ("9", "\\"),
        ("10", "^"),
        ("11", "%"),
        ("12", "]"),
        ("13", "<"),
        ("14", "["),
        ("15", "'"),
        ("16", '"'),
        ("17", "~"),
        ("18", "#"),
        ("19", "|"),
        ("20", "{"),
        ("21", "}"),
        ("22", "^"),
    )
    def test__bad_name(self, symbol):
        request_data = {
            "company_name": "BAD name",
            "theme_css_file": SimpleUploadedFile(
                f"theme_{symbol}.css",
                CSS_CONTENT,
                content_type="text/css",
            ),
        }
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test__bad_extension_css(self):
        request_data = {
            "company_name": "BAD extension",
            "theme_css_file": SimpleUploadedFile(
                "theme.png", CSS_CONTENT, content_type="text/css"
            ),
        }
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test__bad_extension_image(self):
        request_data = {
            "company_name": "BAD extension",
            "logo_dark_image": SimpleUploadedFile(
                "dark 2.txt", self.image_content,
                content_type="image/png",
            ),
        }
        response = self.client.post(
            path=self.url,
            data=request_data,
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
