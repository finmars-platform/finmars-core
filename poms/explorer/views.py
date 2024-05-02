import json
import logging
import mimetypes
import os
import traceback
from tempfile import NamedTemporaryFile

from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from poms.common.storage import get_storage
from poms.common.views import AbstractViewSet
from poms.explorer.serializers import ExplorerSerializer
from poms.explorer.utils import (
    define_content_type,
    join_path,
    remove_first_folder_from_path,
)
from poms.procedures.handlers import ExpressionProcedureProcess
from poms.procedures.models import ExpressionProcedure
from poms.users.models import Member
from poms_app import settings

_l = logging.getLogger("poms.explorer")


storage = get_storage()


class ExplorerViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        path = serializer.validated_data["path"]

        space_code = request.space_code

        path = join_path(space_code, path) if path else f"{space_code}/"

        if path[-1] != "/":
            path = f"{path}/"

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

        return Response({"path": path, "results": results})


class ExplorerViewFileViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def list(self, request, *args, **kwargs):
        path = request.query_params.get("path")

        try:
            if not path:
                raise ValidationError("Path is required")

            path = join_path(request.space_code, path)

            if settings.AZURE_ACCOUNT_KEY and path[-1] != "/":
                path = f"{path}/"

            # TODO validate path that either public/import/system or user home folder

            with storage.open(path, "rb") as file:
                result = file.read()
                file_content_type = define_content_type(file.name)
                response = (
                    HttpResponse(result, content_type=file_content_type)
                    if file_content_type
                    else HttpResponse(result)
                )

            return response

        except Exception as e:
            _l.error(f"view file error {repr(e)} trace {traceback.format_exc()}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExplorerServeFileViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def retrieve(self, request, filepath=None, *args, **kwargs):
        _l.info(f"ExplorerServeFileViewSet.filepath {filepath}")
        filepath = filepath.rstrip("/")

        # check if the file does not have an extension
        if "." not in filepath.split("/")[-1]:
            filepath += ".html"

        path = f"{request.space_code}/{filepath}"

        # TODO validate path that either public/import/system or user home folder

        _l.info(f"path {path}")

        with storage.open(path, "rb") as file:
            result = file.read()
            file_content_type = define_content_type(file.name)
            response = (
                HttpResponse(result, content_type=file_content_type)
                if file_content_type
                else HttpResponse(result)
            )

        return response


class ExplorerUploadViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        _l.info(f"request {request.data}")

        path = request.data["path"]

        path = join_path(request.space_code, path) if path else request.space_code

        # TODO validate path that either public/import/system or user home folder

        _l.info(f"path {path}")

        for file in request.FILES.getlist("file"):
            _l.info(f"file {file} from request list ")

            filepath = f"{path}/{file.name}"

            _l.info(f"going to save {filepath}")

            storage.save(filepath, file)

        if path == f"{request.space_code}/import":
            try:
                settings_path = f"{request.space_code}/import/.settings.json"

                with storage.open(settings_path) as file:
                    import_settings = json.loads(file.read())

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
                _l.error(f"Could not import anything due to {repr(e)}")

        return Response({"status": "ok"})


class ExplorerDeleteViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        # refactor later, for destroy id is required
        path = request.query_params.get("path")
        is_dir = request.query_params.get("is_dir") == "true"

        # TODO validate path that either public/import/system or user home folder

        if not path:
            raise ValidationError("Path is required")
        elif path == "/":
            raise ValidationError("Could not remove root folder")
        else:
            path = f"{request.space_code}/{path}"

        if path == f"{request.space_code}/.system/":
            raise PermissionDenied("Could not remove .system folder")

        try:
            _l.info(f"going to delete {path}")

            if is_dir:
                storage.delete_directory(path)

            storage.delete(path)
        except Exception as e:
            _l.error(f"ExplorerDeleteViewSet failed due to {repr(e)}")

        return Response(status=status.HTTP_204_NO_CONTENT)


class ExplorerCreateFolderViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        path = request.data.get("path")

        # TODO validate path that either public/import/system or user home folder

        if not path:
            raise ValidationError("Path is required")
        else:
            path = f"{request.space_code}/{path}/.init"

        with NamedTemporaryFile() as tmpf:
            tmpf.write(b"")
            tmpf.flush()
            storage.save(path, tmpf)

        return Response({"path": path})


class ExplorerDeleteFolderViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        path = request.data.get("path")

        if not path:
            raise ValidationError("Path is required")

        path = join_path(request.space_code, path)

        _l.info(f"Delete directory {path}")

        storage.delete_directory(path)

        return Response({"status": "ok"})


class DownloadAsZipViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        paths = request.data.get("paths")

        # TODO validate path that either public/import/system or user home folder

        if not paths:
            raise ValidationError("paths is required")

        zip_file_path = storage.download_paths_as_zip(paths)

        # Serve the zip file as a response
        response = FileResponse(
            open(zip_file_path, "rb"), content_type="application/zip"
        )
        response["Content-Disposition"] = 'attachment; filename="archive.zip"'

        return response


class DownloadViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request, *args, **kwargs):
        path = request.data.get("path")

        # TODO validate path that either public/import/system or user home folder

        if not path:
            raise ValidationError("path is required")

        _l.info(f"path {path}")

        path = f"{request.space_code}/{path}"

        # Serve the zipped file or file as a response
        with storage.open(path, "rb") as file:
            response = FileResponse(file, content_type="application/octet-stream")
            response[
                "Content-Disposition"
            ] = f'attachment; filename="{os.path.basename(path)}"'

        return response
