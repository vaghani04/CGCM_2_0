import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.app.controllers.context_gather_controller import (
    ContextGatherController,
)
from src.app.models.schemas.context_gather_query_schema import CodebaseContextRequest
from src.app.utils.error_handler import handle_exceptions

router = APIRouter()


@router.post("/context-gather")
@handle_exceptions
async def context_gather_route(
    codebase_context: CodebaseContextRequest,
    context_gather_controller: ContextGatherController = Depends(
        ContextGatherController
    ),
):
    start_time = time.time()
    print(f"API request started at: {start_time}")

    response_data = await context_gather_controller.context_gather(codebase_context.codebase_path)

    status_message = "Context Gathered Successfully!"
    end_time = time.time()
    time_taken = end_time - start_time

    print(f"API request ended at: {end_time}")
    print(f"Time taken: {time_taken:.4f} seconds")

    return JSONResponse(
        content={
            "data": response_data,
            "statuscode": 200,
            "detail": status_message,
            "error": "",
            "time_taken_seconds": round(time_taken, 4),
        },
        status_code=status.HTTP_200_OK,
    )