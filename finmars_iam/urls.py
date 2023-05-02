from rest_framework import routers

import finmars_iam.views as iam

router = routers.DefaultRouter()
router.register(r'role', iam.RoleViewSet, 'role')
router.register(r'group', iam.GroupViewSet, 'group')
router.register(r'access-policy-template', iam.AccessPolicyTemplateViewSet, 'accessPolicyTemplate')



