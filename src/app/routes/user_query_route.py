import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.app.controllers.user_query_controller import (
    UserQueryController,
)
from src.app.models.schemas.user_query_schema import UserQueryRequest
from src.app.utils.error_handler import handle_exceptions

router = APIRouter()


@router.post("/user-query")
@handle_exceptions
async def user_query_route(
    user_query: UserQueryRequest,
    user_query_controller: UserQueryController = Depends(
        UserQueryController
    ),
):
    start_time = time.time()
    print(f"API request started at: {start_time}")
    
    response_data = await user_query_controller.user_query(user_query)

    status_message = "User Query Successfully!"
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