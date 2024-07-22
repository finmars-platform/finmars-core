import logging
from copy import deepcopy
from typing import Optional, Union

from django.conf import settings

from poms.configuration.utils import get_default_configuration_code
from poms.explorer.models import DIR_SUFFIX, AccessLevel, FinmarsDirectory, FinmarsFile
from poms.iam.models import AccessPolicy
from poms.users.models import Member

StorageObject = Union[FinmarsFile, FinmarsDirectory]

_l = logging.getLogger("poms.explorer")

RESOURCE = f"frn:{settings.SERVICE_NAME}:explorer:{{resource}}"

FULL_ACTION = f"{settings.SERVICE_NAME}:explorer:{AccessLevel.WRITE}"
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
    if access == AccessLevel.WRITE:
        policy["Statement"][0]["Action"].append(FULL_ACTION)

    policy["Statement"][0]["Resource"] = RESOURCE.format(resource=obj.path)

    return policy


def get_default_owner() -> Member:
    return Member.objects.get(username="finmars_bot")


def get_or_create_storage_access_policy(
    obj: StorageObject, member: Member, access: str
) -> AccessPolicy:
    """
    Creates or retrieves a storage access policy for a given object, member,
    and access level.

    Parameters:
        obj (StorageObject): The storage object for which the access policy is created.
        member (Member): The member for whom the access policy is created.
        access (str): The level of access for the policy.

    Returns:
        AccessPolicy: The created or retrieved access policy.
    """

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


def get_or_create_access_policy_to_path(
    path: str, member: Member, access: str
) -> AccessPolicy:
    """
    Retrieves or creates an access policy for a given path, member, and access level.

    Parameters:
        path (str): The path for which the access policy is retrieved or created.
        member (Member): The member for whom the access policy is created.
        access (str): The level of access for the policy.

    Returns:
        AccessPolicy: The retrieved or created access policy.
    """
    if path.endswith(DIR_SUFFIX):
        obj = FinmarsDirectory.objects.get(path=path)
    else:
        obj = FinmarsFile.objects.get(path=path)

    return get_or_create_storage_access_policy(obj=obj, member=member, access=access)


def check_obj_access(
    obj: StorageObject, owner: Member, member: Member, access: str
) -> Optional[bool]:
    """
    Check if a member has access to the specific object based on the access level.

    Parameters:
        obj (StorageObject): The object for which access needs to be checked.
        owner (Member): The default owner of the object.
        member (Member): The member whose access is being checked.
        access (str): The level of access to check.

    Returns:
        Optional[bool]: True if the member has access, False if the member has
        no access to the object or its parents,
        and None if the object has parent(s) access to which has to checked.
    """
    AccessLevel.validate_level(access)
    obj_access_policy = AccessPolicy.objects.filter(
        owner=owner,
        user_code=obj.policy_user_code(access),
        members=member,
    ).first()
    if obj_access_policy:
        _l.info(f"{member.username} has {access} access to {obj.path}")
        return True

    if not obj.parent:
        _l.info(f"{member.username} has no {access} access to {obj.path} (no parent)")
        return False

    return None  # storage object has parent(s)


def member_has_access(obj: StorageObject, member: Member, access: str) -> bool:
    """
    A function that determines if a member has access to a specific object
    or any of his parents based on the access level.

    Parameters:
        obj (StorageObject): The object for which access needs to be checked.
        member (Member): The member whose access is being checked.
        access (str): The level of access to check.

    Returns:
        bool: True if the member has access, False otherwise.
    """
    owner = get_default_owner()

    has_access = check_obj_access(obj, owner, member, access)
    if has_access is not None:
        return has_access

    parents = obj.parent.get_ancestors(include_self=True)
    policy_user_codes = [parent.policy_user_code(access) for parent in parents]
    obj_access_policy = AccessPolicy.objects.filter(
        owner=owner,
        user_code__in=policy_user_codes,
        members=member,
    ).first()

    if obj_access_policy:
        _l.info(f"{member.username} has {access} access to parent of {obj.path}")
        return True

    _l.info(f"{member.username} has no {access} access to any parent of {obj.path}")
    return False


def member_has_access_to_path(path: str, member: Member, access: str) -> bool:
    """
    A function that determines if a member has access to a specific path
    based on the access level.

    Parameters:
        path (str): The path for which access needs to be checked.
        member (Member): The member whose access is being checked.
        access (str): The level of access to check.

    Returns:
        bool: True if the member has access, False otherwise.
    """
    try:
        if path.endswith(DIR_SUFFIX):
            obj = FinmarsDirectory.objects.get(path=path)
        else:
            obj = FinmarsFile.objects.get(path=path)
    except (FinmarsFile.DoesNotExist, FinmarsDirectory.DoesNotExist):
        _l.info(f"{member.username} has no {access} access to {path} (not found)")
        return False

    return member_has_access(obj, member, access)
