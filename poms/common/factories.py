import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyFloat, FuzzyInteger, FuzzyText

from django.contrib.auth.models import User

from poms.currencies.models import Currency
from poms.instruments.models import (
    Accrual,
    AccrualCalculationModel,
    AccrualCalculationSchedule,
    Instrument,
    InstrumentClass,
    InstrumentType,
    Periodicity,
)
from poms.users.models import EcosystemDefault, MasterUser, Member


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    is_staff = True
    is_superuser = True


class MasterUserFactory(DjangoModelFactory):
    class Meta:
        model = MasterUser

    name = factory.Sequence(lambda n: f"MasterUser {n}")
    realm_code = "realm00000"
    space_code = "space00000"
    description = factory.Faker("text")
    status = MasterUser.STATUS_ONLINE
    journal_status = MasterUser.JOURNAL_STATUS_DISABLED
    language = "en"
    timezone = "UTC"
    notification_business_days = 0
    token = factory.Faker("hexify", text="^" * 32, upper=False)
    unique_id = factory.Faker("hexify", text="^" * 32, upper=False)
    journal_storage_policy = MasterUser.MONTH

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        existing_instance = model_class.objects.filter(space_code=cls.space_code).first()
        if existing_instance:
            return existing_instance
        return super()._create(model_class, *args, **kwargs)


class MemberFactory(DjangoModelFactory):
    class Meta:
        model = Member

    user = factory.SubFactory(UserFactory)
    master_user = factory.SubFactory(MasterUserFactory)
    join_date = factory.Faker("date_time")
    username = "finmars_bot"
    is_admin = True
    is_owner = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        existing_instance = model_class.objects.filter(username=cls.username).first()
        if existing_instance:
            return existing_instance
        return super()._create(model_class, *args, **kwargs)


class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = Currency

    master_user = factory.SubFactory(MasterUserFactory)
    owner = factory.SubFactory(MemberFactory)
    default_fx_rate = factory.Faker("pyfloat", min_value=1.0, max_value=2.0)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        existing_instance = model_class.objects.filter(user_code=kwargs.get("user_code")).first()
        if existing_instance:
            return existing_instance
        return super()._create(model_class, *args, **kwargs)


class InstrumentTypeFactory(DjangoModelFactory):
    class Meta:
        model = InstrumentType

    master_user = factory.SubFactory(MasterUserFactory)
    owner = factory.SubFactory(MemberFactory)  # default code
    instrument_class_id = InstrumentClass.GENERAL
    user_code = factory.Sequence(lambda n: f"instrument_type_{n}")
    name = factory.LazyAttribute(lambda obj: obj.user_code)
    short_name = factory.LazyAttribute(lambda obj: obj.user_code)
    public_name = factory.LazyAttribute(lambda obj: obj.user_code)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        existing_instance = model_class.objects.filter(
            user_code=kwargs.get("user_code"),
            master_user=kwargs.get("master_user"),
        ).first()
        if existing_instance:
            return existing_instance
        return super()._create(model_class, *args, **kwargs)


class InstrumentFactory(DjangoModelFactory):
    class Meta:
        model = Instrument

    master_user = factory.SubFactory(MasterUserFactory)
    owner = factory.SubFactory(MemberFactory)  # default code
    instrument_class_id = InstrumentClass.GENERAL

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        existing_instance = model_class.objects.filter(
            user_code=kwargs.get("user_code"),
            master_user=kwargs.get("master_user"),
        ).first()
        if existing_instance:
            return existing_instance
        return super()._create(model_class, *args, **kwargs)


class EcosystemDefaultFactory(DjangoModelFactory):
    class Meta:
        model = EcosystemDefault

    master_user = factory.SubFactory(MasterUserFactory)


class PeriodicityFactory(DjangoModelFactory):
    class Meta:
        model = Periodicity
        abstract = True

    class Params:
        periodicity_type = Periodicity.QUARTERLY

    id = factory.LazyAttribute(lambda obj: obj.periodicity_type)
    user_code = factory.LazyAttribute(lambda obj: Periodicity.CLASSES[obj.periodicity_type - 1][1])
    name = factory.LazyAttribute(lambda obj: Periodicity.CLASSES[obj.periodicity_type - 1][2])
    short_name = factory.LazyAttribute(lambda obj: obj.user_code)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if existing_obj := model_class.objects.filter(id=kwargs.get("id")).first():
            return existing_obj

        return model_class(*args, **kwargs)

class AccrualCalculationModelFactory(DjangoModelFactory):
    class Meta:
        model = AccrualCalculationModel
        abstract = True

    class Params:
        model_type = AccrualCalculationModel.DAY_COUNT_ACT_ACT_ICMA

    id = factory.LazyAttribute(lambda obj: obj.model_type)
    user_code = factory.LazyAttribute(lambda obj: AccrualCalculationModel.CLASSES[obj.model_type - 1][1])
    name = factory.LazyAttribute(lambda obj: AccrualCalculationModel.CLASSES[obj.model_type - 1][2])
    short_name = factory.LazyAttribute(lambda obj: obj.user_code)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if existing_obj := model_class.objects.filter(id=kwargs.get("id")).first():
            return existing_obj

        return model_class(*args, **kwargs)


class AccrualCalculationScheduleFactory(DjangoModelFactory):
    class Meta:
        model = AccrualCalculationSchedule

    instrument = factory.SubFactory(InstrumentFactory)
    periodicity = factory.SubFactory(PeriodicityFactory)
    accrual_calculation_model = factory.SubFactory(AccrualCalculationModelFactory)
    accrual_start_date = factory.Faker("future_date")
    first_payment_date = factory.LazyAttribute(lambda obj: obj.accrual_start_date)


class AccrualFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Accrual

    instrument = factory.SubFactory(InstrumentFactory)
    user_code = factory.LazyAttribute(lambda obj: f"{obj.instrument.user_code}:{obj.date}")
    date = factory.Faker("date_object")
    size = FuzzyFloat(100.0, 1000.0)
    notes = FuzzyText(length=20)
    accrual_calculation_model = factory.SubFactory(AccrualCalculationModelFactory)
    periodicity_n = FuzzyInteger(90, 365)
