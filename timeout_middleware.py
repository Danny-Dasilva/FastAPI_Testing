import pydantic
from fastapi import FastAPI
"""Request Middleware: Classes definend here are mainly used for handling sentry logging."""
import time
import asyncio
from typing import Any, Dict, List, Type, Union, Callable, Optional, Sequence
from starlette.types import ASGIApp
import pytest
import time
import random
# Installed Packages
from fastapi import params, Request, routing, Response
from sentry_sdk import Hub, capture_event
from fastapi.routing import APIRoute, APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi.datastructures import Default
from fastapi import APIRouter
from starlette.routing import BaseRoute
from httpx import AsyncClient
from starlette.status import HTTP_200_OK
app = FastAPI()
QUEUED_ROUTE_TIMEOUT = .1
QUEUED_ROUTE_MAX_RETRIES = 5

class QueuedRoute(APIRoute):

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                
                before = time.time()
                response = await asyncio.wait_for(
                    original_route_handler(request), timeout=QUEUED_ROUTE_TIMEOUT
                )
                print(response)
                duration = time.time() - before
                response.headers["Queued-Response-Time"] = str(duration)
                return response

            except asyncio.TimeoutError:
                duration = time.time() - before
                retry_attempt = int(request.headers.get("retry-attempt", 0))
                # ADD TO GOOGLE TASK QUEUE
                if retry_attempt <= QUEUED_ROUTE_MAX_RETRIES:
                    print("retry")
                return JSONResponse(
                    {
                        "detail": "Request processing time excedeed limit",
                        "processing_time": duration,
                        "retry-attempt": retry_attempt,
                    },
                    status_code=200,
                )

        return custom_route_handler



class LoggedRouter(APIRouter):  # noqa
    def __init__(  # noqa
        self,
        *,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),  # noqa: B008
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        routes: Optional[List[routing.BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
    ) -> None:
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=APIRoute,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
        )

class QueuedRouter(APIRouter):  # noqa
    def __init__(  # noqa
        self,
        *,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[Sequence[params.Depends]] = None,
        default_response_class: Type[Response] = Default(JSONResponse),  # noqa: B008
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[BaseRoute]] = None,
        routes: Optional[List[routing.BaseRoute]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        dependency_overrides_provider: Optional[Any] = None,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
    ) -> None:
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=QueuedRoute,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
        )

app.router.route_class = LoggedRouter

router = LoggedRouter()

queued = QueuedRouter()

@router.get("/")
def root() -> dict:
    from time import sleep
    sleep(2)

    return {"message": "Hello World"}

@queued.get("/test")
def test() -> dict:
    from time import sleep
    sleep(2)
    return {"message": "test"}

@queued.get("/test1")
async def test1() -> dict:
    await asyncio.sleep(3)
    return {"message": "test"}

app.include_router(router)
app.include_router(queued)


# Testing wether or not the middleware triggers
@pytest.mark.asyncio
async def test_504_error_triggers():
    # Creating an asynchronous client to test our asynchronous function
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/test")
    assert response.status_code == HTTP_200_OK
    assert response.json().get("detail") == "Request processing time excedeed limit"

# Testing middleware's precision
# ie : Testing if it triggers when it should not and vice versa
@pytest.mark.asyncio
async def test_504_error_precision():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        for i in range(100):
            
            response = await ac.get("/test1")
            assert response.status_code == HTTP_200_OK
            body = response.json()
            print(body.get("processing_time"))
            assert body.get("processing_time") > .1
            assert body.get("processing_time") < .11

if __name__ == "__main__":
    # Installed Packages
    import uvicorn

    uvicorn.run("test:app", reload=True, log_level="debug", use_colors=True)
