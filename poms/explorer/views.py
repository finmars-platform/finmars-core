import json
import logging
import mimetypes
import os

from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import BaseFilterBackend
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.pagination import PageNumberPaginationExt
from poms.common.storage import get_storage
from poms.common.views import AbstractModelViewSet, AbstractViewSet
from poms.explorer.explorer_permission import (
    ExplorerDeletePathPermission,
    ExplorerMovePermission,
    ExplorerReadDirectoryPathPermission,
    ExplorerReadFilePathPermission,
    ExplorerRootAccessPermission,
    ExplorerRootWritePermission,
    ExplorerUnZipPermission,
    ExplorerWriteDirectoryPathPermission,
    ExplorerZipPathsReadPermission,
)
from poms.explorer.models import StorageObject
from poms.explorer.serializers import (
    AccessPolicySerializer,
    BasePathSerializer,
    CopySerializer,
    DeletePathSerializer,
    DirectoryPathSerializer,
    FilePathSerializer,
    MoveSerializer,
    PaginatedResponseSerializer,
    QuerySearchSerializer,
    RenameSerializer,
    ResponseSerializer,
    SearchResultSerializer,
    StorageObjectResourceGroupSerializer,
    TaskResponseSerializer,
    UnZipSerializer,
    ZipFilesSerializer,
)
from poms.explorer.tasks import (
    copy_directory_in_storage,
    move_directory_in_storage,
    rename_directory_in_storage,
    sync_storage_with_database,
    unzip_file_in_storage,
)
from poms.explorer.utils import (
    join_path,
    paginate,
    remove_first_dir_from_path,
    response_with_file,
)
from poms.procedures.handlers import ExpressionProcedureProcess
from poms.procedures.models import ExpressionProcedure
from poms.users.models import Member
from poms_app import settings

_l = logging.getLogger("poms.explorer")

storage = get_storage()


class ContextMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            {
                "storage": storage,
                "space_code": self.request.space_code,
                "realm_code": self.request.realm_code,
            },
        )
        return context


class ExplorerViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerReadDirectoryPathPermission
    ]
    serializer_class = DirectoryPathSerializer
    http_method_names = ["get"]

    @swagger_auto_schema(
        query_serializer=DirectoryPathSerializer(),
        responses={status.HTTP_200_OK: ResponseSerializer()},
    )
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        space_code = request.space_code
        original_path = serializer.validated_data["path"]
        path = f"{join_path(space_code, original_path)}/"

        directories, files = storage.listdir(path)

        members_usernames = set(
            Member.objects.exclude(user=request.user).values_list(
                "user__username", flat=True
            )
        )

        results = [
            {
                "type": "dir",
                "name": dir_name,
            }
            for dir_name in directories
            if path == f"{space_code}/"
            and dir_name not in members_usernames
            or path != f"{space_code}/"
        ]
        for file in files:
            created_at = storage.get_created_time(f"{path}/{file}")
            modified_at = storage.get_modified_time(f"{path}/{file}")
            mime_type, encoding = mimetypes.guess_type(file)

            item = {
                "type": "file",
                "mime_type": mime_type,
                "name": file,
                "created_at": created_at,
                "modified_at": modified_at,
                "file_path": f"/{remove_first_dir_from_path(os.path.join(path, file))}",
                "size": storage.size(f"{path}/{file}"),
                "size_pretty": storage.convert_size(storage.size(f"{path}/{file}")),
            }

            results.append(item)

        page = serializer.validated_data["page"]
        page_size = serializer.validated_data["page_size"]
        api_url = f"{request.build_absolute_uri(location='')}?path={original_path}"
        page_dict = paginate(results, page_size, page, api_url)

        result = {
            "status": "ok",
            "path": path,
            "results": page_dict["items"],
            "count": page_dict["count"],
            "previous": page_dict["previous_url"],
            "next": page_dict["next_url"],
        }
        return Response(PaginatedResponseSerializer(result).data)


class ExplorerViewFileViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerReadFilePathPermission
    ]
    serializer_class = FilePathSerializer
    http_method_names = ["get"]

    @swagger_auto_schema(
        query_serializer=FilePathSerializer(),
        responses={
            status.HTTP_200_OK: openapi.Schema(
                type="string",
                format="binary",
                description="File response",
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        path = join_path(request.space_code, serializer.validated_data["path"])
        if settings.AZURE_ACCOUNT_KEY and path[-1] != "/":
            path = f"{path}/"

        # TODO validate path that either public/import/system or user home directory

        return response_with_file(storage, path)


class ExplorerServerFileViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerReadFilePathPermission
    ]
    serializer_class = FilePathSerializer
    http_method_names = ["get"]

    @swagger_auto_schema(
        query_serializer=FilePathSerializer(),
        responses={
            status.HTTP_200_OK: openapi.Schema(
                type="string",
                format="binary",
                description="File response",
            ),
        },
    )
    def retrieve(self, request, filepath=None, *args, **kwargs):
        serializer = self.get_serializer(data={"path": filepath})
        serializer.is_valid(raise_exception=True)
        if "." not in filepath.split("/")[-1]:
            filepath += ".html"
        path = join_path(request.space_code, serializer.validated_data["path"])

        # TODO validate path that either public/import/system or user home directory

        return response_with_file(storage, path)


class ExplorerUploadViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerWriteDirectoryPathPermission
    ]
    serializer_class = DirectoryPathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=DirectoryPathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = join_path(request.space_code, serializer.validated_data["path"])

        # TODO validate path that either public/import/system or user home directory

        _l.info(f"path {path}")

        files = []
        for file in request.FILES.getlist("file"):
            filepath = f"{path}/{file.name}"

            _l.info(f"going to save {filepath}")

            storage.save(filepath, file)

            files.append(filepath)

        if path == f"{request.space_code}/import":
            try:
                settings_path = f"{request.space_code}/import/.settings.json"

                with storage.open(settings_path) as settings_file:
                    import_settings = json.loads(settings_file.read())

                    procedures = import_settings["on_create"]["expression_procedure"]

                    for item in procedures:
                        _l.info(f"Trying to execute {item}")

                        procedure = ExpressionProcedure.objects.get(user_code=item)

                        instance = ExpressionProcedureProcess(
                            procedure=procedure,
                            master_user=request.user.master_user,
                            member=request.user.member,
                        )
                        instance.process()

            except Exception as e:
                _l.error(f"get file resulted in {repr(e)}")
                result = {"status": "error", "path": path, "details": repr(e)}
                return Response(
                    ResponseSerializer(result).data,
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = {"status": "ok", "path": path, "files": files}
        return Response(ResponseSerializer(result).data)


class ExplorerDeleteViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerDeletePathPermission
    ]
    serializer_class = DeletePathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=DeletePathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        # refactor later, for destroy id is required
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        path = f"{request.space_code}/{serializer.validated_data['path']}"
        is_dir = serializer.validated_data["is_dir"]

        # TODO validate path that either public/import/system or user home directory

        try:
            _l.info(f"going to delete {path}")

            if is_dir:
                storage.delete_directory(path)
            else:
                storage.delete(path)

        except Exception as e:
            _l.error(f"ExplorerDeleteViewSet failed due to {repr(e)}")
            result = {"status": "error", "path": path, "details": repr(e)}
            return Response(
                ResponseSerializer(result).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        else:
            result = {"status": "ok", "path": path}
            return Response(ResponseSerializer(result).data)


class ExplorerCreateFolderViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerRootWritePermission,
    ]
    serializer_class = BasePathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=BasePathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = f"{request.space_code}/{serializer.validated_data['path']}/"

        # TODO validate path that either public/import/system or user home directory

        try:
            # to create folder we have to create system .init file
            init_file_storage_path = f"{path}.init"
            init_file = ContentFile(b"init", name=".init")
            storage.save(init_file_storage_path, init_file)

        except Exception as e:
            _l.error(f"ExplorerCreateFolderViewSet failed due to {repr(e)}")
            result = {"status": "error", "path": path, "details": repr(e)}
            return Response(
                ResponseSerializer(result).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        else:
            result = {"status": "ok", "path": path}
            return Response(ResponseSerializer(result).data)


class ExplorerDeleteFolderViewSet(AbstractViewSet):
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerWriteDirectoryPathPermission
    ]
    serializer_class = DeletePathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=DeletePathSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = join_path(request.space_code, serializer.validated_data["path"])

        _l.info(f"Delete directory {path}")
        try:
            storage.delete_directory(path)
        except Exception as e:
            _l.error(f"ExplorerDeleteFolderViewSet failed due to {repr(e)}")
            result = {"status": "error", "path": path, "details": repr(e)}
            return Response(
                ResponseSerializer(result).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            result = {"status": "ok", "path": path}
            return Response(ResponseSerializer(result).data)


class DownloadAsZipViewSet(AbstractViewSet):
    serializer_class = ZipFilesSerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerZipPathsReadPermission
    ]

    @swagger_auto_schema(
        request_body=ZipFilesSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: openapi.Schema(
                type="string",
                format="binary",
                description="File response",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO validate path that either public/import/system or user home directory

        try:
            zip_file_path = storage.download_paths_as_zip(
                serializer.validated_data["paths"],
            )
        except Exception as e:
            _l.error(f"DownloadAsZipViewSet failed due to {repr(e)}")
            result = {"status": "error", "details": repr(e)}
            return Response(
                ResponseSerializer(result).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            response = FileResponse(
                open(zip_file_path, "rb"),
                content_type="application/zip",
            )
            response["Content-Disposition"] = 'attachment; filename="archive.zip"'
            return response


class DownloadViewSet(AbstractViewSet):
    serializer_class = FilePathSerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerReadFilePathPermission,
    ]

    @swagger_auto_schema(
        request_body=FilePathSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: openapi.Schema(
                type="string",
                format="binary",
                description="File response",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = f"{request.space_code}/{serializer.validated_data['path']}"

        # TODO validate path that either public/import/system or user home directory

        try:
            with storage.open(path, "rb") as file:
                response = FileResponse(file, content_type="application/octet-stream")
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="{os.path.basename(path)}"'

        except Exception as e:
            _l.error(f"DownloadViewSet failed due to {repr(e)}")
            result = {"status": "error", "details": repr(e)}
            return Response(
                ResponseSerializer(result).data,
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return response


class MoveViewSet(ContextMixin, AbstractViewSet):
    serializer_class = MoveSerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerMovePermission,
    ]

    @swagger_auto_schema(
        request_body=MoveSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: TaskResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Move directory in storage",
            type="move_directory_in_storage",
            options_object=serializer.validated_data,
        )

        move_directory_in_storage.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": self.request.space_code,
                    "realm_code": self.request.realm_code,
                },
            }
        )

        return Response(
            TaskResponseSerializer(
                {
                    "status": "ok",
                    "task_id": celery_task.id,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class UnZipViewSet(ContextMixin, AbstractViewSet):
    serializer_class = UnZipSerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerUnZipPermission,
    ]

    @swagger_auto_schema(
        request_body=UnZipSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: TaskResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Unzip file in storage",
            type="unzip_file_in_storage",
            options_object=serializer.validated_data,
        )

        unzip_file_in_storage.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": self.request.space_code,
                    "realm_code": self.request.realm_code,
                },
            }
        )

        return Response(
            TaskResponseSerializer(
                {
                    "status": "ok",
                    "task_id": celery_task.id,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class SyncViewSet(AbstractViewSet):
    http_method_names = ["post"]

    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: TaskResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Sync files with database",
            type="sync_storage_with_database",
            options_object={},
        )

        sync_storage_with_database.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": self.request.space_code,
                    "realm_code": self.request.realm_code,
                },
            }
        )

        return Response(
            TaskResponseSerializer(
                {
                    "status": "ok",
                    "task_id": celery_task.id,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class StorageObjectFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        queries = request.query_params.get("query")
        if not queries:
            return queryset

        options = Q()
        for query in queries.split(","):
            query = query.strip("/")
            options.add(Q(path__icontains=query), Q.OR)

        return queryset.filter(options)


class SearchViewSet(AbstractModelViewSet):
    access_policy = ExplorerRootAccessPermission
    serializer_class = SearchResultSerializer
    queryset = StorageObject.objects.filter(is_file=True)
    pagination_class = PageNumberPaginationExt
    http_method_names = ["get"]
    filter_backends = AbstractModelViewSet.filter_backends + [StorageObjectFilter]

    @swagger_auto_schema(
        query_serializer=QuerySearchSerializer(),
        responses={
            status.HTTP_200_OK: SearchResultSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class StorageObjectResourceGroupViewSet(ContextMixin, AbstractViewSet):
    serializer_class = StorageObjectResourceGroupSerializer
    http_method_names = ["patch"]

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff or not request.user.is_superuser:
            raise PermissionDenied("Only privileged users can perform this action")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_policy = serializer.set_access_policy()

        return Response(
            AccessPolicySerializer(access_policy).data,
            status=status.HTTP_200_OK,
        )


class RenameViewSet(ContextMixin, AbstractViewSet):
    serializer_class = RenameSerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerMovePermission,
    ]

    @swagger_auto_schema(
        request_body=RenameSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: TaskResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Rename directory in storage",
            type="rename_directory_in_storage",
            options_object=serializer.validated_data,
        )

        rename_directory_in_storage.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": self.request.space_code,
                    "realm_code": self.request.realm_code,
                },
            }
        )

        return Response(
            TaskResponseSerializer(
                {
                    "status": "ok",
                    "task_id": celery_task.id,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class CopyViewSet(ContextMixin, AbstractViewSet):
    serializer_class = CopySerializer
    http_method_names = ["post"]
    permission_classes = AbstractViewSet.permission_classes + [
        ExplorerMovePermission,
    ]

    @swagger_auto_schema(
        request_body=CopySerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: TaskResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            verbose_name="Copy directory in storage",
            type="copy_directory_in_storage",
            options_object=serializer.validated_data,
        )

        copy_directory_in_storage.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": self.request.space_code,
                    "realm_code": self.request.realm_code,
                },
            }
        )

        return Response(
            TaskResponseSerializer(
                {
                    "status": "ok",
                    "task_id": celery_task.id,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
