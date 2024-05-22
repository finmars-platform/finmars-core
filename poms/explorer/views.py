import json
import logging
import mimetypes
import os
from tempfile import NamedTemporaryFile

from django.http import FileResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from poms.common.storage import get_storage
from poms.common.views import AbstractViewSet
from poms.explorer.serializers import (
    DeletePathSerializer,
    FilePathSerializer,
    FolderPathSerializer,
    MoveSerializer,
    ResponseSerializer,
    ZipFilesSerializer,
)
from poms.explorer.utils import (
    join_path,
    remove_first_folder_from_path,
    response_with_file,
    move_file,
    move_folder,
path_is_file,
)
from poms.procedures.handlers import ExpressionProcedureProcess
from poms.procedures.models import ExpressionProcedure
from poms.users.models import Member
from poms_app import settings

_l = logging.getLogger("poms.explorer")


storage = get_storage()


class ExplorerViewSet(AbstractViewSet):
    serializer_class = FolderPathSerializer
    http_method_names = ["get"]

    @swagger_auto_schema(
        query_serializer=FolderPathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
        },
    )
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        space_code = request.space_code
        path = f"{join_path(space_code, serializer.validated_data['path'])}/"

        directories, files = storage.listdir(path)

        members_usernames = Member.objects.exclude(user=request.user).values_list(
            "user__username", flat=True
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
            created = storage.get_created_time(f"{path}/{file}")
            modified = storage.get_modified_time(f"{path}/{file}")

            mime_type, encoding = mimetypes.guess_type(file)

            item = {
                "type": "file",
                "mime_type": mime_type,
                "name": file,
                "created": created,
                "modified": modified,
                "file_path": f"/{remove_first_folder_from_path(os.path.join(path, file))}",
                "size": storage.size(f"{path}/{file}"),
                "size_pretty": storage.convert_size(storage.size(f"{path}/{file}")),
            }

            results.append(item)

        result = {"status": "ok", "path": path, "results": results}
        return Response(ResponseSerializer(result).data)


class ExplorerViewFileViewSet(AbstractViewSet):
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

        # TODO validate path that either public/import/system or user home folder

        return response_with_file(storage, path)


class ExplorerServeFileViewSet(AbstractViewSet):
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

        # TODO validate path that either public/import/system or user home folder

        return response_with_file(storage, path)


class ExplorerUploadViewSet(AbstractViewSet):
    serializer_class = FolderPathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=FolderPathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = join_path(request.space_code, serializer.validated_data["path"])

        # TODO validate path that either public/import/system or user home folder

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

        # TODO validate path that either public/import/system or user home folder

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
    serializer_class = FilePathSerializer
    http_method_names = ["post"]

    @swagger_auto_schema(
        request_body=FilePathSerializer(),
        responses={
            status.HTTP_200_OK: ResponseSerializer(),
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        path = f"{request.space_code}/{serializer.validated_data['path']}/.init"

        # TODO validate path that either public/import/system or user home folder

        try:
            with NamedTemporaryFile() as tmpf:
                tmpf.write(b"")
                tmpf.flush()
                storage.save(path, tmpf)

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

        # TODO validate path that either public/import/system or user home folder

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

        # TODO validate path that either public/import/system or user home folder

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


class MoveViewSet(AbstractViewSet):
    serializer_class = MoveSerializer
    http_method_names = ["post"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            {
                "storage": storage,
                "space_code": self.request.space_code,
            },
        )
        return context

    @swagger_auto_schema(
        request_body=MoveSerializer(),
        responses={
            status.HTTP_400_BAD_REQUEST: ResponseSerializer(),
            status.HTTP_200_OK: ResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        directories = []
        files = []
        for item in serializer.validated_data["items"]:
            if path_is_file(storage, item):
                files.append(item)
            else:
                directories.append(item)

        destination_folder = serializer.validated_data["target_directory_path"]
        for directory in directories:
            move_folder(storage, directory, destination_folder)

        for file in files:
            move_file(storage, file, destination_folder)

        return Response(ResponseSerializer({"status": "ok"}).data)
