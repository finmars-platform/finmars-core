import time
import traceback
from datetime import timedelta
from logging import getLogger

import django_filters
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.db import transaction
from django.utils import timezone, translation
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy
from django.views.decorators.csrf import ensure_csrf_cookie
from django_filters.rest_framework import FilterSet
from rest_framework import parsers, renderers, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

import pyotp
from celery.result import AsyncResult

from poms.accounts.models import Account, AccountType
from poms.celery_tasks.models import CeleryTask
from poms.common.filters import CharFilter, NoOpFilter
from poms.common.finmars_authorizer import AuthorizerService
from poms.common.pagination import BigPagination
from poms.common.utils import datetime_now
from poms.common.views import (
    AbstractApiView,
    AbstractAsyncViewSet,
    AbstractModelViewSet,
    AbstractViewSet,
)

from poms.complex_import.models import ComplexImportScheme
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, InstrumentType
from poms.integrations.models import InstrumentDownloadScheme
from poms.strategies.models import (
    Strategy1,
    Strategy1Group,
    Strategy1Subgroup,
    Strategy2,
    Strategy2Group,
    Strategy2Subgroup,
    Strategy3,
    Strategy3Group,
    Strategy3Subgroup,
)
from poms.transactions.models import (
    ComplexTransaction,
    Transaction,
    TransactionType,
    TransactionTypeAction,
    TransactionTypeInput,
)
from poms.users.filters import (
    IsMemberFilterBackend,
    MasterUserBackupsForOwnerOnlyFilter,
    MasterUserFilter,
    OwnerByMasterUserFilter,
    OwnerByUserFilter,
)
from poms.users.models import (
    EcosystemDefault,
    MasterUser,
    Member,
    OtpToken,
    ResetPasswordToken,
    UsercodePrefix,
)
from poms.users.permissions import (
    IsCurrentMasterUser,
    IsCurrentUser,
    SuperUserOrReadOnly,
)
from poms.users.serializers import (
    EcosystemDefaultSerializer,
    EmailSerializer,
    MasterUserCopySerializer,
    MasterUserCreateSerializer,
    MasterUserLightSerializer,
    MasterUserSerializer,
    MemberSerializer,
    OtpTokenSerializer,
    PasswordTokenSerializer,
    PingSerializer,
    UsercodePrefixSerializer,
    UserRegisterSerializer,
    UserSerializer,
    UserSetPasswordSerializer,
    UserUnsubscribeSerializer,
)
from poms.users.tasks import clone_master_user

_l = getLogger("poms.users")


class ObtainAuthTokenViewSet(AbstractApiView, ViewSet):
    parser_classes = (
        FormParser,
        MultiPartParser,
        JSONParser,
    )
    serializer_class = AuthTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        Token.objects.filter(user=user).delete()
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class PingViewSet(AbstractApiView, ViewSet):
    permission_classes = [
        AllowAny,
    ]

    @method_decorator(ensure_csrf_cookie)
    def list(self, request, *args, **kwargs):
        current_master_user_id = None
        current_member_id = None

        if hasattr(request.user, "master_user") and request.user.master_user:
            current_master_user_id = request.user.master_user.id

        if hasattr(request.user, "member") and request.user.member:
            current_member_id = request.user.member.id

        serializer = PingSerializer(
            instance={
                "message": "pong",
                "version": request.version,
                "is_authenticated": request.user.is_authenticated,
                "current_master_user_id": current_master_user_id,
                "current_member_id": current_member_id,
                "is_anonymous": request.user.is_anonymous,
                "now": timezone.template_localtime(timezone.now()),
            }
        )
        return Response(serializer.data)


class ProtectedPingViewSet(PingViewSet):
    permission_classes = [
        IsAuthenticated,
    ]


class LoginViewSet(ViewSet):
    permission_classes = []
    parser_classes = [
        FormParser,
        MultiPartParser,
        JSONParser,
    ]
    serializer_class = AuthTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        response = {"success": True, "two_factor_check": False}

        try:
            existing_user = User.objects.get(username=user)
        except User.DoesNotExist as e:
            raise PermissionDenied() from e

        if existing_user.profile.two_factor_verification:
            tokens = OtpToken.objects.filter(user=existing_user)

            active_tokens = False

            if len(list(tokens)):
                for token in tokens:
                    if token.is_active:
                        active_tokens = True

            response["two_factor_check"] = bool(active_tokens)

        if not response["two_factor_check"]:
            login(request, user)

        return Response(response)


class LogoutViewSet(ViewSet):
    def create(self, request, *args, **kwargs):
        logout(request)
        return Response({"success": True})


class UserRegisterViewSet(AbstractApiView, ViewSet):
    serializer_class = UserRegisterSerializer
    permission_classes = []
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.save()
        user = validated_data["user"]
        login(request, user)
        return Response({"success": True})


class MasterUserCreateViewSet(ViewSet):
    serializer_class = MasterUserCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.save()
        name = validated_data["name"]
        description = validated_data["description"]

        master_user = MasterUser.objects.create_master_user(
            user=request.user,
            language=translation.get_language(),
            name=name,
            description=description,
        )

        member = Member.objects.create(
            user=request.user,
            master_user=master_user,
            is_owner=True,
            is_admin=True,
        )
        member.save()

        return Response(
            {
                "id": master_user.id,
                "name": master_user.name,
                "description": master_user.description,
            }
        )


class MasterUserCopyViewSet(AbstractAsyncViewSet):
    celery_task = clone_master_user
    serializer_class = MasterUserCopySerializer

    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        task_id = instance.task_id

        signer = TimestampSigner()

        _l.debug(f"TASK id: {task_id}")

        if task_id:
            res = AsyncResult(signer.unsign(task_id))

            try:
                celery_task = CeleryTask.objects.get(
                    master_user=request.user.master_user, task_id=task_id
                )
            except CeleryTask.DoesNotExist:
                celery_task = None
                _l.debug("Cant create Celery Task")

            _l.debug(f"celery_task {celery_task}")

            st = time.perf_counter()

            if res.ready():
                instance = res.result

                if celery_task:
                    celery_task.finished_at = datetime_now()

            elif celery_task:
                if res.result:
                    celery_task_data = {}

                    celery_task.data = celery_task_data

            _l.debug(f"AsyncResult res.ready: {time.perf_counter() - st}")

            _l.debug(f"instance {instance}")

            if instance.master_user.id != request.user.master_user.id:
                raise PermissionDenied()

            _l.debug(f"TASK STATUS {res.status}  celery_task {celery_task}")

            instance.task_id = task_id
            instance.task_status = res.status

            if celery_task:
                celery_task.task_status = res.status
                celery_task.save()

        else:
            res = self.celery_task.apply_async(
                kwargs={
                    "instance": instance,
                    "name": request.data["name"],
                    "current_user": request.user,
                }
            )
            instance.task_id = signer.sign(f"{res.id}")

            celery_task = CeleryTask.objects.create(
                master_user=request.user.master_user,
                member=request.user.member,
                task_type="clone_master_user",
                celery_task_id=res.id,
            )

            celery_task.save()

            instance.task_status = res.status

        serializer = self.get_serializer(instance=instance, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MasterUserCreateCheckUniquenessViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        name = request.query_params.get("name")

        try:
            MasterUser.objects.get(name=name)
            result = False

        except MasterUser.DoesNotExist:
            result = True

        return Response({"unique": result})


def get_password_reset_token_expiry_time():
    """
    Returns the password reset token expirty time in hours (default: 24)
    Set Django SETTINGS.DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME
    to overwrite this time
    :return: expiry time
    """
    # get token validation time
    return getattr(settings, "DJANGO_REST_MULTITOKENAUTH_RESET_TOKEN_EXPIRY_TIME", 24)


class ResetPasswordConfirmViewSet(AbstractApiView, ViewSet):
    """
    An Api View which provides a method to reset a password based on a unique token
    """

    throttle_classes = ()
    permission_classes = []
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = PasswordTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        token = serializer.validated_data["token"]

        # get token validation time
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # find token
        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()

        if reset_password_token is None:
            return Response({"status": "notfound"}, status=status.HTTP_404_NOT_FOUND)

        # check expiry date
        expiry_date = reset_password_token.created_at + timedelta(
            hours=password_reset_token_validation_time
        )

        if timezone.now() > expiry_date:
            # delete expired token
            reset_password_token.delete()
            return Response({"status": "expired"}, status=status.HTTP_404_NOT_FOUND)

        # change users password
        if reset_password_token.user.has_usable_password():
            reset_password_token.user.set_password(password)
            reset_password_token.user.save()

        # Delete all password reset tokens for this user
        ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()

        return Response({"status": "OK"})


class ResetPasswordRequestTokenViewSet(AbstractApiView, ViewSet):
    """
    An Api View which provides a method to request a password reset token
    based on an e-mail address
    Sends a signal reset_password_token_created when a reset token was created
    """

    throttle_classes = ()
    permission_classes = []
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = EmailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # before we continue, delete all existing expired tokens
        password_reset_token_validation_time = get_password_reset_token_expiry_time()

        # datetime.now minus expiry hours
        now_minus_expiry_time = timezone.now() - timedelta(
            hours=password_reset_token_validation_time
        )

        # delete all tokens where created_at < now - 24 hours
        ResetPasswordToken.objects.filter(
            created_at__lte=now_minus_expiry_time
        ).delete()

        # find a user by email address (case insensitive search)
        users = User.objects.filter(email__iexact=email)

        active_user_found = False

        # iterate over all users and check if there is any user that is active
        # also check whether the password can be changed (is useable),
        # as there could be users that are not allowed
        # to change their password (e.g., LDAP user)
        for user in users:
            if user.is_active and user.has_usable_password():
                active_user_found = True

        # No active user found, raise a validation error
        if not active_user_found:
            raise ValidationError(
                {
                    "email": ValidationError(
                        gettext_lazy(
                            "There is no active user associated with this e-mail address or the password can not be changed"
                        ),
                        code="invalid",
                    )
                }
            )

        # last but not least: iterate over all users that are active
        # and can change their password
        # and create a Reset Password Token and send a signal with the created token

        for user in users:
            if user.is_active and user.has_usable_password():
                # define the token as none for now
                token = None

                # check if the user already has a token
                if user.password_reset_tokens.all().count() > 0:
                    # yes, already has a token, re-use this token
                    token = user.password_reset_tokens.all()[0]
                else:
                    # no token exists, generate a new token
                    token = ResetPasswordToken.objects.create(
                        user=user,
                        user_agent=request.META["HTTP_USER_AGENT"],
                        ip_address=request.META["REMOTE_ADDR"],
                    )

                link = (
                    f"https://{settings.DOMAIN_NAME}/forgot-password-confirm.html"
                    f"?token={token.key}"
                )

                _l.debug(f"link {link}")

                message = f"Your password reset <a href='{link}'>link</a>"

                subject = "Password reset"
                recipient_list = [user.email]

                send_mail(subject, message, None, recipient_list, html_message=message)

                print(f"token {token.key} ")

        return Response({"status": "OK"})


class UserViewSet(AbstractModelViewSet):
    queryset = User.objects
    serializer_class = UserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentUser,
    ]

    def get_queryset(self):
        qs = super(UserViewSet, self).get_queryset()
        qs = qs.filter(id=self.request.user.id)
        return qs

    def get_object(self):
        return self.request.user

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    @action(
        detail=True,
        methods=("PUT",),
        url_path="set-password",
        serializer_class=UserSetPasswordSerializer,
    )
    def set_password(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()

    @action(
        detail=True,
        methods=("PUT",),
        url_path="unsubscribe",
        serializer_class=UserUnsubscribeSerializer,
    )
    def unsubscribe(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()


class UserMemberViewSet(AbstractModelViewSet):
    queryset = Member.objects
    serializer_class = MemberSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [
        IsMemberFilterBackend,
    ]


class MasterUserViewSet(AbstractModelViewSet):
    queryset = MasterUser.objects.select_related(
        "system_currency",
    )
    serializer_class = MasterUserSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentMasterUser,
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        MasterUserFilter,
        MasterUserBackupsForOwnerOnlyFilter,
    ]
    ordering_fields = [
        "name",
    ]
    pagination_class = BigPagination

    def get_object(self):
        set_st = time.perf_counter()

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        if lookup_value == "0":
            return self.request.user.master_user
        obj = super(MasterUserViewSet, self).get_object()

        _l.debug(f"set_master_user get_object done: {time.perf_counter() - set_st}")

        return obj

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    @staticmethod
    def _save_master_user_data(request, master_user):
        master_user.name = request.data["name"]
        master_user.description = request.data["description"]
        master_user.status = request.data["status"]
        master_user.journal_status = request.data["journal_status"]
        master_user.journal_storage_policy = request.data["journal_storage_policy"]
        master_user.save()

    def update(self, request, *args, **kwargs):
        # Name and Description only available for change

        user = request.user

        try:
            master_user = MasterUser.objects.get(id=request.data["id"])
            member_qs = Member.objects.filter(
                master_user=master_user, user=user, is_admin=True
            )

            if len(list(member_qs)):
                self._save_master_user_data(request, master_user)
            else:
                raise PermissionDenied()

        except MasterUser.DoesNotExist as e:
            raise PermissionDenied() from e

        return Response({"status": "OK"})

    @action(detail=False, methods=["POST"], url_path="update")
    def update_master_user(self, request, *args, **kwargs):
        # Name and Description only available for change

        user = request.user

        try:
            master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

            member_qs = Member.objects.filter(
                master_user=master_user, user=user, is_admin=True
            )

            if len(list(member_qs)):
                master_user.name = request.data["name"]
                master_user.description = request.data["description"]
                master_user.status = request.data["status"]
                master_user.journal_status = request.data["journal_status"]
                master_user.journal_storage_policy = request.data[
                    "journal_storage_policy"
                ]
                master_user.save()
            else:
                raise PermissionDenied()

        except MasterUser.DoesNotExist as e:
            raise PermissionDenied() from e

        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

        serializer = MasterUserSerializer(instance=master_user)

        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="get")
    def get_master_user(self, request, *args, **kwargs):
        master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

        serializer = MasterUserSerializer(instance=master_user)

        return Response(serializer.data)


class MasterUserLightViewSet(AbstractModelViewSet):
    queryset = MasterUser.objects.prefetch_related("members")
    serializer_class = MasterUserLightSerializer
    permission_classes = AbstractModelViewSet.permission_classes + [
        IsCurrentMasterUser,
        SuperUserOrReadOnly,
    ]
    filter_backends = AbstractModelViewSet.filter_backends + [
        MasterUserFilter,
        MasterUserBackupsForOwnerOnlyFilter,
    ]
    ordering_fields = [
        "name",
    ]
    pagination_class = BigPagination

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        if lookup_value == "0":
            return self.request.user.master_user
        return super(MasterUserLightViewSet, self).get_object()

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()


class OtpTokenViewSet(AbstractModelViewSet):
    queryset = OtpToken.objects
    serializer_class = OtpTokenSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByUserFilter]
    ordering_fields = [
        "name",
    ]
    pagination_class = BigPagination

    @action(
        detail=False,
        methods=(
            "PUT",
            "PATCH",
        ),
        url_path="generate-code",
        permission_classes=[IsAuthenticated],
    )
    def generate_code(self, request, pk=None):
        secret = pyotp.random_base32()

        user = request.user

        token_name = f"Two Factor Auth {user.username}"

        token = OtpToken.objects.create(user=user, secret=secret, name=token_name)
        token.save()

        name = user.email or user.username
        totp = pyotp.TOTP(token.secret)

        url = totp.provisioning_uri(name, "finmars.com")

        # u'otpauth://totp/finmars.com:szhitenev?secret=7PXELOEQIHBUKLYS
        # &issuer=finmars.com'

        return Response({"provisioning_uri": url, "token_id": token.id})

    @action(
        detail=False,
        methods=(
            "PUT",
            "PATCH",
        ),
        url_path="validate-code",
        permission_classes=[],
    )
    def validate_code(self, request, pk=None):
        code = request.data["code"]
        username = request.data["username"]
        result = False

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            raise PermissionDenied() from e

        token_id = None
        try:
            token = OtpToken.objects.get(user=user)
            token_id = token.id

            totp = pyotp.TOTP(token.secret)

            if totp.now() == code:
                result = True

        except OtpToken.DoesNotExist:
            result = False

        if result:
            login(request, user)

        return Response({"match": result, "id": token_id})


class EcosystemDefaultViewSet(AbstractModelViewSet):
    queryset = EcosystemDefault.objects.select_related(
        "currency",
        "account_type",
        "account",
        "account__type",
        "counterparty_group",
        "counterparty",
        "counterparty__group",
        "responsible_group",
        "responsible",
        "responsible__group",
        "instrument_type",
        "instrument_type__instrument_class",
        "instrument",
        "instrument__instrument_type",
        "instrument__instrument_type__instrument_class",
        "portfolio",
        "strategy1_group",
        "strategy1_subgroup",
        "strategy1_subgroup__group",
        "strategy1",
        "strategy1__subgroup",
        "strategy1__subgroup__group",
        "strategy2_group",
        "strategy2_subgroup",
        "strategy2_subgroup__group",
        "strategy2",
        "strategy2__subgroup",
        "strategy2__subgroup__group",
        "strategy3_group",
        "strategy3_subgroup",
        "strategy3_subgroup__group",
        "strategy3",
        "strategy3__subgroup",
        "strategy3__subgroup__group",
        "mismatch_portfolio",
        "mismatch_account",
    )
    serializer_class = EcosystemDefaultSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [OwnerByMasterUserFilter]
    ordering_fields = [
        "name",
    ]
    pagination_class = BigPagination


class MemberFilterSet(FilterSet):
    id = NoOpFilter()
    is_deleted = django_filters.BooleanFilter()
    username = CharFilter()
    first_name = CharFilter()
    last_name = CharFilter()
    email = CharFilter()

    class Meta:
        model = Member
        fields = []


class MemberViewSet(AbstractModelViewSet):
    queryset = Member.objects.select_related("user")
    serializer_class = MemberSerializer
    permission_classes = AbstractModelViewSet.permission_classes + []
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = MemberFilterSet
    ordering_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
    ]
    pagination_class = BigPagination

    def list(self, request, *args, **kwargs):
        # Rewriting parent list, we must show deleted members

        queryset = self.filter_queryset(Member.objects.all())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        if lookup_value == "0":
            try:
                return self.request.user.member
            except AttributeError:
                return None

        return super().get_object()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            self.perform_create(serializer)  # try to create member

            member = serializer.instance

            try:
                AuthorizerService().invite_member(member=member, from_user=request.user)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED, headers=headers
                )
            except Exception as err:
                # Authorizer API call failed, rollback the transaction
                transaction.set_rollback(True)

                return self._handle_authorizer_error(request, member, err)

    @staticmethod
    def _handle_authorizer_error(request, member, err):
        params = {
            "base_api_url": settings.BASE_API_URL,
            "username": member.username,
            "is_admin": member.is_admin,
            "from_user_username": request.user.username,
        }
        error_message = (
            f"Could not create/invite member, using params={params}, due to "
            f"Authorizer error={repr(err)}"
        )
        _l.error(f"MemberViewset.create {error_message} trace {traceback.format_exc()}")

        return Response(
            {"error_message": error_message},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def update(self, request, *args, **kwargs):
        member = self.get_object()
        if member.username == "finmars_bot":
            raise PermissionDenied()

        if request.user.member.id != member.id:
            if not request.user.member.is_admin:
                raise PermissionDenied()

            form_data_is_owner = request.data.get("is_owner", False)
            form_data_is_admin = request.data.get("is_admin", False)

            if member.is_owner and form_data_is_owner is False:
                raise ValidationError("Could not remove owner rights from owner")

            if (
                member.is_owner
                and member.is_admin
                and form_data_is_admin is False
            ):
                raise ValidationError("Could not remove admin rights from owner")

        if request.user.member.id == member.id:
            self.validate_member_settings(request)

        return super().update(request, *args, **kwargs)

    @staticmethod
    def validate_member_settings(request):
        status = request.data.get("status", Member.STATUS_ACTIVE)
        if status != Member.STATUS_ACTIVE:
            raise ValidationError("Could not block yourself")

        form_data_is_admin = request.data.get("is_admin", False)
        if request.user.member.is_admin and form_data_is_admin is False:
            raise ValidationError("Could not remove admin rights from yourself")

        form_data_is_owner = request.data.get("is_owner", False)
        if request.user.member.is_owner and form_data_is_owner is False:
            raise ValidationError("Could not remove owner rights from yourself")

    def destroy(self, request, *args, **kwargs):
        if self.get_object().username == "finmars_bot":
            raise PermissionDenied()

        if (
            request.user.member.id != self.get_object().id
            and not request.user.member.is_admin
        ):
            raise PermissionDenied()

        instance = self.get_object()
        self.perform_destroy(instance, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance, request):
        if instance.is_owner:
            raise PermissionDenied()

        authorizer = AuthorizerService()

        authorizer.kick_member(instance)

        instance.status = Member.STATUS_DELETED
        instance.save()

        return super(MemberViewSet, self).perform_destroy(instance)

    @action(detail=True, methods=("PUT",), url_path="send-invite")
    def send_invite(self, request, pk=None):
        member = self.get_object()

        if not member.is_deleted and member.status != Member.STATUS_INVITE_DECLINED:
            raise PermissionDenied()

        member.status = Member.STATUS_INVITED
        member.save()

        authorizer = AuthorizerService()

        authorizer.invite_member(member=member, from_user=request.user)

        return Response({"status": "ok"})


class UsercodePrefixFilterSet(FilterSet):
    id = NoOpFilter()
    value = CharFilter()

    class Meta:
        model = UsercodePrefix
        fields = []


class UsercodePrefixViewSet(AbstractModelViewSet):
    queryset = UsercodePrefix.objects.select_related("master_user")
    serializer_class = UsercodePrefixSerializer
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = UsercodePrefixFilterSet
    ordering_fields = [
        "value",
    ]
    pagination_class = BigPagination


class LeaveMasterUserViewSet(AbstractApiView, ViewSet):
    permission_classes = [IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def retrieve(self, request, pk=None, *args, **kwargs):
        if not request.user.member:
            raise PermissionDenied()

        if request.user.member.is_owner:
            raise PermissionDenied()

        Member.objects.get(user=request.user.id, master_user=pk).delete()

        return Response(status=status.HTTP_200_OK)


class DeleteMasterUserViewSet(
    AbstractApiView,
    ViewSet,
):
    permission_classes = [IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def destroy(self, request, pk=None, *args, **kwargs):
        master_user_id = pk

        if not request.user.member:
            raise PermissionDenied()

        if not request.user.member.is_owner:
            raise PermissionDenied()

        master_user = MasterUser.objects.get(id=master_user_id)

        try:
            Member.objects.get(master_user=master_user_id, user=request.user.id)
        except EcosystemDefault.DoesNotExist as e:
            raise PermissionDenied() from e

        try:
            ecosystem_default = EcosystemDefault.objects.get(master_user=master_user_id)
            ecosystem_default.delete()
        except EcosystemDefault.DoesNotExist:
            print("EcosystemDefault Already deleted")

        Transaction.objects.filter(master_user=master_user_id).delete()
        ComplexTransaction.objects.filter(master_user=master_user_id).delete()

        ComplexImportScheme.objects.filter(master_user=master_user_id).delete()

        Instrument.objects.filter(master_user=master_user_id).delete()
        InstrumentType.objects.filter(master_user=master_user_id).delete()

        transaction_types = TransactionType.objects.filter(master_user=master_user_id)

        TransactionTypeAction.objects.filter(
            transaction_type__in=transaction_types
        ).delete()
        TransactionTypeInput.objects.filter(
            transaction_type__in=transaction_types
        ).delete()

        TransactionType.objects.filter(master_user=master_user_id).delete()

        InstrumentDownloadScheme.objects.filter(master_user=master_user_id).delete()

        Account.objects.filter(master_user=master_user_id).delete()
        AccountType.objects.filter(master_user=master_user_id).delete()
        Currency.objects.filter(master_user=master_user_id).delete()
        Strategy1.objects.filter(master_user=master_user_id).delete()
        Strategy2.objects.filter(master_user=master_user_id).delete()
        Strategy3.objects.filter(master_user=master_user_id).delete()
        Strategy1Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy2Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy3Subgroup.objects.filter(master_user=master_user_id).delete()
        Strategy1Group.objects.filter(master_user=master_user_id).delete()
        Strategy2Group.objects.filter(master_user=master_user_id).delete()
        Strategy3Group.objects.filter(master_user=master_user_id).delete()

        MasterUser.objects.get(id=master_user_id).delete()

        return Response(
            status=status.HTTP_200_OK,
            data={"message": f"Master user {master_user.name} has been deleted."},
        )


class GetCurrentMasterUserViewSet(AbstractViewSet):
    serializer_class = MasterUserSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, pk=None, *args, **kwargs):
        serializer = self.get_serializer(request.user.master_user)

        return Response(serializer.data)
