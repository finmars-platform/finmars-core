from django.contrib.auth.models import User
from rest_framework import parsers, renderers

from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.compat import coreapi, coreschema
from rest_framework.response import Response
from rest_framework.schemas import ManualSchema
from rest_framework.schemas import coreapi as coreapi_schema
from rest_framework.views import APIView

from poms.auth_tokens.models import AuthToken

import logging

from poms.auth_tokens.serializers import SetAuthTokenSerializer, CreateUserSerializer, CreateMasterUserSerializer, \
    CreateMemberSerializer
from poms.auth_tokens.utils import generate_random_string
from poms.users.models import MasterUser, Member, UserProfile, Group
from django.utils import translation

_l = logging.getLogger('poms.auth_tokens')


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AuthTokenSerializer

    if coreapi_schema.is_enabled():
        schema = ManualSchema(
            fields=[
                coreapi.Field(
                    name="username",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Username",
                        description="Valid username for authentication",
                    ),
                ),
                coreapi.Field(
                    name="password",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Password",
                        description="Valid password for authentication",
                    ),
                ),
            ],
            encoding="application/json",
        )

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = AuthToken.objects.get_or_create(user=user)
        return Response({'token': token.key})


class SetAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = SetAuthTokenSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _l.info('serializer.validated_data %s' % serializer.validated_data)

        # ============= Getting User

        from poms.users.models import UserProfile
        from django.contrib.auth.models import User

        user = None

        try:
            user_profile = UserProfile.objects.get(user_unique_id=serializer.validated_data['user_id'])
            user = user_profile.user
        except UserProfile.DoesNotExist:
            _l.info("Could not find User Profile by UUID")

        if user is None and 'user_legacy_id' in serializer.validated_data:
            try:
                user = User.objects.get(id=serializer.validated_data['user_legacy_id'])
            except User.DoesNotExist:
                raise Exception("User does not exist")

        # ====================== Getting Master User and Member

        master_user = None
        member = None

        try:
            master_user = MasterUser.objects.get(unique_id=serializer.validated_data['current_master_user_id'])
        except MasterUser.DoesNotExist:
            _l.info("Could not find  Master User by UUID")

        if master_user is None and 'current_master_user_legacy_id' in serializer.validated_data:

            try:
                master_user = MasterUser.objects.get(id=serializer.validated_data['current_master_user_legacy_id'])
            except MasterUser.DoesNotExist:
                _l.info("Could not find Master User by Legacy id")
                raise Exception("Master User does not exist")

        member = Member.objects.get(master_user=master_user, user=user)

        # ======================= Generating/Updating Token

        token = None

        try:
            token = AuthToken.objects.get(key=serializer.validated_data['key'], user=user)
        except AuthToken.DoesNotExist:
            token = AuthToken.objects.create(key=serializer.validated_data['key'], user=user)

        token.current_master_user = master_user
        token.current_member = member

        token.save()

        _l.info("Auth Token is successfully set")

        return Response({'token': token.key})


class CreateUser(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = CreateUserSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        user_unique_id = serializer.validated_data['user_unique_id']

        _l.info('Create user validated data %s' % serializer.validated_data)

        password = generate_random_string(10)

        user = None

        try:
            user = User.objects.get(username=username)

        except User.DoesNotExist:

            try:

                user = User.objects.create(email=email, username=username, password=password)
                user.save()

            except Exception as e:
                _l.info("Create user error %s" % e)

        if user:
            user_profile, created = UserProfile.objects.get_or_create(user_id=user.pk)

            user_profile.user_unique_id = user_unique_id
            user_profile.save()

        return Response({'status': 'ok'})


class CreateMasterUser(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = CreateMasterUserSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        unique_id = serializer.validated_data['unique_id']
        user_unique_id = serializer.validated_data['user_unique_id']

        user_profile = UserProfile.objects.get(user_unique_id=user_unique_id)
        user = User.objects.get(id=user_profile.user_id)

        master_user = MasterUser.objects.create_master_user(
            user=user,
            language=translation.get_language(), name=name)

        master_user.unique_id = unique_id

        master_user.save()

        member = Member.objects.create(user=user, master_user=master_user, is_owner=True, is_admin=True)
        member.save()

        admin_group = Group.objects.get(master_user=master_user, role=Group.ADMIN)
        admin_group.members.add(member.id)
        admin_group.save()

        return Response({'status': 'ok'})


class CreateMember(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = CreateMemberSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        groups = serializer.validated_data['groups']

        user_id = serializer.validated_data['user_id']

        user_legacy_id = None
        if 'user_legacy_id' in serializer.validated_data:
            user_legacy_id = serializer.validated_data['user_legacy_id']

        master_user_id = serializer.validated_data['master_user_id']

        user_legacy_id = None
        if 'master_user_legacy_id' in serializer.validated_data:
            user_legacy_id = serializer.validated_data['master_user_legacy_id']

        user_profile = UserProfile.objects.get(user_unique_id=user_id)
        user = User.objects.get(id=user_profile.user_id)

        master_user = MasterUser.objects.get(unique_id=master_user_id)

        try:
            member = Member.objects.create(user=user, master_user=master_user)
            member.save()

            admin_group = Group.objects.get(master_user=master_user, role=Group.ADMIN)
            admin_group.members.add(member.id)
            admin_group.save()
            member.is_admin = True
            member.save()

            if groups:

                groups_list = groups.split(',')

                for group in groups_list:

                    if group != 'Administrators':
                        group = Group.objects.get(master_user=master_user, role=Group.USER, name=group)
                        group.members.add(member.id)
                        group.save()



        except Exception as e:
            _l.info("Could not create member Error %s" % e)

        return Response({'status': 'ok'})
