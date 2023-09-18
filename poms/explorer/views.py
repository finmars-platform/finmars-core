import json
import logging
import mimetypes
import os
import traceback
from tempfile import NamedTemporaryFile

from django.http import FileResponse
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from poms.common.views import AbstractViewSet
from poms.explorer.serializers import ExplorerSerializer
from poms.procedures.handlers import ExpressionProcedureProcess
from poms.procedures.models import ExpressionProcedure
from poms.users.models import Member
from poms_app import settings

_l = logging.getLogger('poms.explorer')

from poms.common.storage import get_storage

storage = get_storage()


class ExplorerViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def remove_first_folder_from_path(self, path):
        split_path = path.split(os.path.sep)
        new_path = os.path.sep.join(split_path[1:])
        return new_path

    def list(self, request):

        path = request.query_params.get('path')

        if not path:
            path = settings.BASE_API_URL + '/'
        else:
            if path[0] == '/':
                path = settings.BASE_API_URL + path
            else:
                path = settings.BASE_API_URL + '/' + path

        if path[-1] != '/':
            path = path + '/'

        items = storage.listdir(path)

        results = []

        for dir in items[0]:

            if path == settings.BASE_API_URL + '/':

                members_usernames = Member.objects.exclude(user=request.user).values_list('user__username', flat=True)

                if dir not in members_usernames:
                    results.append({
                        'type': 'dir',
                        'name': dir
                    })

            else:

                results.append({
                    'type': 'dir',
                    'name': dir
                })

        for file in items[1]:
            created = storage.get_created_time(path + '/' + file)
            modified = storage.get_modified_time(path + '/' + file)

            mime_type, encoding = mimetypes.guess_type(file)

            item = {
                'type': 'file',
                'mime_type': mime_type,
                'name': file,
                'created': created,
                'modified': modified,
                'file_path': '/' + self.remove_first_folder_from_path(os.path.join(path, file)),
                # path already has / in end of str
                'size': storage.size(path + '/' + file),
                'size_pretty': storage.convert_size(storage.size(path + '/' + file))
            }

            results.append(item)

        return Response({
            "path": path,
            "results": results
        })


class ExplorerViewFileViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def list(self, request):

        try:

            path = request.query_params.get('path')

            if not path:
                raise ValidationError("Path is required")
            else:
                if path[0] == '/':
                    path = settings.BASE_API_URL + path
                else:
                    path = settings.BASE_API_URL + '/' + path

            if settings.AZURE_ACCOUNT_KEY:
                if path[-1] != '/':
                    path = path + '/'

            # TODO validate path that eiher public/import/system or user home folder

            with storage.open(path, 'rb') as file:

                result = file.read()

                file_content_type = None

                if '.txt' in file.name:
                    file_content_type = 'plain/text'

                if '.csv' in file.name:
                    file_content_type = 'text/csv'

                if '.json' in file.name:
                    file_content_type = 'application/json'

                if '.yml' in file.name or '.yaml' in file.name:
                    file_content_type = 'application/yaml'

                if '.py' in file.name:
                    file_content_type = 'text/x-python'

                if '.png' in file.name:
                    file_content_type = 'image/png'

                if '.jp' in file.name:
                    file_content_type = 'image/jpeg'

                if '.pdf' in file.name:
                    file_content_type = 'application/pdf'

                if '.doc' in file.name:
                    file_content_type = 'application/msword'

                if '.doc' in file.name:
                    file_content_type = 'application/msword'

                if '.xls' in file.name:
                    file_content_type = 'application/vnd.ms-excel'

                if '.xlsx' in file.name:
                    file_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

                # if file_content_type:
                #     response = FileResponse(result, content_type=file_content_type)
                # else:
                #     response = FileResponse(result)

                if file_content_type:
                    response = HttpResponse(result, content_type=file_content_type)
                else:
                    response = HttpResponse(result)

            return response

        except Exception as e:
            _l.error('view file error %s' % e)
            _l.error('view file traceback %s' % traceback.format_exc())
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


from bs4 import BeautifulSoup


def sanitize_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for script in soup(["script", "style"]):  # Remove these tags
        script.extract()

    return str(soup)


class ExplorerServeFileViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def retrieve(self, request, filepath=None):

        _l.info('ExplorerServeFileViewSet.filepath %s' % filepath)
        filepath = filepath.rstrip('/')

        if not '.' in filepath.split('/')[-1]:  # if the file does not have an extension
            filepath += '.html'

        path = settings.BASE_API_URL + '/' + filepath

        # TODO validate path that eiher public/import/system or user home folder

        _l.info('path %s' % path)

        with storage.open(path, 'rb') as file:

            result = file.read()

            file_content_type = None

            if '.html' in file.name:
                file_content_type = 'text/html'
                # result = sanitize_html(result)

            if '.txt' in file.name:
                file_content_type = 'plain/text'

            if '.js' in file.name:
                file_content_type = 'text/javascript'

            if '.csv' in file.name:
                file_content_type = 'text/csv'

            if '.json' in file.name:
                file_content_type = 'application/json'

            if '.yml' in file.name or '.yaml' in file.name:
                file_content_type = 'application/yaml'

            if '.py' in file.name:
                file_content_type = 'text/x-python'

            if '.png' in file.name:
                file_content_type = 'image/png'

            if '.jp' in file.name:
                file_content_type = 'image/jpeg'

            if '.pdf' in file.name:
                file_content_type = 'application/pdf'

            if '.doc' in file.name:
                file_content_type = 'application/msword'

            if '.doc' in file.name:
                file_content_type = 'application/msword'

            if '.css' in file.name:
                file_content_type = 'text/css'

            if '.xls' in file.name:
                file_content_type = 'application/vnd.ms-excel'

            if '.xlsx' in file.name:
                file_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            # if file_content_type:
            #     response = FileResponse(result, content_type=file_content_type)
            # else:
            #     response = FileResponse(result)

            if file_content_type:
                response = HttpResponse(result, content_type=file_content_type)
            else:
                response = HttpResponse(result)

        return response


class ExplorerUploadViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):

        _l.info('request %s' % request.data)

        path = request.data['path']

        if not path:
            path = settings.BASE_API_URL
        else:
            if path[0] == '/':
                path = settings.BASE_API_URL + path
            else:
                path = settings.BASE_API_URL + '/' + path

        # TODO validate path that eiher public/import/system or user home folder

        for file in request.FILES.getlist('file'):
            _l.info('f %s' % file)

            filepath = path + '/' + file.name

            _l.info('going to save %s' % filepath)

            # Possibly deprecated
            # try:
            #
            #     storage.delete(filepath)
            #
            #     _l.info("File exist, going to delete")
            #
            # except Exception as e:
            #     _l.info("File is not exists, going to create")

            storage.save(filepath, file)

        _l.info('path %s' % path)

        if path == settings.BASE_API_URL + '/import':

            try:

                settings_path = settings.BASE_API_URL + '/import/.settings.json'

                with storage.open(settings_path) as file:

                    import_settings = json.loads(file.read())

                    procedures = import_settings['on_create']['expression_procedure']

                    for item in procedures:
                        _l.info("Trying to execute %s" % item)

                        procedure = ExpressionProcedure.objects.get(user_code=item)

                        instance = ExpressionProcedureProcess(procedure=procedure, master_user=request.user.master_user,
                                                              member=request.user.member)
                        instance.process()

            except Exception as e:
                _l.error("Could not import anything %s" % e)

        return Response({
            'status': 'ok'
        })


class ExplorerDeleteViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):  # refactor later, for destroy id is required

        path = request.query_params.get('path')
        is_dir = request.query_params.get('is_dir')

        # TODO validate path that eiher public/import/system or user home folder

        if is_dir == 'true':
            is_dir = True
        else:
            is_dir = False

        if not path:
            raise ValidationError("Path is required")
        elif path == '/':
            raise ValidationError("Could not remove root folder")
        else:
            path = settings.BASE_API_URL + '/' + path

        if path == settings.BASE_API_URL + '/.system/':
            raise PermissionDenied('Could not remove .system folder')

        try:
            _l.info('going to delete %s' % path)

            if is_dir:
                storage.delete_directory(path)

            storage.delete(path)
        except Exception as e:
            _l.error("ExplorerDeleteViewSet.e %s" % e)
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExplorerCreateFolderViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):

        path = request.data.get('path')

        # TODO validate path that eiher public/import/system or user home folder

        if not path:
            raise ValidationError("Path is required")
        else:
            path = settings.BASE_API_URL + '/' + path + '/.init'

        with NamedTemporaryFile() as tmpf:

            tmpf.write(b'')
            tmpf.flush()
            storage.save(path, tmpf)

        return Response({
            "path": path
        })


class ExplorerDeleteFolderViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):

        path = request.data.get('path')

        # TODO validate path that eiher public/import/system or user home folder

        if not path:
            raise ValidationError("Path is required")
        else:
            if path[0] == '/':
                path = settings.BASE_API_URL + path
            else:
                path = settings.BASE_API_URL + '/' + path

        _l.info("Delete directory %s" % path)

        storage.delete_directory(path)

        return Response({
            "status": 'ok'
        })


class DownloadAsZipViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):
        paths = request.data.get('paths')

        # TODO validate path that eiher public/import/system or user home folder

        if not paths:
            raise ValidationError("paths is required")

        zip_file_path = storage.download_paths_as_zip(paths)

        # Serve the zip file as a response
        response = FileResponse(open(zip_file_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="archive.zip"'

        return response


class DownloadViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):
        path = request.data.get('path')

        # TODO validate path that eiher public/import/system or user home folder

        if not path:
            raise ValidationError("path is required")

        _l.info('path %s' % path)

        path = settings.BASE_API_URL + '/' + path

        # Serve the zip file as a response
        # Serve the file as a response
        with storage.open(path, 'rb') as file:
            response = FileResponse(file, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(path)}"'

        return response
