import json
import logging
import os
from tempfile import NamedTemporaryFile
from django.http import HttpResponse

from django.http import FileResponse
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

from poms.common.storage import get_storage, delete_folder, download_folder_as_zip

storage = get_storage()


class ExplorerViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

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

            item = {
                'type': 'file',
                'name': file,
                'file_path': path + file, # path already has / in end of str
                'size': storage.size(path + '/' + file),
            }

            try:
                item['last_modified']: storage.modified_time(path + '/' + file)
            except Exception as e:
                _l.error("Modfied date is not avaialbel")

            results.append(item)

        return Response({
            "path": path,
            "results": results
        })


class ExplorerViewFileViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def list(self, request):

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

            try:

                storage.delete(filepath)

                _l.info("File exist, going to delete")

            except Exception as e:
                _l.info("File is not exists, going to create")

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
        else:
            path = settings.BASE_API_URL + '/' + path

        if path == settings.BASE_API_URL + '/.system/':
            raise PermissionDenied('Could not remove .system folder')

        try:
            _l.info('going to delete %s' % path)

            if is_dir:
                storage.delete(path + '/.init')

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
            path = settings.BASE_API_URL + '/' + path

        delete_folder(path)

        return Response({
            "status": 'ok'
        })


class DownloadFolderAsZipViewSet(AbstractViewSet):
    serializer_class = ExplorerSerializer

    def create(self, request):

        path = request.data.get('path')

        # TODO validate path that eiher public/import/system or user home folder

        if not path:
            raise ValidationError("Path is required")
        else:
            path = settings.BASE_API_URL + '/' + path

        zip_file_path = download_folder_as_zip(path)

        # Serve the zip file as a response
        response = FileResponse(open(zip_file_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="archive.zip"'

        return response



