from copy import deepcopy
from typing import Union

from django.conf import settings

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import FULL_ACCESS, READ_ACCESS, FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

RESOURCE = f"frn:{settings.SERVICE_NAME}:explorer:{{resource}}"

FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:{FULL_ACCESS}"
READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                f"{settings.SERVICE_NAME}:explorer:{READ_ACCESS}",
            ],
            "Effect": "Allow",
            "Resource": "",
            "Principal": "*",
        }
    ],
}


def validate_obj_access(obj: Union[FinmarsFile, FinmarsDirectory], access: str):
    if not (isinstance(obj, FinmarsFile) or isinstance(obj, FinmarsDirectory)):
        raise ValueError("Object must be a FinmarsFile or FinmarsDirectory")
    if access not in [READ_ACCESS, FULL_ACCESS]:
        raise ValueError(f"Access must be either '{READ_ACCESS}' or '{FULL_ACCESS}'")


def create_policy(
    obj: Union[FinmarsFile, FinmarsDirectory],
    access: str = READ_ACCESS,
) -> dict:
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
    if access == FULL_ACCESS:
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    policy["Statement"][0]["Resource"] = RESOURCE.format(resource=obj.resource)

    return policy


def upsert_storage_obj_access_policy(
    obj: Union[FinmarsFile, FinmarsDirectory], owner: Member, access: str
) -> AccessPolicy:
    validate_obj_access(obj, access)

    configuration_code = get_default_configuration_code()
    user_code = obj.policy_user_code()
    name = obj.resource
    policy = create_policy(obj, access)
    description = f"{name} : {access} access policy"
    access_policy, created = AccessPolicy.objects.update_or_create(
        user_code=user_code,
        owner=owner,
        defaults={
            "configuration_code": configuration_code,
            "policy": policy,
            "name": name,
            "description": description,
        },
    )

    return access_policy


def create_default_access_policy(
    obj: Union[FinmarsFile, FinmarsDirectory]
) -> AccessPolicy:
    owner = Member.objects.get(username="finmars_bot")
    return upsert_storage_obj_access_policy(obj, owner, FULL_ACCESS)
