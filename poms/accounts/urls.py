from rest_framework import routers

import poms.accounts.views as accounts

router = routers.DefaultRouter()
router.register(r'account', accounts.AccountViewSet, 'account')
router.register(r'account-attribute-type', accounts.AccountAttributeTypeViewSet, 'accountattributetype')
router.register(r'account-classifier', accounts.AccountClassifierViewSet, 'accountclassifier')


router.register(r'account-type', accounts.AccountTypeViewSet)
router.register(r'account-type-attribute-type', accounts.AccountTypeAttributeTypeViewSet,
                'accounttypeattributetype')


