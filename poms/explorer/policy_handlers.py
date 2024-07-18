import logging
from copy import deepcopy
from typing import Union

from django.conf import settings

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import AccessLevel, FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

StorageObject = Union[FinmarsFile, FinmarsDirectory]

_l = logging.getLogger("poms.explorer")

RESOURCE = f"frn:{settings.SERVICE_NAME}:explorer:{{resource}}"

FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:{AccessLevel.FULL}"
READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                f"{settings.SERVICE_NAME}:explorer:{AccessLevel.READ}",
            ],
            "Effect": "Allow",
            "Resource": "",
            "Principal": "*",
        }
    ],
}


def validate_obj_and_access(obj: StorageObject, access: str):
    if not isinstance(obj, StorageObject):
        raise ValueError("Object must be FinmarsFile or FinmarsDirectory")

    AccessLevel.validate_level(access)


def create_policy(obj: StorageObject, access: str = AccessLevel.READ) -> dict:
    """
    A function that creates a policy dict based on the type of
    object (file or directory) and the access level.
    Parameters:
        obj (Union[FinmarsFile, FinmarsDirectory]): The object to create the policy for.
        access (str): The level of access, either 'full' or another value.
    Returns:
        dict: The generated policy based on the object and access level.
    """

    policy = deepcopy(READ_ACCESS_POLICY)
    if access == AccessLevel.FULL:
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    policy["Statement"][0]["Resource"] = RESOURCE.format(resource=obj.path)

    return policy


def get_default_owner() -> Member:
    return Member.objects.get(username="finmars_bot")


def get_or_create_storage_access_policy(
    obj: StorageObject, member: Member, access: str
) -> AccessPolicy:
    validate_obj_and_access(obj, access)

    configuration_code = get_default_configuration_code()
    policy_user_code = obj.policy_user_code(access)
    name = obj.path
    policy = create_policy(obj, access)
    description = f"{name} : {access} access policy"
    access_policy, created = AccessPolicy.objects.get_or_create(
        user_code=policy_user_code,
        owner=get_default_owner(),
        defaults={
            "configuration_code": configuration_code,
            "policy": policy,
            "name": name,
            "description": description,
        },
    )
    access_policy.members.add(member)

    _l.info(
        f"AccessPolicy {access_policy.pk} created, resource={obj.path} "
        f"member={member.username} access={access}"
    )
    return access_policy


def verify_access_policy(member: Member, obj: StorageObject, access: str):
    AccessLevel.validate_level(access)
    object_policies = AccessPolicy.objects.filter(
        owner=get_default_owner(),
        user_code=obj.policy_user_code(access),
        members=member,
    )
    resource = obj.path
    # TODO validate path against policies
    return
