from src.auth.schemas import UserCreate

auth_prefix = f"/api/v1/auth"


def test_register(fake_session, fake_user_service, test_client):
    register_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "praiz@gmail.com",
        "username": "john-doe",
        "password": "Anything12#",
    }

    response = test_client.post(
        url=f"{auth_prefix}/register",
        json=register_data,
    )

    user_data = UserCreate(**register_data)

    # Valid Registration
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["email"] == register_data["email"]

    # Verify service calls
    assert fake_user_service.user_exists_called_once()
    assert fake_user_service.username_exists_called_once()
    assert fake_user_service.user_exists_called_once_with(
        register_data["email"], fake_session
    )
    assert fake_user_service.user_exists_called_once_with(
        register_data["username"], fake_session
    )
    assert fake_user_service.create_user_called_once()
    assert fake_user_service.create_user_called_once_with(user_data, fake_session)

    # Email exists - 422
    # Username exists - 422
    # Invalid Registration - 422
