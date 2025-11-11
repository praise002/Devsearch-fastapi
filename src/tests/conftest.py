import asyncio
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src import app
from src.auth.schemas import UserCreate
from src.db.main import get_session


def pytest_configure(config):
    """
    Configure pytest markers and settings.
    """
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test")


@pytest.fixture(scope="session")
def event_loop():
    """
    Creates an event loop for the entire test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgresql_proc_config():
    """
    Configure how pytest-postgresql starts the PostgreSQL process.
    """
    return {
        "port": None,  # 5433
        "host": "localhost",
        "user": "postgres",
        "password": "",
        "options": "-c fsync=off",  # Faster for testing (disables some safety checks)
    }


@pytest.fixture(scope="session")
async def database_url(postgresql_proc):
    """
    Constructs the async database URL for the temporary database and creates it.
    """
    from sqlalchemy_utils import create_database, database_exists

    # Extract connection details from postgresql_proc fixture
    user = postgresql_proc.user
    host = postgresql_proc.host
    port = postgresql_proc.port
    dbname = postgresql_proc.dbname
    password = postgresql_proc.password if hasattr(postgresql_proc, "password") else ""

    # Construct sync URL for database creation
    sync_url = (
        f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        if password
        else f"postgresql://{user}@{host}:{port}/{dbname}"
    )

    # Create the database if it doesn't exist
    if not database_exists(sync_url):
        create_database(sync_url)

    # Construct and return async URL for the engine
    async_url = (
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
        if password
        else f"postgresql+asyncpg://{user}@{host}:{port}/{dbname}"
    )

    return async_url


@pytest.fixture(scope="session")
async def test_engine(database_url, event_loop):
    """
    Creates async SQLAlchemy engine connected to temporary database.

    Args:
        database_url: URL from database_url fixture
        event_loop: Event loop for async operations

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True to see SQL queries (useful for debugging)
        poolclass=NullPool,  # Don't pool connections in tests
        future=True,
    )

    yield engine

    # Dispose engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a fresh database with clean tables for each test.
    """
    # Drop and recreate all tables before each test
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create session
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Creates an async HTTP client for testing API endpoints.



    Args:
        db_session: Database session from db_session fixture

    Yields:
        AsyncClient: HTTP client for making requests
    """

    # Override the database dependency
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # Create async client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_email(monkeypatch):
    """
    Mocks the send_email function to prevent real emails during tests.

    Returns:
        list: List of "sent" emails that can be verified in tests
    """
    sent_emails = []

    def fake_send_email(
        background_tasks,
        subject: str,
        email_to: str,
        template_context: dict,
        template_name: str,
    ):
        """Fake send_email that stores email details."""
        sent_emails.append(
            {
                "subject": subject,
                "email_to": email_to,
                "template_context": template_context,
                "template_name": template_name,
            }
        )

    # Mock send_email where it's USED (in routes), not where it's defined
    from src.auth import routes

    monkeypatch.setattr(routes, "send_email", fake_send_email)
    # TODO: FIX, ACTUAL EMAIL BEING SENT

    return sent_emails


@pytest.fixture
def mock_otp(monkeypatch):
    """
    Mocks OTP generation to return predictable test value.

    Returns:
        int: The predictable OTP that will be "generated"
    """

    def fake_generate_otp(user, session):
        return 123456

    from src.auth import routes

    monkeypatch.setattr(routes, "generate_otp", fake_generate_otp)

    return 123456


@pytest.fixture
def valid_user_data():
    """
    Provides valid user registration data.

    Returns:
        dict: Valid user registration data
    """
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePass123!",
    }


@pytest.fixture
def another_user_data():
    """
    Provides different user data for testing multiple users.

    Returns:
        dict: Another set of valid user data
    """
    return {
        "email": "another@example.com",
        "username": "anotheruser",
        "first_name": "Another",
        "last_name": "User",
        "password": "AnotherPass123!",
    }


@pytest.fixture
def user2_data():
    return {
        "email": "user2@example.com",
        "username": "user2",
        "first_name": "Test",
        "last_name": "User2",
        "password": "SecurePass123!",
    }


@pytest.fixture
def user3_data():
    return {
        "email": "user3@example.com",
        "username": "user3",
        "first_name": "Test",
        "last_name": "User3",
        "password": "SecurePass123!",
    }


@pytest.fixture
def invalid_user_data():
    return {
        "email": "invalid-email",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePass123!",
    }


@pytest.fixture
def weak_password_data():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "123",
    }


@pytest.fixture
async def registered_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user2_data: dict,
):
    """
    Creates a registered but unverified user for testing.
    """
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**user2_data)
    user = await user_service.create_user(user_create, db_session)
    return user


@pytest.fixture
async def verified_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user3_data: dict,
):
    """
    Creates a verified user for testing.
    """
    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**user3_data)
    user = await user_service.create_user(user_create, db_session)

    await user_service.update_user(user, {"is_email_verified": True}, db_session)
    return user


@pytest.fixture
async def inactive_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    another_user_data: dict,
):

    from src.auth.service import UserService

    user_service = UserService()
    user_create = UserCreate(**another_user_data)
    user = await user_service.create_user(user_create, db_session)

    await user_service.update_user(user, {"is_email_verified": True, "is_active": False}, db_session)
    return user


@pytest.fixture
async def otp_for_user(
    db_session: AsyncSession,
    registered_user,
    mock_otp: str,
):
    """
    Creates a valid OTP for a user.
    """

    from src.db.models import Otp

    # Create OTP record directly
    otp_record = Otp(user_id=registered_user.id, otp=mock_otp, is_valid=True)
    db_session.add(otp_record)
    await db_session.commit()

    return mock_otp
