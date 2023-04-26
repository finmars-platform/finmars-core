from rest_framework import routers

import poms.accounts.views as accounts

router = routers.DefaultRouter()
router.register(r'account-type-ev-group', accounts.AccountTypeEvGroupViewSet) # DEPRECATED
router.register(r'account-type', accounts.AccountTypeViewSet)
router.register(r'account-type-ev', accounts.AccountTypeEvViewSet) # DEPRECATED
router.register(r'account-type-attribute-type', accounts.AccountTypeAttributeTypeViewSet,
                'accounttypeattributetype')

router.register(r'account-attribute-type', accounts.AccountAttributeTypeViewSet, 'accountattributetype')
router.register(r'account-classifier', accounts.AccountClassifierViewSet, 'accountclassifier')
router.register(r'account-ev-group', accounts.AccountEvGroupViewSet, 'accountevgroup') # DEPRECATED
router.register(r'account-ev', accounts.AccountEvViewSet, 'accountev') # DEPRECATED
router.register(r'account', accounts.AccountViewSet, 'account')
router.register(r'account-light', accounts.AccountLightViewSet, 'accountlight')  # DEPRECATED