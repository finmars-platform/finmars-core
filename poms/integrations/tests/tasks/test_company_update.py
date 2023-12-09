from poms.common.common_base_test import BaseTestCase
from poms.common.models import ProxyRequest, ProxyUser
from poms.counterparties.models import Counterparty
from poms.counterparties.serializers import CounterpartySerializer


class DatabaseClientTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        proxy_user = ProxyUser(self.member, self.master_user)
        proxy_request = ProxyRequest(proxy_user)
        self.context = {"request": proxy_request}
        self.user_code = self.random_string()
        self.company_data = {
            "user_code": self.user_code,
            "name": self.user_code,
            "short_name": self.user_code,
            "public_name": self.random_string(),
            "notes": self.random_string(),
        }

    def check_serializer_get_counterparty(self, serializer):
        self.assertTrue(serializer.is_valid())
        serializer.save()
        return Counterparty.objects.get(
            master_user=self.master_user,
            user_code=self.user_code,
        )

    def test__create(self):
        serializer = CounterpartySerializer(data=self.company_data)

        company = self.check_serializer_get_counterparty(serializer)
        self.assertIsNotNone(company)
        self.assertEqual(company.user_code, self.user_code)

    def test__update(self):
        serializer = CounterpartySerializer(
            data=self.company_data,
            context=self.context,
        )

        instance = self.check_serializer_get_counterparty(serializer)
        new_serializer = CounterpartySerializer(
            data=self.company_data,
            context=self.context,
            instance=instance,
        )
        self.assertTrue(new_serializer.is_valid())
        new_serializer.save()
