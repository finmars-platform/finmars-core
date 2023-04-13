


class BookException(Exception):
    code: int
    error_message: str

    def __init__(self, code: int, error_message: str):

        self.code = code
        self.error_message = error_message


class BookSkipException(Exception):
    code: int
    error_message: str

    def __init__(self, code: int, error_message: str):

        self.code = code
        self.error_message = error_message
