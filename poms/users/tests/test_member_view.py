import copy
from unittest import mock

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.users.models import Member

REQUEST_DATA = {
    "groups": [],
    "base_api_url": "space00000",
    "is_owner": False,
    "username": "",
    "is_admin": True,
}


class MemberViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/users/member/"

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check paging format
        self.assertEqual(response_json["count"], 1)  # finmars_bot

        self.assertEqual(len(response_json["results"]), 1)

        username = response_json["results"][0]["user"]["username"]
        self.assertEqual(username, self.user.username)

    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__create_member(self, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        self.assertEqual(Member.objects.all().count(), 1)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 2)  # member created

    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__create_member_check_called_url(self, requests_post):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        self.assertEqual(Member.objects.all().count(), 1)

        requests_post.return_value = mock_response = mock.Mock()
        mock_response.status_code = 200

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)

        requests_post.assert_called_once()

        self.assertEqual(Member.objects.all().count(), 2)  # member created

    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__double_update(self, requests_post):
        user_name = self.random_string()
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = user_name

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)
        member_data = response.json()

        data.update(**{
            "data": {"key": "value"},
            "is_admin": True,
            "is_owner": True,
        })

        response = self.client.patch(
            path=f"{self.url}{member_data['id']}/",
            format="json",
            data=data,
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["data"], data["data"])

    @BaseTestCase.cases(
        ("groups", "groups"),
        ("base_api_url", "base_api_url"),
        ("is_owner", "is_owner"),
        ("is_admin", "is_admin"),
    )
    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__create_member_wo_param(self, param, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        data.pop(param)

        self.assertEqual(Member.objects.all().count(), 1)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 2)  # member created
        self.assertIsNotNone(Member.objects.filter(username=data["username"]).first())

    @BaseTestCase.cases(
        ("username", "username"),
    )
    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__create_member_wo_username(self, param, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        data.pop(param)

        self.assertEqual(Member.objects.all().count(), 1)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 400, response.content)

        invite_member.assert_not_called()
        self.assertEqual(Member.objects.all().count(), 1)  # member was not created

    @mock.patch("poms.users.views.AuthorizerService.invite_member")
    def test__create_member_authorizer_error(self, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        self.assertEqual(Member.objects.all().count(), 1)

        invite_member.side_effect = RuntimeError("Authorizer API error, status=500")

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 422, response.content)

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 1)  # member was not created

    def test__retrieve_0(self):
        response = self.client.get(path=f"{self.url}0/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertTrue(response_json["is_owner"])
        self.assertTrue(response_json["is_admin"])
        self.assertTrue(response_json["is_superuser"])
        self.assertFalse(response_json["is_deleted"])

        user_data = response_json["user"]
        self.assertEqual(user_data["username"], "test_user")
        self.assertEqual(user_data["id"], self.user.id)
