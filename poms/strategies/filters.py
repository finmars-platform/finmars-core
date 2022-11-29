# class SubgroupOwnerByGroupUserFilter(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         master_user = request.user.master_user
#         return queryset.filter(group__master_user=master_user)
#
#
# class StrategyOwnerBySubgroupUserFilter(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         master_user = request.user.master_user
#         return queryset.filter(subgroup__group__master_user=master_user)
#
