from fastapi import FastAPI
from fastapi.requests import Request
import time
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

logger = logging.getLogger("uvicorn.access")
logging.disabled = True

def register_middleware(app: FastAPI):

    @app.middleware("http")
    async def add_ratelimit_headers(request: Request, call_next):
        response = await call_next(request)

        remaining = getattr(request.state, "rate_limit_remaining", None)
        limit = getattr(request.state, "rate_limit_limit", None)

        if remaining is not None:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response

    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        
        start_time = time.time()

        response = await call_next(request)

        processing_time = time.time() - start_time

        message = f"{request.client.host}:{request.client.port} - {request.method} - {request.url.path} - {response.status_code} completed after {processing_time}s"

        print(message)

        return response
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins = ["*"],
        allow_methods = ["*"],
        allow_headers = ["*"],
        allow_credentials = True,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts = ["localhost", "127.0.0.1"]
    )