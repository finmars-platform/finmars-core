from copy import deepcopy
from typing import Union

from poms.explorer.models import FinmarsFile, FinmarsDirectory

FILE_PATH_TEMPLATE = "frn:finmars:explorer:{filepath}"
DIR_PATH_TEMPLATE = "frn:finmars:explorer:{path}/*"
FULL_ACTION = "finmars:explorer:update"
READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                "finmars:explorer:retrieve",
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
            filepath=obj.filepath
        )
    elif isinstance(obj, FinmarsDirectory):
        policy["Statement"][0]["Resource"] = DIR_PATH_TEMPLATE.format(path=obj.path)
    else:
        raise ValueError("Object must be of type FinmarsFile or FinmarsDirectory")

    return policy
