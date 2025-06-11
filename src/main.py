from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n🌐 Incoming request:")
    print(f"   Method: {request.method}")
    print(f"   URL: {request.url}")
    print(f"   Client: {request.client}")
    print(f"   Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    print(f"   📨 Response: {response.status_code}")
    return response

# Add CORS middleware to handle browser preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add other middlewares
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
