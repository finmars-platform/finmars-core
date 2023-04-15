import logging
import os
from datetime import date

from django_filters.rest_framework import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response

from poms.celery_tasks.models import CeleryTask
from poms.common.filters import CharFilter
from poms.common.views import AbstractModelViewSet
from poms.configuration.handlers import export_configuration_to_folder
from poms.configuration.models import Configuration
from poms.configuration.serializers import ConfigurationSerializer
from poms.configuration.utils import zip_directory, DeleteFileAfterResponse, save_json_to_file
from poms_app import settings

_l = logging.getLogger('poms.configuration')


class ConfigurationFilterSet(FilterSet):
    name = CharFilter()
    short_name = CharFilter()
    version = CharFilter()

    class Meta:
        model = Configuration
        fields = []


class ConfigurationViewSet(AbstractModelViewSet):
    queryset = Configuration.objects
    serializer_class = ConfigurationSerializer
    filter_class = ConfigurationFilterSet
    filter_backends = AbstractModelViewSet.filter_backends + [

    ]
    permission_classes = AbstractModelViewSet.permission_classes + [

    ]

    @action(detail=True, methods=['get'], url_path='export')
    def export(self, request, pk=None):
        task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type="export_configuration",
        )

        configuration = self.get_object()

        _l.info('configuration %s' % configuration)

        zip_filename = configuration.name + '.zip'
        source_directory = os.path.join(settings.BASE_DIR,
                                        'configurations/' + str(task.id) + '/source')
        output_zipfile = os.path.join(settings.BASE_DIR,
                                      'configurations/' + str(task.id) + '/' + zip_filename)


        export_configuration_to_folder(source_directory, configuration, request.user)

        manifest_filepath = source_directory + '/manifest.json'

        save_json_to_file(manifest_filepath, {
            "name": configuration.name,
            "configuration_code": configuration.configuration_code,
            "version": configuration.version,
            "date": str(date.today()),
        })

        # Create Configuration zip file
        zip_directory(source_directory, output_zipfile)

        response = DeleteFileAfterResponse(open(output_zipfile, 'rb'), content_type='application/zip',
                                           path_to_delete=output_zipfile)
        response['Content-Disposition'] = u'attachment; filename="{filename}'.format(
            filename=zip_filename)

        return response

    @action(detail=True, methods=['get'], url_path='configure')
    def configure(self, request, pk=None):
        configuration = self.get_object()

        # RESPONSE WITH HUGE JSON OF CONFIG, AND USER CAN SELECT WHAT TO DO WITH IT

        return Response({"status": "ok"})
