from src.auth.schema_examples import UNAUTHORIZED, VALIDATION_ERROR
from src.auth.schemas import FAILURE_EXAMPLE

CREATE_PROJECT_RESPONSES = {
    # 201 & 422 by default
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

UPDATE_PROJECT_RESPONSES = {
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
                            "message": "You can only update your own projects",
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
                        "message": "Project with slug '<slug>' not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}


DELETE_PROJECT_RESPONSES = {
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
                            "message": "You can only delete your own projects",
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
                        "message": "Project with slug '<slug>' not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}

CREATE_REVIEW_RESPONSES = {
    # 201 by default
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
                            "message": "You cannot review your own project",
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
                        "message": "Project with slug '<slug>' not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
    422: {
        "content": {
            "application/json": {
                "examples": {
                    "review_exists": {
                        "value": {
                            "status": "failure",
                            "message": "You have already reviewed this project",
                            "err_code": "unprocessable_entity",
                        },
                    },
                    "validation_error": VALIDATION_ERROR,
                }
            }
        },
    },
}

CREATE_REVIEW_RESPONSES = {
    # 200 & 422 by default
    404: {
        "content": {
            "application/json": {
                "examples": {
                    "value": {
                        "status": FAILURE_EXAMPLE,
                        "message": "Project with slug '<slug>' not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}

ADD_TAGS_PROJECT_RESPONSES = {
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
                            "message": "You can only add tags to your own projects",
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
                        "message": "Project with slug '<slug>' not found",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
    422: {
        "content": {
            "application/json": {
                "examples": {
                    "review_exists": {
                        "value": {
                            "status": "failure",
                            "message": "No valid tags provided",
                            "err_code": "unprocessable_entity",
                        },
                    },
                    "validation_error": VALIDATION_ERROR,
                }
            }
        },
    },
}

REMOVE_TAGS_PROJECT_RESPONSES = {
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
                            "message": "You can only remove tags from your own projects",
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
                    "message": "Project with slug '<slug>' not found",
                    "err_code": "not_found",
                }
            }
        }
    },
    422: {
        "content": {
            "application/json": {
                "examples": {
                    "review_exists": {
                        "value": {
                            "status": "failure",
                            "message": "No valid tags provided",
                            "err_code": "unprocessable_entity",
                        },
                    },
                    "validation_error": VALIDATION_ERROR,
                }
            }
        },
    },
}

GET_ALL_TAGS_RESPONSES = {
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

GET_RELATED_PROJECTS_RESPONSES = {
    # 200 by default
    404: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Project with slug '<slug>' not found",
                    "err_code": "not_found",
                }
            }
        }
    },
}
