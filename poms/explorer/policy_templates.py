from copy import deepcopy
from typing import Union

from django.conf import settings

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

FILE_PATH_TEMPLATE = f"frn:{settings.SERVICE_NAME}:explorer:{{fullpath}}"
DIR_PATH_TEMPLATE = f"frn:{settings.SERVICE_NAME}:explorer:{{fullpath}}/*"
FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:update"
FULL_ACCESS = "full"
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
    if access == FULL_ACCESS:
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    if isinstance(obj, FinmarsFile):
        template = FILE_PATH_TEMPLATE
    elif isinstance(obj, FinmarsDirectory):
        template = DIR_PATH_TEMPLATE
    else:
        raise ValueError("Object must be of type FinmarsFile or FinmarsDirectory")

    policy["Statement"][0]["Resource"] = template.format(fullpath=obj.fullpath)

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
    access_policy, created = AccessPolicy.objects.update_or_create(
        user_code=user_code,
        owner=member,
        defaults={"policy": policy, "name": name, "description": description},
    )

    return access_policy


def create_default_access_policy(
    obj: Union[FinmarsFile, FinmarsDirectory]
) -> AccessPolicy:
    member = Member.objects.get(username="finmars_bot")
    return update_or_create_file_access_policy(obj, member, FULL_ACCESS)
