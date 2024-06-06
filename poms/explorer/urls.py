from rest_framework import routers

import poms.explorer.views as explorer

router = routers.DefaultRouter()

router.register(
    r"explorer",
    explorer.ExplorerViewSet,
    "explorer",
)
router.register(
    r"view",
    explorer.ExplorerViewFileViewSet,
    "explorer_view",
)
router.register(
    r"upload",
    explorer.ExplorerUploadViewSet,
    "explorer_upload",
)
router.register(
    r"delete",
    explorer.ExplorerDeleteViewSet,
    "explorer_delete",
)
router.register(
    r"create-folder",
    explorer.ExplorerCreateFolderViewSet,
    "explorer_create_folder",
)
router.register(
    r"delete-folder",
    explorer.ExplorerDeleteFolderViewSet,
    "explorer_delete_folder",
)
router.register(
    r"download-as-zip",
    explorer.DownloadAsZipViewSet,
    "download_as_zip",
)
router.register(
    r"download",
    explorer.DownloadViewSet,
    "explorer_download",
)
router.register(
    r"move",
    explorer.MoveViewSet,
    "explorer_move",
)
router.register(
    r"unzip",
    explorer.UnZipViewSet,
    "explorer_unzip",
)
