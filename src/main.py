from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette_admin.contrib.sqla import Admin, ModelView

from src.db.main import init_db
from src.db.models import User
from src.db.main import async_engine

@asynccontextmanager
async def life_span(app:FastAPI):
    await init_db()
    print('Server is starting...')
    yield 
    print('Server has been stopped...')
    
version = "v1"

app = FastAPI(
    title="Devsearch",
    description="A REST API for a developer connect platform",
    version=version,
    docs_url=f"/api/{version}/docs",
    redoc_url=f"/api/{version}/redoc",
    contact={
        "email": "praizthecoder@gmail.com",
    },
    lifespan=life_span #TODO: REMOVE LATER
)

# Create admin
admin = Admin(async_engine, title="Devsearch")

# Add view
admin.add_view(ModelView(User, icon="fas fa-user"))

# Mount admin to your app
admin.mount_to(app)


@app.get("/")
def read_root():
    return {"Hello": "World"}
