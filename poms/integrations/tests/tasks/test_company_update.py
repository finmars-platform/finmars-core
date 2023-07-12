from poms.common.common_base_test import BaseTestCase
from poms.common.models import ProxyRequest, ProxyUser
from poms.counterparties.models import Counterparty, CounterpartyGroup
from poms.counterparties.serializers import CounterpartySerializer


class DatabaseClientTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        proxy_user = ProxyUser(self.member, self.master_user)
        proxy_request = ProxyRequest(proxy_user)
        self.context = {"request": proxy_request}
        self.group = CounterpartyGroup.objects.get(
            master_user=self.master_user,
            user_code="-",
        )
        self.user_code = self.random_string()
        self.company_data = {
            "user_code": self.user_code,
            "name": self.random_string(),
            "short_name": self.random_string(),
            "public_name": self.random_string(),
            "notes": self.random_string(),
            "group": self.group.id,
        }

    def test__create(self):
        serializer = CounterpartySerializer(
            data=self.company_data,
            context=self.context,
        )

        self.assertTrue(serializer.is_valid())

        serializer.save()

        company = Counterparty.objects.get(
            master_user=self.master_user,
            user_code=self.user_code,
        )

        self.assertIsNotNone(company)
        self.assertEqual(company.user_code, self.user_code)

    def test__update(self):
        serializer = CounterpartySerializer(
            data=self.company_data,
            context=self.context,
        )

        self.assertTrue(serializer.is_valid())

        serializer.save()

        instance = Counterparty.objects.get(
            master_user=self.master_user,
            user_code=self.user_code,
        )
        new_serializer = CounterpartySerializer(
            data=self.company_data,
            context=self.context,
            instance=instance,
        )
        self.assertTrue(new_serializer.is_valid())
        updated_instance = new_serializer.save()
