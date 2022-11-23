from enum import Enum


class Error(Enum):
    SESSION_NOT_AUTHORIZED = 20
    PARAMETERS_ERROR = 21
    NOT_INITIALIZED = 22
    SYSTEM_ERROR = 99
    USER_NOT_FOUND = 101
    TRANSACTION_DATA_NOT_FOUND = 104
    NOT_ENTITLED_TO_GAME = 120
    INVALID_PASSWORD = 122
    ALREADY_REGISTERED = 160
    CODE_ALREADY_USED = 180
    CODE_NOT_FOUND = 181
    TOS_OUT_OF_DATE = 260
    RECORD_NOT_FOUND = 5000


class TransactionSkip:
    pass


class TransactionError:

    errorCode: int
    localizedMessage: str
    errorContainer: dict

    def __init__(self, error: Error, container: dict = {}):
        self.errorCode = error.value
        self.localizedMessage = self.__get_localized_message(error)
        self.errorContainer = container

    @staticmethod
    def __get_localized_message(error: Error):
        match error:
            case Error.PARAMETERS_ERROR:
                return "The required parameters for this call are missing or invalid"
            case Error.NOT_INITIALIZED:
                return "The client did not send up the initial hello packet"
            case Error.ALREADY_REGISTERED:
                return "That account name is already taken"
            case Error.INVALID_PASSWORD:
                return "The password the user specified is incorrect"
            case Error.TOS_OUT_OF_DATE:
                return "The TOS Content is out of date."
            case Error.NOT_ENTITLED_TO_GAME:
                return "The user is not entitled to access this game"
            case Error.CODE_ALREADY_USED:
                return "That code has already been used"
            case Error.USER_NOT_FOUND:
                return "The user was not found"
            case Error.SYSTEM_ERROR:
                return "System Error"
            case Error.CODE_NOT_FOUND:
                return "The code is not valid for registering this game"
            case Error.SESSION_NOT_AUTHORIZED:
                return "Session Not Authorized"
            case Error.TRANSACTION_DATA_NOT_FOUND:
                return "The data necessary for this transaction was not found"
            case Error.RECORD_NOT_FOUND:
                return "Record not found"
