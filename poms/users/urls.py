from rest_framework import routers

import poms.users.views as users

router = routers.DefaultRouter()

router.register(
    r"ping",
    users.PingViewSet,
    "ping",
)
router.register(
    r"user",
    users.UserViewSet,
)
# Deprecated
# router.register(
#     r"user-member",
#     users.UserMemberViewSet,
#     "usermember",
# )
router.register(
    r"master-user",
    users.MasterUserViewSet,
)
router.register(
    r"master-user-light",
    users.MasterUserLightViewSet,
    "masteruserlight",
)  # Deprecated at all, no light-method needed
# Deprecated
# router.register(
#     r"get-current-master-user",
#     users.GetCurrentMasterUserViewSet,
#     "getcurrentmasteruser",
# )
router.register(
    r"member",
    users.MemberViewSet,
)
# router.register(r'group', users.GroupViewSet)
# router.register(
#     r"group",
#     iam.GroupViewSet,
# )
# router.register(
#     r"language",
#     api.LanguageViewSet,
#     "language",
# )
# router.register(
#     r"timezone",
#     api.TimezoneViewSet,
#     "timezone",
# )

router.register(
    r"ecosystem-default",
    users.EcosystemDefaultViewSet,
    "ecosystemdefault",
)
router.register(
    r"usercode-prefix",
    users.UsercodePrefixViewSet,
    "usercodeprefix",
)
