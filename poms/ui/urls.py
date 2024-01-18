from rest_framework import routers

import poms.ui.views as ui

router = routers.DefaultRouter()
router.register(
    r"portal-interface-access",
    ui.PortalInterfaceAccessViewSet,
)
router.register(
    r"list-layout",
    ui.ListLayoutViewSet,
)
router.register(
    r"template-layout",
    ui.TemplateLayoutViewSet,
)
router.register(
    r"dashboard-layout",
    ui.DashboardLayoutViewSet,
)
router.register(
    r"member-layout",
    ui.MemberLayoutViewSet,
)
router.register(
    r"mobile-layout",
    ui.MobileLayoutViewSet,
)
router.register(
    r"draft",
    ui.DraftViewSet,
)
router.register(
    r"edit-layout",
    ui.EditLayoutViewSet,
)
router.register(
    r"bookmark",
    ui.BookmarkViewSet,
)
router.register(
    r"configuration-export-layout",
    ui.ConfigurationExportLayoutViewSet,
)
router.register(
    r"complex-transaction-user-field",
    ui.ComplexTransactionUserFieldViewSet,
)
router.register(
    r"transaction-user-field",
    ui.TransactionUserFieldViewSet,
)
router.register(
    r"instrument-user-field",
    ui.InstrumentUserFieldViewSet,
)
router.register(
    r"entity-tooltip",
    ui.EntityTooltipViewSet,
)
router.register(
    r"context-menu-layout",
    ui.ContextMenuLayoutViewSet,
)
router.register(
    r"color-palette",
    ui.ColorPaletteViewSet,
)
router.register(
    r"cross-entity-attribute-extension",
    ui.CrossEntityAttributeExtensionViewSet,
)
router.register(
    r"column-sort-data",
    ui.ColumnSortDataViewSet,
)
router.register(
    r"system-attributes",
    ui.SystemAttributesViewSet,
    basename="System attributes",
)

# DEPRECATED
router.register(
    r"list-layout-light",
    ui.ListLayoutLightViewSet,
)
