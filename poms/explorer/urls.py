from rest_framework import routers

import poms.explorer.views as explorer

router = routers.DefaultRouter()
router.register(r'explorer', explorer.ExplorerViewSet, 'explorer')
router.register(r'view', explorer.ExplorerViewFileViewSet, 'explorerView')
router.register(r'upload', explorer.ExplorerUploadViewSet, 'explorerUpload')
router.register(r'delete', explorer.ExplorerDeleteViewSet, 'explorerDelete')
router.register(r'create-folder', explorer.ExplorerCreateFolderViewSet, 'explorerCreateFolder')
router.register(r'delete-folder', explorer.ExplorerDeleteFolderViewSet, 'explorerDeleteFolder')
router.register(r'download-as-zip', explorer.DownloadAsZipViewSet, 'downloadAsZip')
