from rest_framework import routers

import poms.strategies.views as strategies

router = routers.DefaultRouter()

router.register(
    "1/group",
    strategies.Strategy1GroupViewSet,
    "group1",
)
router.register(
    "1/subgroup",
    strategies.Strategy1SubgroupViewSet,
    "subgroup1",
)
router.register(
    "1/strategy",
    strategies.Strategy1ViewSet,
    "strategy1",
)
router.register(
    "1/strategy-attribute-type",
    strategies.Strategy1AttributeTypeViewSet,
    "strategy_attribute_type_1",
)
router.register(
    "2/group",
    strategies.Strategy2GroupViewSet,
    "group2",
)
router.register(
    "2/subgroup",
    strategies.Strategy2SubgroupViewSet,
    "subgroup2",
)
router.register(
    "2/strategy",
    strategies.Strategy2ViewSet,
    "strategy2",
)
router.register(
    "2/strategy-attribute-type",
    strategies.Strategy2AttributeTypeViewSet,
    "strategy_attribute_type_2",
)
router.register(
    "3/group",
    strategies.Strategy3GroupViewSet,
    "group3",
)
router.register(
    "3/subgroup",
    strategies.Strategy3SubgroupViewSet,
    "subgroup3",
)
router.register(
    "3/strategy",
    strategies.Strategy3ViewSet,
    "strategy3",
)
router.register(
    "3/strategy-attribute-type",
    strategies.Strategy3AttributeTypeViewSet,
    "strategy_attribute_type_3",
)
