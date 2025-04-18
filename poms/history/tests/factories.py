
import json
import factory
from faker import Faker
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from poms.common.factories import MasterUserFactory, MemberFactory
from poms.history.models import HistoricalRecord

faker = Faker()


class HistoricalRecordFactory(DjangoModelFactory):
    class Meta:
        model = HistoricalRecord

    master_user = factory.SubFactory(MasterUserFactory)
    member = factory.SubFactory(MemberFactory)
    user_code = factory.Faker("uuid4")
    action = FuzzyChoice([
        HistoricalRecord.ACTION_CREATE,
        HistoricalRecord.ACTION_CHANGE,
        HistoricalRecord.ACTION_DELETE,
        HistoricalRecord.ACTION_DANGER,
        HistoricalRecord.ACTION_RECYCLE_BIN
    ])
    content_type = None
    context_url = factory.Faker("url")
    notes = factory.Faker("sentence")
    diff = factory.Faker("text", max_nb_chars=500)
    json_data = '{}'
