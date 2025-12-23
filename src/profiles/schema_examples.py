from src.auth.schema_examples import UNAUTHORIZED, VALIDATION_ERROR
from src.auth.schemas import (
    EMAIL_EXAMPLE,
    FAILURE_EXAMPLE,
    SUCCESS_EXAMPLE,
    UUID_EXAMPLE,
)

PROFILE_RES_EX = {
    "id": UUID_EXAMPLE,
    "email": EMAIL_EXAMPLE,
    "first_name": "John",
    "last_name": "Doe",
    "username": "johndoe",
    "short_intro": "Full-stack developer passionate about building scalable web applications",
    "bio": "I'm a software engineer with 5+ years of experience in Python, JavaScript, and cloud technologies.",
    "location": "San Francisco, CA",
    "avatar_url": "https://example.com/avatars/johndoe.jpg",
    "github": "https://github.com/johndoe",
    "stack_overflow": "https://stackoverflow.com/users/12345/johndoe",
    "tw": "https://twitter.com/johndoe",
    "ln": "https://linkedin.com/in/johndoe",
    "website": "https://johndoe.dev",
    "skills": [
        {
            "id": UUID_EXAMPLE,
            "name": "Python",
            "description": "Expert level proficiency in Python development",
        },
        {
            "id": UUID_EXAMPLE,
            "name": "FastAPI",
            "description": "Advanced knowledge of FastAPI framework",
        },
    ],
}

GET_USER_PROFILE_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": SUCCESS_EXAMPLE,
                    "message": "Profile retrieved successfully",
                    "data": PROFILE_RES_EX,
                }
            }
        }
    },
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


UPDATE_PROFILE_RESPONSES = {
    # 422 by default
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": SUCCESS_EXAMPLE,
                    "message": "Profile updated successfully",
                    "data": PROFILE_RES_EX,
                }
            }
        }
    },
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

DELETE_AVATAR_RESPONSES = {
    # 204 by default
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


GET_USER_PROFILE_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": SUCCESS_EXAMPLE,
                    "message": "Profile retrieved successfully",
                    "data": PROFILE_RES_EX,
                }
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Profile for user '<username>' not found",
                    "err_code": "not_found",
                }
            }
        }
    },
}

UPDATE_USER_PROFILE_RESPONSES = {
    # 422 by default
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": SUCCESS_EXAMPLE,
                    "message": "Profile retrieved successfully",
                    "data": PROFILE_RES_EX,
                }
            }
        }
    },
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

UPLOAD_AVATAR_RESPONSES = {
    # 200 and 422 by default
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


ADD_SKILL_RESPONSES = {
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
    422: {
        "content": {
            "application/json": {
                "examples": {
                    "skill_exists": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Skill 'Python' already exists in your profile",
                            "err_code": "unprocessable_entity",
                        }
                    },
                    "validation_error": VALIDATION_ERROR,
                }
            }
        }
    },
}

GET_USER_SKILLS_RESPONSES = {
    # 200 anddd 422 by default
    404: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Profile for user '<username>' not found",
                    "err_code": "not_found",
                }
            }
        }
    },
}


UPDATE_SKILL_RESPONSES = {
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
    404: {
        "content": {
            "application/json": {
                "example": {
                    "value": {
                        "status": FAILURE_EXAMPLE,
                        "message": "Skill not found in profile",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}


DELETE_SKILL_RESPONSES = {
    # 204 by default
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
    404: {
        "content": {
            "application/json": {
                "example": {
                    "value": {
                        "status": FAILURE_EXAMPLE,
                        "message": "Skill not found in profile",
                        "err_code": "not_found",
                    }
                }
            }
        }
    },
}