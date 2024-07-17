from copy import deepcopy
from typing import List, Union
import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import FULL, READ, FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

StorageObject = Union[FinmarsFile, FinmarsDirectory]

_l = logging.getLogger("poms.explorer")

RESOURCE = f"frn:{settings.SERVICE_NAME}:explorer:{{resource}}"

FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:{FULL}"
READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                f"{settings.SERVICE_NAME}:explorer:{READ}",
            ],
            "Effect": "Allow",
            "Resource": "",
            "Principal": "*",
        }
    ],
}


def validate_obj_access(obj: StorageObject, access: str):
    if not isinstance(obj, StorageObject):
        raise ValueError("Object must be a FinmarsFile or FinmarsDirectory")
    if access not in {READ, FULL}:
        raise ValueError(f"Access must be either '{READ}' or '{FULL}'")


def create_policy(obj: StorageObject, access: str = READ) -> dict:
    """
    A function that creates a policy dict based on the type of
    object (file or directory) and the access level.
    Parameters:
        obj (Union[FinmarsFile, FinmarsDirectory]): The object to create the policy for.
        access (str): The level of access, either 'full' or another value.
    Returns:
        dict: The generated policy based on the object and access level.
    """
    validate_obj_access(obj, access)

    policy = deepcopy(READ_ACCESS_POLICY)
    if access == FULL:
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    policy["Statement"][0]["Resource"] = RESOURCE.format(resource=obj.resource)

    return policy


def upsert_storage_obj_access_policy(obj: StorageObject, owner: Member, access: str):
    validate_obj_access(obj, access)

    configuration_code = get_default_configuration_code()
    user_code = f"{obj.policy_user_code()}-{access}"
    name = obj.resource
    policy = create_policy(obj, access)
    description = f"{name} : {access} access policy"
    AccessPolicy.objects.update_or_create(
        user_code=user_code,
        owner=owner,
        defaults={
            "configuration_code": configuration_code,
            "policy": policy,
            "name": name,
            "description": description,
        },
    )


def create_default_storage_access_policies():
    owner = Member.objects.get(username="finmars_bot")
    for directory in FinmarsDirectory.objects.all().iterator():
        upsert_storage_obj_access_policy(directory, owner, FULL)
        upsert_storage_obj_access_policy(directory, owner, READ)

    for file in FinmarsFile.objects.all().iterator():
        upsert_storage_obj_access_policy(file, owner, FULL)
        upsert_storage_obj_access_policy(file, owner, READ)


def add_user_to_storage_obj_policy(obj: StorageObject, user: Member, access: str):
    validate_obj_access(obj, access)
    user_code = f"{obj.policy_user_code()}-{access}"

    try:
        access_policy = AccessPolicy.objects.filter(user_code=user_code).first()
    except AccessPolicy.DoesNotExist:
        _l.error(f"No AccessPolicy for user_code={user_code}")
        raise

    access_policy.members.add(user)


def get_member_explorer_policies(member: Member) -> List[AccessPolicy]:
    """
    Get all AccessPolicy objects for the member from cache or db
    Args:
        member:
    Returns:
        list of AccessPolicy objects
    """

    cache_key = f"member_access_policies_{member.id}"
    access_policies = cache.get(cache_key)

    if access_policies is None:
        access_policies = (
            AccessPolicy.objects.filter(
                Q(members=member)
                | Q(iam_roles__members=member)
                | Q(iam_groups__members=member)
            )
            .filter(
                user_code__contains=":explorer:",
            )
            .distinct()
        )

        # Cache the result for a specific duration (e.g., 5 minutes)
        cache.set(cache_key, access_policies, settings.ACCESS_POLICY_CACHE_TTL)

    return access_policies


def verify_access_policy(member: Member, obj: StorageObject, access: str):
    # TODO load all 'explorer' policies for the user
    # TODO validate path against policies
    return AccessPolicy.objects.filter(user_code=obj.policy_user_code()).exists()
