class FinmarsBaseException(Exception):
    def __init__(self, error_key: str, message: str = "", status_code: int = 500):
        """
        A custom exception for Finmars with an obligatory error_key property.

        :param error_key: A unique string key identifying the error.
        :param args: Additional arguments passed to the base Exception class.
        """
        super().__init__(message)
        self.error_key = error_key
        self.status_code = status_code

    def __str__(self):
        """
        Returns a string representation of the exception, including the error key.
        """
        return super().__str__()
        # return f"{self.__class__.__name__}(error_key={self.error_key}, message={super().__str__()})"

    def __repr__(self):
        return super().__str__()
