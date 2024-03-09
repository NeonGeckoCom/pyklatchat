class KlatAPIAuthorizationError(Exception):
    MESSAGE = "Failed to authenticate in klat with provided credentials"

    def __init__(self, message=None):
        message = self.MESSAGE if message is None else message
        super().__init__(message)
