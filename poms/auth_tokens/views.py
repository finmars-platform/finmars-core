import logging

from django.contrib.auth.models import User
from django.utils import translation
from django_filters.filterset import FilterSet
from rest_framework import parsers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.compat import coreapi, coreschema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.schemas import ManualSchema
from rest_framework.schemas import coreapi as coreapi_schema
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from poms.auth_tokens.models import AuthToken, PersonalAccessToken
from poms.auth_tokens.serializers import (
    AcceptInviteSerializer,
    CreateMasterUserSerializer,
    CreateMemberSerializer,
    CreatePersonalAccessTokenSerializer,
    CreateUserSerializer,
    DeleteMemberSerializer,
    MasterUserChangeOwnerSerializer,
    PersonalAccessTokenSerializer,
    RenameMasterUserSerializer,
    SetAuthTokenSerializer,
)
from poms.auth_tokens.utils import generate_random_string
from poms.common.filters import (
    CharFilter,
    NoOpFilter,
)
from poms.common.models import ProxyRequest, ProxyUser
from poms.common.renderers import FinmarsJSONRenderer
from poms.common.views import AbstractModelViewSet
from poms.configuration.utils import get_default_configuration_code
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import MasterUser, Member, UserProfile

_l = logging.getLogger("poms.auth_tokens")


class ObtainAuthToken(APIView):
    throttle_classes = ()
    authentication_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = AuthTokenSerializer

    if coreapi_schema.is_enabled():
        schema = ManualSchema(
            fields=[
                coreapi.Field(
                    name="username",
                    required=True,
                    location="form",
                    schema=coreschema.String(
                        title="Username",
                        description="Valid username for authentication",
                    ),
                ),
                coreapi.Field(
                    name="password",
                    required=True,
                    location="form",
                    schema=coreschema.String(
                        title="Password",
                        description="Valid password for authentication",
                    ),
                ),
            ],
            encoding="application/json",
        )

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = AuthToken.objects.get_or_create(user=user)
        return Response({"token": token.key})


class SetAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = SetAuthTokenSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _l.info(f"serializer.validated_data {serializer.validated_data}")

        # ============= Getting User

        from django.contrib.auth.models import User

        from poms.users.models import UserProfile

        user = None

        try:
            user_profile = UserProfile.objects.get(user_unique_id=serializer.validated_data["user_id"])
            user = user_profile.user
        except UserProfile.DoesNotExist:
            _l.info("Could not find User Profile by UUID")

        if user is None and "user_legacy_id" in serializer.validated_data:
            try:
                user = User.objects.get(id=serializer.validated_data["user_legacy_id"])
            except User.DoesNotExist:
                raise Exception("User does not exist")

        # ====================== Getting Master User and Member

        master_user = None
        member = None

        try:
            master_user = MasterUser.objects.get(
                unique_id=serializer.validated_data["current_master_user_id"]
            )
        except MasterUser.DoesNotExist:
            _l.info("Could not find  Master User by UUID")

        if master_user is None and "current_master_user_legacy_id" in serializer.validated_data:

            try:
                master_user = MasterUser.objects.get(
                    id=serializer.validated_data["current_master_user_legacy_id"]
                )
            except MasterUser.DoesNotExist:
                _l.info("Could not find Master User by Legacy id")
                raise Exception("Master User does not exist")

        if master_user and user:
            member = Member.objects.get(master_user=master_user, user=user)

            # ======================= Generating/Updating Token
            try:
                token = AuthToken.objects.get(key=serializer.validated_data["key"], user=user)
            except AuthToken.DoesNotExist:
                token = AuthToken.objects.create(key=serializer.validated_data["key"], user=user)

            token.current_master_user = master_user
            token.current_member = member

            token.save()

            _l.info("Auth Token is successfully set")

            return Response({"token": token.key})
        else:
            return Response({"token": None})


class CreateUser(APIView):
    throttle_classes = ()
    permission_classes = (AllowAny,)  # TODO add more sophisticated permissions
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    authentication_classes = ()
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = CreateUserSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        from poms.iam.models import Group, Role

        member = Member.objects.get(username="finmars_bot")
        master_user = MasterUser.objects.all().first()

        proxy_user = ProxyUser(member, master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            "request": proxy_request,
            "master_user": master_user,
            "member": member,
        }

        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        email = serializer.validated_data["email"]
        roles = serializer.validated_data["roles"]
        groups = serializer.validated_data["groups"]
        is_admin = serializer.validated_data["is_admin"]

        _l.info(f"Create user validated data {serializer.validated_data}")

        password = generate_random_string(10)
        user = None
        try:
            user = User.objects.get(username=username)

        except User.DoesNotExist:

            try:

                user = User.objects.create(email=email, username=username, password=password)
                user.save()

            except Exception as e:
                _l.info(f"Create user error {e}")

        if user:
            user_profile, created = UserProfile.objects.get_or_create(user_id=user.pk)
            user_profile.save()

        master_user = MasterUser.objects.all().first()

        try:
            member = Member.objects.create(user=user, username=user.username, master_user=master_user)
            member.save()

            roles = roles.split(",")
            groups = groups.split(",")

            roles_instances = Role.objects.filter(user_code__in=roles)
            groups_instances = Group.objects.filter(user_code__in=groups)

            if not len(roles_instances):
                try:

                    configuration_code = get_default_configuration_code()

                    viewer_only_role = Role.objects.get(user_code=f"{configuration_code}:viewer")

                    roles_instances = [viewer_only_role]

                except Exception as e:
                    _l.error("Roles are not set, even default view only is not available")

            member.iam_roles.set(roles_instances)
            member.iam_groups.set(groups_instances)
            member.is_admin = is_admin
            member.save()

        except Exception as e:
            _l.error(f"Could not create member Error {e}")

        return Response({"status": "ok"})


class AcceptInvite(APIView):
    permission_classes = (AllowAny,)  # TODO consider change, maybe add more sophisticated permissions
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    authentication_classes = (JWTAuthentication,)
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = AcceptInviteSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        member = Member.objects.get(username="finmars_bot")
        master_user = MasterUser.objects.all().first()

        proxy_user = ProxyUser(member, master_user)
        proxy_request = ProxyRequest(proxy_user)
        context = {
            "request": proxy_request,
            "master_user": master_user,
            "member": member,
        }

        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        target_member = Member.objects.get(username=username)
        target_member.status = Member.STATUS_ACTIVE
        target_member.is_deleted = False
        target_member.save()

        return Response({"status": "ok"})


class DeclineInvite(APIView):
    permission_classes = (AllowAny,)  # TODO consider change, maybe add more sophisticated permissions
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    authentication_classes = (JWTAuthentication,)
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = AcceptInviteSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        member = Member.objects.get(username="finmars_bot")
        master_user = MasterUser.objects.all().first()

        proxy_user = ProxyUser(member, master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            "request": proxy_request,
            "master_user": master_user,
            "member": member,
        }

        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        target_member = Member.objects.get(username=username)
        target_member.status = Member.STATUS_INVITE_DECLINED
        target_member.save()

        return Response({"status": "ok"})


class CreateMasterUser(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = CreateMasterUserSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        unique_id = serializer.validated_data["unique_id"]
        user_unique_id = serializer.validated_data["user_unique_id"]
        user_profile = UserProfile.objects.get(user_unique_id=user_unique_id)
        user = User.objects.get(id=user_profile.user_id)

        _l.info(f"Create master_user validated data {serializer.validated_data}")

        if "old_backup_name" in serializer.validated_data:
            # If From backup
            master_user = MasterUser.objects.get(name=serializer.validated_data["old_backup_name"])
            master_user.name = name
            master_user.unique_id = unique_id
            master_user.save()
            Member.objects.filter(is_owner=False).delete()

        else:
            master_user = MasterUser.objects.create_master_user(
                user=user, language=translation.get_language(), name=name
            )
            master_user.unique_id = unique_id
            master_user.save()
            member = Member.objects.create(user=user, master_user=master_user, is_owner=True, is_admin=True)
            member.save()
        return Response({"status": "ok"})


class RenameMasterUser(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = RenameMasterUserSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        space_code = kwargs["space_code"]
        master_user = MasterUser.objects.get(space_code=space_code)
        master_user.name = name
        master_user.save()

        return Response({"status": "ok"})


class MasterUserChangeOwner(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = MasterUserChangeOwnerSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_member_username = serializer.validated_data["target_member_username"]
        unique_id = serializer.validated_data["unique_id"]
        master_user = MasterUser.objects.get(unique_id=unique_id)
        members = Member.objects.filter(master_user=master_user)

        for member in members:
            member.is_owner = False
            member.save()

        new_owner_member = Member.objects.get(master_user=master_user, user__username=target_member_username)
        new_owner_member.is_owner = True
        new_owner_member.save()
        return Response({"status": "ok"})


class CreateMember(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = CreateMemberSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        groups = serializer.validated_data["groups"]
        username = serializer.validated_data["username"]
        user, created = User.objects.get_or_create(username=username)
        master_user = MasterUser.objects.all().first()

        try:
            member = Member.objects.create(user=user, username=user.username, master_user=master_user)
            member.save()
            member.is_admin = True
            member.save()

        except Exception as e:
            _l.info(f"Could not create member Error {e}")

        return Response({"status": "ok"})


class DeleteMember(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.JSONParser,
    )
    renderer_classes = [FinmarsJSONRenderer]
    serializer_class = DeleteMemberSerializer

    def get_serializer_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            Member.objects.filter(username=serializer.validated_data["username"]).delete()

        except Exception as e:
            _l.info(f"Could not delete member Error {e}")

        return Response({"status": "ok"})


class PersonalAccessTokenFilterSet(FilterSet):
    id = NoOpFilter()
    user_code = CharFilter()
    name = CharFilter()
    short_name = CharFilter()
    public_name = CharFilter()

    class Meta:
        model = PersonalAccessToken
        fields = []


class PersonalAccessTokenViewSet(AbstractModelViewSet):
    queryset = PersonalAccessToken.objects.select_related(
        "master_user",
        "member",
    )
    serializer_class = PersonalAccessTokenSerializer
    renderer_classes = [FinmarsJSONRenderer]
    filter_backends = AbstractModelViewSet.filter_backends + [
        OwnerByMasterUserFilter,
    ]
    filter_class = PersonalAccessTokenFilterSet
    ordering_fields = [
        "user_code",
        "name",
    ]

    @action(
        detail=False,
        methods=["post"],
        url_path="create-token",
        serializer_class=CreatePersonalAccessTokenSerializer,
    )
    def create_personal_access_token(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            {
                "id": serializer.instance.id,
                "name": serializer.instance.name,
                "user_code": serializer.instance.user_code,
                "expires_at": serializer.instance.expires_at,
                "access_token": serializer.instance.token,
            }
        )
