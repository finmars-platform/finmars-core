from copy import deepcopy
from typing import Union

from django.conf import settings

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

FILE_PATH_TEMPLATE = f"frn:{settings.SERVICE_NAME}:explorer:{{filepath}}"
DIR_PATH_TEMPLATE = f"frn:{settings.SERVICE_NAME}:explorer:{{path}}/*"
FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:update"
READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                f"{settings.SERVICE_NAME}:explorer:retrieve",
            ],
            "Effect": "Allow",
            "Resource": "",
            "Principal": "*",
        }
    ],
}


def create_policy(obj: Union[FinmarsFile, FinmarsDirectory], access: str) -> dict:
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
    if access == "full":
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    if isinstance(obj, FinmarsFile):
        policy["Statement"][0]["Resource"] = FILE_PATH_TEMPLATE.format(
            filepath=obj.fullpath
        )
    elif isinstance(obj, FinmarsDirectory):
        policy["Statement"][0]["Resource"] = DIR_PATH_TEMPLATE.format(path=obj.path)
    else:
        raise ValueError("Object must be of type FinmarsFile or FinmarsDirectory")

    return policy


def update_or_create_file_access_policy(
    obj: Union[FinmarsFile, FinmarsDirectory], member: Member, access: str
) -> AccessPolicy:
    configuration_code = get_default_configuration_code()
    user_code = (
        f"{configuration_code}:{settings.SERVICE_NAME}"
        f":explorer:{obj.policy_name}-{access}"
    )
    policy = create_policy(obj, access)
    name = obj.policy_name
    description = f"{name} : {access} access policy"
    access_policy, created = AccessPolicy.objects.get_or_create(
        user_code=user_code,
        owner=member,
        name=name,
        defaults={"policy": policy, "description": description},
    )

    return access_policy


def create_default_access_policy(
    obj: Union[FinmarsFile, FinmarsDirectory]
) -> AccessPolicy:
    member = Member.objects.get(username="finmars_bot")
    return update_or_create_file_access_policy(obj, member, "full")
