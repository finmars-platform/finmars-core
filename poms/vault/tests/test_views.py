import json

from poms.common.common_base_test import BaseTestCase
from poms.vault.models import VaultRecord

TOKEN_RECORD = {
    "user_code": "test-code",
    "name": "test-name",
    "data": {"token": "test-token"}
}


class VaultRecordViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = 'realm00000'
        self.space_code = 'space00000'
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/vault/vault-record/"
        )

    def test__create_record(self):
        response = self.client.post(path=self.url, format="json", data=TOKEN_RECORD)
        self.assertEqual(response.status_code, 201, response.content)
        result = VaultRecord.objects.get(user_code=TOKEN_RECORD["user_code"])
        self.assertEqual(result.data, json.dumps(TOKEN_RECORD["data"]))

    def test__get_record(self):
        obj = VaultRecord.objects.create(
            master_user=self.master_user,
            owner=self.member,
            user_code=TOKEN_RECORD["user_code"],
            name=TOKEN_RECORD["name"],
            data=json.dumps(TOKEN_RECORD["data"])
        )
        response = self.client.get(path=f"{self.url}{obj.id}/")
        self.assertEqual(response.json(), {**response.json(), **TOKEN_RECORD})
