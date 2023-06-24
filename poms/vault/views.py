import logging
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from poms.common.views import AbstractViewSet
from poms.vault.serializers import VaultSecretSerializer, VaultEngineSerializer, VaultStatusSerializer, \
    GetVaultSecretSerializer, DeleteVaultEngineSerializer, DeleteVaultSecretSerializer
from rest_framework.decorators import action

from poms.vault.vault import FinmarsVault
from poms_app import settings

_l = logging.getLogger('poms.vault')


class VaultStatusViewSet(AbstractViewSet):
    serializer_class = VaultStatusSerializer

    def list(self, request):

        data = {}

        if settings.VAULT_TOKEN:
            data['status'] = 'ok'
            data['text'] = 'Vault is operational for storing secrets'
        else:
            data['status'] = 'unknown'
            data['text'] = 'Vault is not configured for this Space'

        serializer = VaultStatusSerializer(data)

        return Response(serializer.data)

class VaultSecretViewSet(AbstractViewSet):
    serializer_class = VaultSecretSerializer


class VaultEngineViewSet(AbstractViewSet):
    serializer_class = VaultEngineSerializer

    def list(self, request):
        finmars_vault = FinmarsVault()

        data = finmars_vault.get_list_engines()

        return Response(data)

    @swagger_auto_schema(
        request_body=VaultEngineSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response("Vault engine created successfully"),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response("Internal server error"),
        }
    )
    @action(detail=False, methods=['post'], url_path="create", serializer_class=VaultEngineSerializer)
    def create_engine(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine_name = serializer.validated_data['engine_name']

        finmars_vault = FinmarsVault()

        try:
            finmars_vault.create_engine(engine_name)
            return Response({"message": "Vault engine created successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path="delete", serializer_class=DeleteVaultEngineSerializer)
    def delete_engine(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine_name = serializer.validated_data['engine_name']

        finmars_vault = FinmarsVault()

        try:
            finmars_vault.delete_engine(engine_name)
            return Response({"message": "Vault engine deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class VaultSecretViewSet(AbstractViewSet):
    serializer_class = VaultSecretSerializer

    def list(self, request):

        engine_name = request.query_params.get('engine_name')

        if not engine_name:
            return Response({'error': 'engine_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        finmars_vault = FinmarsVault()

        data = finmars_vault.get_list_secrets(engine_name)

        return Response(data)

    @swagger_auto_schema(
        request_body=VaultSecretSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response("Vault secret created successfully"),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response("Internal server error"),
        }
    )
    @action(detail=False, methods=['post'], url_path="create", serializer_class=VaultSecretSerializer)
    def create_secret(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine_name = serializer.validated_data['engine_name']
        path = serializer.validated_data['path']
        data = serializer.validated_data['data']

        finmars_vault = FinmarsVault()

        try:
            finmars_vault.create_secret(engine_name, path, data)
            return Response({"message": "Vault secret created successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['put'], url_path="update", serializer_class=VaultSecretSerializer)
    def update_secret(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine_name = serializer.validated_data['engine_name']
        path = serializer.validated_data['path']
        data = serializer.validated_data['data']

        finmars_vault = FinmarsVault()

        try:
            finmars_vault.update_secret(engine_name, path, data)
            return Response({"message": "Vault secret update successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        method='get',
        responses={200: VaultSecretSerializer}
    )
    @action(detail=False, methods=['get'], url_path="get", serializer_class=GetVaultSecretSerializer)
    def get_secret(self, request):
        engine_name = request.query_params.get('engine_name')
        path = request.query_params.get('path')

        if not engine_name or not path:
            return Response({'error': 'engine_name and path are required'}, status=status.HTTP_400_BAD_REQUEST)

        finmars_vault = FinmarsVault()

        try:
            result = finmars_vault.get_secret(engine_name, path)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path="delete", serializer_class=DeleteVaultSecretSerializer)
    def delete_secret(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine_name = serializer.validated_data['engine_name']
        path = serializer.validated_data['path']

        finmars_vault = FinmarsVault()

        try:
            finmars_vault.delete_secret(engine_name, path)
            return Response({"message": "Vault secret deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)