from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette_admin.contrib.sqla import Admin, ModelView

from src.auth.routes import router as auth_router
from src.db.main import async_engine
from src.db.models import User

description = """
## Overview
DEVSEARCH API is a powerful platform designed to connect developers around the world.

## Features
- **Collaboration**: Connect with other developers worldwide
- **Skill-sharing**: Showcase and discover technical skills
- **Project discovery**: Find interesting projects to contribute to
- **Profile management**: Create and manage developer profiles
- **Project listings**: Search and browse through projects
- **Ratings & Reviews**: Rate and review projects

## Technical Details
The API is built using modern best practices and RESTful principles, ensuring that it is intuitive and easy to integrate into your applications.
"""

version = "v1"

app = FastAPI(
    title="DevSearch",
    description=description,
    version=version,
    docs_url=f"/api/{version}/docs",
    redoc_url=f"/api/{version}/redoc",
    contact={
        "name": "Devsearch admin",
        "email": "praizthecoder@gmail.com",
    },
)

templates = Jinja2Templates(directory="templates")


app.mount("/static", StaticFiles(directory="static"), name="static")

# Create admin
admin = Admin(async_engine, title="Devsearch")

# Add view
# admin.add_view(ModelView(User, icon="fas fa-user"))

# Mount admin to your app
# admin.mount_to(app)

app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["auth"])


@app.get("/")
async def root():
    return {"message": "Welcome to DevSearch API"}
