FILE_PATH_TEMPLATE = "frn:finmars:explorer:{path}/{name}.{extension}"

FILE_FULL_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                "finmars:explorer:retrieve",
                "finmars:explorer:update",
            ],
            "Effect": "Allow",
            "Resource": FILE_PATH_TEMPLATE,
            "Principal": "*",
        }
    ],
}

FILE_READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                "finmars:explorer:retrieve",
            ],
            "Effect": "Allow",
            "Resource": FILE_PATH_TEMPLATE,
            "Principal": "*",
        }
    ],
}

DIR_PATH_TEMPLATE = "frn:finmars:explorer:{path}/*"

DIR_FULL_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                "finmars:explorer:retrieve",
                "finmars:explorer:update",
            ],
            "Effect": "Allow",
            "Resource": DIR_PATH_TEMPLATE,
            "Principal": "*",
        }
    ],
}

DIR_READ_ACCESS_POLICY = {
    "Version": "2023-01-01",
    "Statement": [
        {
            "Action": [
                "finmars:explorer:retrieve",
            ],
            "Effect": "Allow",
            "Resource": DIR_PATH_TEMPLATE,
            "Principal": "*",
        }
    ],
}
