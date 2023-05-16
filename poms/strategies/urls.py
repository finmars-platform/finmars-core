from rest_framework import routers

import poms.strategies.views as strategies

router = routers.DefaultRouter()
router.register(r'1/group', strategies.Strategy1GroupViewSet)

router.register(r'1/subgroup', strategies.Strategy1SubgroupViewSet)
router.register(r'1/strategy', strategies.Strategy1ViewSet, 'strategy1')
router.register(r'1/strategy-attribute-type', strategies.Strategy1AttributeTypeViewSet)

router.register(r'2/group', strategies.Strategy2GroupViewSet)
router.register(r'2/subgroup', strategies.Strategy2SubgroupViewSet)
router.register(r'2/strategy', strategies.Strategy2ViewSet, 'strategy2')
router.register(r'2/strategy-attribute-type', strategies.Strategy2AttributeTypeViewSet)

router.register(r'3/group', strategies.Strategy3GroupViewSet)
router.register(r'3/subgroup', strategies.Strategy3SubgroupViewSet)
router.register(r'3/strategy', strategies.Strategy3ViewSet, 'strategy3')
router.register(r'3/strategy-attribute-type', strategies.Strategy3AttributeTypeViewSet)



