from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.app.config.database import mongodb_database
from src.app.middlewares.path_validation_middleware import PathValidationMiddleware
from src.app.routes import context_gather_route
from src.app.routes import user_query_route


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    mongodb_database.connect()

    yield

    mongodb_database.disconnect()


app = FastAPI(title="My FastAPI Application", lifespan=db_lifespan)

# Add middlewares
app.add_middleware(PathValidationMiddleware)

# Include routers
app.include_router(
    context_gather_route.router, prefix="/api/v1", tags=["Context Gathering"]
)
app.include_router(
    user_query_route.router, prefix="/api/v1", tags=["User Query"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to my FastAPI application!"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
