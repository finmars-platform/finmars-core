from rest_framework import routers

import poms.csv_import.views as csv_import

router = routers.DefaultRouter()
router.register(r'csv/scheme', csv_import.SchemeViewSet, 'import_csv_scheme')
router.register(r'csv', csv_import.CsvDataImportViewSet, 'import_csv')
router.register(r'simple-import', csv_import.CsvDataImportViewSet,
                'simpleimportviewset')

