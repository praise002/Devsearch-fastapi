from src.auth.utils import EMAIL_EXAMPLE, UUID_EXAMPLE

GET_USER_PROFILE_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "status": "success",
                    "message": "Profile retrieved successfully",
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
            }
        }
    },
    401: {
        "content": {
            "application/json": {
                "example": {
                    "status": "failure",
                    "message": "Please provide a valid access token.",
                    "err_code": "access_token_required",
                }
            }
        }
    },
}
