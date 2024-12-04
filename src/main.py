from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db

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
)


@app.get("/")
def read_root():
    return {"Hello": "World"}
