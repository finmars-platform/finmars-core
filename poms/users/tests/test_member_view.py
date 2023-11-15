import copy
from unittest import mock

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.users.models import Member


API_URL = f"/{settings.BASE_API_URL}/api/v1/users/member/"
REQUEST_DATA = {
    "groups": [],
    "base_api_url": "space00000",
    "is_owner": False,
    "username": "",
    "is_admin": True,
}


class MemberViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = API_URL

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check paging format
        self.assertEqual(response_json["count"], 2)  # 2 members ( tester & finmars_bot)

        self.assertEqual(len(response_json["results"]), 2)

        user_1 = response_json["results"][0]["user"]["username"]
        user_2 = response_json["results"][1]["user"]["username"]
        self.assertEqual({user_1, user_2}, {"finmars_bot", "test_bot"})

    @mock.patch("poms.common.finmars_authorizer.AuthorizerService.invite_member")
    def test__create_member(self, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        self.assertEqual(Member.objects.all().count(), 2)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 3)  # member created

    def test__double_update(self):
        from poms.ui.models import MemberLayout

        # check get_or_create layout in Member method save() works properly
        update_data = {
            "username": self.random_string(),
            "json_data": {"key": "value"},
            "is_admin": True,
            "is_owner": True,
        }

        response = self.client.patch(
            path=f"{self.url}{self.member.id}/",
            format="json",
            data=update_data,
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.patch(
            path=f"{self.url}{self.member.id}/",
            format="json",
            data=update_data,
        )
        self.assertEqual(response.status_code, 200, response.content)

        layout = MemberLayout.objects.filter(member_id=self.member.id).first()
        self.assertIsNotNone(layout)
        self.assertEqual(layout.owner_id, self.member.id)

    @BaseTestCase.cases(
        ("groups", "groups"),
        ("base_api_url", "base_api_url"),
        ("is_owner", "is_owner"),
        ("is_admin", "is_admin"),
    )
    @mock.patch("poms.common.finmars_authorizer.AuthorizerService.invite_member")
    def test__create_member_wo_param(self, param, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        data.pop(param)

        self.assertEqual(Member.objects.all().count(), 2)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 201, response.content)

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 3)  # member created
        self.assertIsNotNone(Member.objects.filter(username=data["username"]).first())

    @BaseTestCase.cases(
        ("username", "username"),
    )
    @mock.patch("poms.common.finmars_authorizer.AuthorizerService.invite_member")
    def test__create_member_wo_username(self, param, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        data.pop(param)

        self.assertEqual(Member.objects.all().count(), 2)

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 400, response.content)

        invite_member.assert_not_called()
        self.assertEqual(Member.objects.all().count(), 2)  # member was not created

    @mock.patch("poms.common.finmars_authorizer.AuthorizerService.invite_member")
    def test__create_member_authorizer_error(self, invite_member):
        data = copy.deepcopy(REQUEST_DATA)
        data["username"] = self.random_string()
        self.assertEqual(Member.objects.all().count(), 2)

        invite_member.side_effect = RuntimeError("Authorizer API error, status=500")

        response = self.client.post(path=self.url, format="json", data=data)
        self.assertEqual(response.status_code, 422, response.content)

        print(response.json())

        invite_member.assert_called_once()
        self.assertEqual(Member.objects.all().count(), 2)  # member was not created
