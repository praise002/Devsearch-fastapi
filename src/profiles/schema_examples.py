from src.auth.schema_examples import UNAUTHORIZED, VALIDATION_ERROR
from src.auth.utils import EMAIL_EXAMPLE, FAILURE_EXAMPLE, SUCCESS_EXAMPLE, UUID_EXAMPLE

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


UPDATE_PROFILE_RESPONSES = {
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
    401: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "Please provide a valid access token.",
                    "err_code": "access_token_required",
                }
            }
        }
    },
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
    # 422 automatically displays in the docs
}

UPDATE_PROFILE_RESPONSES = {
    # 422 by default
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

GET_USER_PROFILE_EXAMPLE = {
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

UPLOAD_AVATAR_RESPONSES = {
    # 200 and 422 by default
    401: UNAUTHORIZED,
}


ADD_SKILL_RESPONSES = {
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "You can only add skills to your own profile",
                    "err_code": "insufficient_permission",
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
    422: {
        "content": {
            "application/json": {
                "examples": {
                    "skill_exists": {
                        "status": FAILURE_EXAMPLE,
                        "message": "Skill 'Python' already exists in your profile",
                        "err_code": "unprocessable_entity",
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
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "You can only update your own skills",
                    "err_code": "insufficient_permission",
                }
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "examples": {
                    "profile_not_found": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Profile for user '<username>' not found",
                            "err_code": "not_found",
                        }
                    },
                    "skill_not_found": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Skill not found in profile",
                            "err_code": "not_found",
                        }
                    },
                }
            }
        }
    },
}


DELETE_SKILL_RESPONSES = {
    401: UNAUTHORIZED,
    403: {
        "content": {
            "application/json": {
                "example": {
                    "status": FAILURE_EXAMPLE,
                    "message": "You can only delete your own skills",
                    "err_code": "insufficient_permission",
                }
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "examples": {
                    "profile_not_found": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Profile for user '<username>' not found",
                            "err_code": "not_found",
                        }
                    },
                    "skill_not_found": {
                        "value": {
                            "status": FAILURE_EXAMPLE,
                            "message": "Skill not found in profile",
                            "err_code": "not_found",
                        }
                    },
                }
            }
        }
    },
}
