from src.auth.schemas import UserCreate

auth_prefix = f"/api/v1/auth"


def test_user_creation(fake_session, fake_user_service, test_client):
    register_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "praiz@gmail.com",
        "username": "john-doe",
        "password": "123456",
    }

    response = test_client.post(
        url=f"{auth_prefix}/register",
        json=register_data,
    )

    user_data = UserCreate(**register_data)

    assert fake_user_service.user_exists_called_once()
    assert fake_user_service.user_exists_called_once_with(
        register_data["email"], fake_session
    )
    assert fake_user_service.create_user_called_once()
    assert fake_user_service.create_user_called_once_with(user_data, fake_session)
