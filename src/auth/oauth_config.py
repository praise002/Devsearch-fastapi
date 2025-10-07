from authlib.integrations.starlette_client import OAuth
from decouple import config

oauth = OAuth()
oauth.register(
    name="google",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    redirect_uri=config("GOOGLE_REDIRECT_URI"),
    client_kwargs={
        "scope": "openid email profile",
    },
    authorize_params={
        "access_type": "offline",  # Get refresh tokens
        "prompt": "select_account",
    },
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
)