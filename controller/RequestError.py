# a generic RequestError Exception


class RequestError(Exception):
    def __init__(self, errorCode, message):
        self.message = message
        self.errorCode = errorCode
