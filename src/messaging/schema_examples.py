from src.auth.schema_examples import UNAUTHORIZED
from src.auth.utils import FAILURE_EXAMPLE

GET_USER_MESSAGES_RESPONSES = {
    # 200 & 422 shows by default
    401: UNAUTHORIZED,
    404: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Profile not found",
                    "err_code": "not_found",
                }
            }
        }
    },
}


GET_MESSAGE_RESPONSES = {
    # 200 & 422 by default
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "examples": {
                    "account_disabled": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Your account has been disabled. Please contact support for assistance",
                            "err_code": "insufficient_permission",
                        },
                    },
                    "account_not_verified": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Account not verified.",
                            "err_code": "account_not_verified",
                        }
                    },
                    "permission_denied": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "You can only read your own messages",
                            "err_code": "insufficient_permission",
                        },
                    },
                }
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "examples": {
                    "value": {
                        "status": FAILURE_EXAMPLE,
                        "message": "Message not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}


MARK_MESSAGE_RESPONSES = {
    # 200 & 422 by default
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "examples": {
                    "account_disabled": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Your account has been disabled. Please contact support for assistance",
                            "err_code": "insufficient_permission",
                        },
                    },
                    "account_not_verified": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Account not verified.",
                            "err_code": "account_not_verified",
                        }
                    },
                    "permission_denied": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "You can only mark your own messages as unread",
                            "err_code": "insufficient_permission",
                        },
                    },
                }
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Message not found",
                    "err_code": "not_found",
                }
            }
        }
    },
}

GET_UNREAD_COUNT_RESPONSES = {
    # 200 by default
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "examples": {
                    "account_disabled": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Your account has been disabled. Please contact support for assistance",
                            "err_code": "insufficient_permission",
                        }
                    },
                    "account_not_verified": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Account not verified.",
                            "err_code": "account_not_verified",
                        }
                    },
                }
            }
        }
    },
}

DELETE_RESPONSES = {
    # 204 & 422 by default
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "examples": {
                    "account_disabled": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Your account has been disabled. Please contact support for assistance",
                            "err_code": "insufficient_permission",
                        },
                    },
                    "account_not_verified": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Account not verified.",
                            "err_code": "account_not_verified",
                        }
                    },
                    "permission_denied": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "You can only delete your own messages",
                            "err_code": "insufficient_permission",
                        },
                    },
                }
            }
        }
    },
}
